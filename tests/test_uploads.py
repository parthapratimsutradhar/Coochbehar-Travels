import asyncio
import io
import json
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.datastructures import Headers

from app.api.deps import get_current_actor
from app.core.config import settings
from app.api.v1.public.uploads import router as uploads_router
from app.db.database import get_db
from app.middleware.upload_request_limit import UploadRequestSizeLimitMiddleware
from app.models.cdn_upload_rate_limit import CDNUploadRateLimit
from app.services import cdn_service as cdn


@pytest.fixture
def cdn_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "cdn"
    root.mkdir()
    monkeypatch.setattr(cdn, "CDN_ROOT", root)
    monkeypatch.setattr(cdn, "CDN_BASE_URL", "https://cdn.example.test")
    monkeypatch.setattr(settings, "CDN_IMAGE_COMPRESSION_ENABLED", False)
    monkeypatch.setattr(settings, "CDN_VIDEO_COMPRESSION_ENABLED", False)
    monkeypatch.setattr(settings, "CDN_ANTIVIRUS_ENABLED", False)
    for folder in cdn.ALLOWED_FOLDERS:
        (root / folder).mkdir()
    return root


def image_bytes(image_format: str = "JPEG", size: tuple[int, int] = (32, 24)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, (32, 120, 200)).save(output, format=image_format)
    return output.getvalue()


def _upload_file(data: bytes, content_type: str, filename: str | None = None) -> UploadFile:
    filename = filename or {
        "image/jpeg": "photo.jpg",
        "image/png": "photo.png",
        "video/mp4": "clip.mp4",
        "video/webm": "clip.webm",
        "video/mov": "clip.mov",
        "application/pdf": "document.pdf",
    }.get(content_type, "upload.bin")
    return UploadFile(
        filename=filename,
        file=io.BytesIO(data),
        headers=Headers({"content-type": content_type}),
    )


def _upload(data: bytes, content_type: str, filename: str | None = None) -> dict:
    return asyncio.run(cdn.upload_file_to_cdn(_upload_file(data, content_type, filename)))


@pytest.fixture
def client():
    test_app = FastAPI()
    test_app.add_middleware(UploadRequestSizeLimitMiddleware)
    test_app.include_router(uploads_router, prefix="/api/v1")
    test_app.dependency_overrides[get_db] = lambda: None
    with TestClient(test_app) as test_client:
        yield test_client


def test_upload_requires_jwt(client: TestClient):
    response = client.post(
        "/api/v1/public/files/upload",
        files={"file": ("photo.jpg", b"invalid", "image/jpeg")},
    )
    assert response.status_code == 401


def test_request_body_limit_rejects_before_multipart_parsing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "CDN_MAX_IMAGE_SIZE_MB", 1)
    monkeypatch.setattr(settings, "CDN_MAX_VIDEO_SIZE_MB", 1)
    monkeypatch.setattr(settings, "CDN_MAX_PDF_SIZE_MB", 1)
    response = client.post(
        "/api/v1/public/files/upload",
        files={"file": ("large.jpg", b"x" * (1024 * 1024 + 256 * 1024 + 1), "image/jpeg")},
    )
    assert response.status_code == 413


@pytest.mark.parametrize(
    ("content_type", "image_format", "extension"),
    [("image/jpeg", "JPEG", ".jpg"), ("image/png", "PNG", ".png")],
)
def test_valid_image_uploads(cdn_root: Path, content_type: str, image_format: str, extension: str):
    result = _upload(image_bytes(image_format), content_type)
    assert result["path"].startswith("temporary-uploads/")
    assert result["filename"].endswith(extension)
    assert result["content_type"] == content_type
    assert (cdn_root / result["path"]).is_file()


def test_native_file_upload_uses_temporary_cdn_folder(cdn_root: Path):
    result = asyncio.run(cdn.upload_file_to_cdn(_upload_file(image_bytes("PNG"), "image/png")))
    assert result["path"].startswith("temporary-uploads/")
    assert result["url"].startswith("https://cdn.example.test/temporary-uploads/")
    assert result["bytes"] > 0


def test_google_profile_picture_uploads_directly_to_permanent_folder(
    cdn_root: Path, monkeypatch: pytest.MonkeyPatch
):
    image = image_bytes("PNG")

    class ImageResponse:
        status_code = 200
        headers = {"content-type": "image/png"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def aiter_bytes(self, chunk_size: int):
            yield image

    class FakeClient:
        def __init__(self, *, timeout, follow_redirects):
            assert follow_redirects is False

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def stream(self, method: str, url: str):
            assert method == "GET"
            assert url.startswith("https://lh3.googleusercontent.com/")
            return ImageResponse()

    monkeypatch.setattr(cdn.httpx, "AsyncClient", FakeClient)
    result_url = asyncio.run(
        cdn.upload_google_profile_picture(
            "https://lh3.googleusercontent.com/a/avatar.png"
        )
    )
    assert result_url.startswith("https://cdn.example.test/profile-picture/")
    stored_files = list((cdn_root / "profile-picture").iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].suffix == ".png"
    assert list((cdn_root / cdn.TEMP_FOLDER).iterdir()) == []
    assert list((cdn_root / ".upload-staging").iterdir()) == []


def test_google_profile_picture_rejects_untrusted_urls():
    with pytest.raises(HTTPException) as error:
        cdn._validate_google_picture_url("https://googleusercontent.com.evil.example/avatar.png")
    assert error.value.status_code == 422


def test_invalid_image_bytes_rejected(cdn_root: Path):
    with pytest.raises(HTTPException) as error:
        _upload(b"not an image", "image/jpeg")
    assert error.value.status_code == 422
    assert not list((cdn_root / cdn.TEMP_FOLDER).iterdir())


def test_oversized_image_rejected(cdn_root: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "CDN_MAX_IMAGE_SIZE_MB", 1)
    with pytest.raises(HTTPException) as error:
        _upload(image_bytes() + b"x" * (1024 * 1024), "image/jpeg")
    assert error.value.status_code == 413


@pytest.mark.parametrize(
    ("data", "content_type", "filename", "expected"),
    [(b"", "image/jpeg", "empty.jpg", 422), (b"MZ", "application/x-msdownload", "x.exe", 415)],
)
def test_empty_and_unsupported_uploads_rejected(
    cdn_root: Path, data: bytes, content_type: str, filename: str, expected: int
):
    with pytest.raises(HTTPException) as error:
        _upload(data, content_type, filename)
    assert error.value.status_code == expected


@pytest.mark.parametrize("unsafe_path", ["../outside", "/etc/passwd", "C:\\Windows\\win.ini"])
def test_unsafe_cdn_paths_rejected(cdn_root: Path, unsafe_path: str):
    with pytest.raises(HTTPException) as error:
        cdn._resolve_path(unsafe_path)
    assert error.value.status_code == 400


def test_generated_filename_is_not_client_controlled(cdn_root: Path):
    result = _upload(image_bytes(), "image/jpeg", "../../client-controlled.jpg")
    assert result["filename"] != "client-controlled.jpg"
    assert uuid.UUID(hex=Path(result["filename"]).stem)


def test_extension_and_content_type_must_match(cdn_root: Path):
    with pytest.raises(HTTPException) as error:
        _upload(image_bytes(), "image/png", "photo.jpg")
    assert error.value.status_code == 415


def test_image_compression_uses_smaller_result(cdn_root: Path, monkeypatch: pytest.MonkeyPatch):
    source, output = cdn_root / "source.jpg", cdn_root / "compressed.jpg"
    Image.effect_noise((512, 512), 100).convert("RGB").save(
        source, format="JPEG", quality=100, optimize=False
    )
    selected = cdn._compress_image(source, output, "JPEG")
    assert selected == output
    assert output.stat().st_size < source.stat().st_size


def test_larger_compression_result_does_not_replace_original(
    cdn_root: Path, monkeypatch: pytest.MonkeyPatch
):
    source, output = cdn_root / "source.jpg", cdn_root / "compressed.jpg"
    source.write_bytes(image_bytes())

    def write_larger(self, target, **kwargs):
        Path(target).write_bytes(b"x" * (source.stat().st_size + 1))

    monkeypatch.setattr(Image.Image, "save", write_larger)
    assert cdn._compress_image(source, output, "JPEG") == source
    assert not output.exists()


def test_animated_gif_is_preserved(cdn_root: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "CDN_IMAGE_COMPRESSION_ENABLED", True)
    buffer = io.BytesIO()
    frames = [Image.new("RGBA", (8, 8), color) for color in ("red", "blue")]
    frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:], duration=100)
    result = _upload(buffer.getvalue(), "image/gif", "motion.gif")
    with Image.open(cdn_root / result["path"]) as stored:
        assert stored.n_frames == 2


def test_animated_webp_is_preserved(cdn_root: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "CDN_IMAGE_COMPRESSION_ENABLED", True)
    buffer = io.BytesIO()
    frames = [Image.new("RGB", (8, 8), color) for color in ("red", "blue")]
    frames[0].save(buffer, format="WEBP", save_all=True, append_images=frames[1:], duration=100)
    result = _upload(buffer.getvalue(), "image/webp", "motion.webp")
    with Image.open(cdn_root / result["path"]) as stored:
        assert stored.n_frames == 2


def _fake_probe(monkeypatch: pytest.MonkeyPatch, *, duration: int = 2, codec: str = "h264"):
    monkeypatch.setattr(cdn.shutil, "which", lambda tool: f"/usr/bin/{tool}")

    def run(command, **kwargs):
        return SimpleNamespace(stdout=json.dumps({
            "format": {
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                "duration": str(duration),
                "tags": {"major_brand": "isom"},
            },
            "streams": [{
                "codec_type": "video", "codec_name": codec, "width": 640, "height": 360
            }],
        }))

    monkeypatch.setattr(cdn.subprocess, "run", run)


def _mp4(size: int = 32) -> bytes:
    return b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isom" + b"x" * size


def test_valid_mp4_upload(cdn_root: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_probe(monkeypatch)
    result = _upload(_mp4(), "video/mp4")
    assert result["content_type"] == "video/mp4"
    assert result["filename"].endswith(".mp4")


def test_video_duration_limit_is_enforced(cdn_root: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_probe(monkeypatch, duration=11)
    monkeypatch.setattr(settings, "CDN_MAX_VIDEO_DURATION_SECONDS", 10)
    with pytest.raises(HTTPException) as error:
        _upload(_mp4(), "video/mp4")
    assert error.value.status_code == 422


def test_video_compression_cleanup(cdn_root: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(cdn.shutil, "which", lambda tool: f"/usr/bin/{tool}")
    monkeypatch.setattr(settings, "CDN_VIDEO_COMPRESSION_ENABLED", True)

    def run(command, **kwargs):
        if Path(command[0]).name == "ffmpeg":
            Path(command[-1]).write_bytes(_mp4(0))
            return SimpleNamespace(stdout="")
        compressed = Path(command[-1]).name != "source"
        codec = "h264" if compressed else "vp9"
        details = {
            "format": {
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                "duration": "2",
                "tags": {"major_brand": "isom"},
            },
            "streams": [{
                "codec_type": "video", "codec_name": codec, "width": 640, "height": 360
            }],
        }
        return SimpleNamespace(stdout=json.dumps(details))

    monkeypatch.setattr(cdn.subprocess, "run", run)
    result = _upload(_mp4(256), "video/mp4")
    assert result["bytes"] < len(_mp4(256))
    assert list((cdn_root / ".upload-staging").iterdir()) == []


def test_failed_ffmpeg_cleanup(cdn_root: Path, monkeypatch: pytest.MonkeyPatch):
    _fake_probe(monkeypatch, codec="vp9")
    monkeypatch.setattr(settings, "CDN_VIDEO_COMPRESSION_ENABLED", True)

    def fail_ffmpeg(command, **kwargs):
        if Path(command[0]).name == "ffmpeg":
            raise cdn.subprocess.CalledProcessError(1, command)
        return SimpleNamespace(stdout=json.dumps({
            "format": {
                "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
                "duration": "2",
                "tags": {"major_brand": "isom"},
            },
            "streams": [{
                "codec_type": "video", "codec_name": "vp9", "width": 640, "height": 360
            }],
        }))

    monkeypatch.setattr(cdn.subprocess, "run", fail_ffmpeg)
    with pytest.raises(HTTPException) as error:
        _upload(_mp4(256), "video/mp4")
    assert error.value.status_code == 502
    assert list((cdn_root / ".upload-staging").iterdir()) == []


class FakeClamd:
    def __init__(self, response: bytes):
        self.response = response

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def settimeout(self, timeout):
        pass

    def sendall(self, data):
        pass

    def recv(self, size):
        response, self.response = self.response, b""
        return response


def test_eicar_test_signature_is_rejected(cdn_root: Path, monkeypatch: pytest.MonkeyPatch):
    source = cdn_root / "eicar.txt"
    source.write_bytes(b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*")
    monkeypatch.setattr(
        cdn.socket, "create_connection",
        lambda *args, **kwargs: FakeClamd(b"stream: Eicar-Test-Signature FOUND\0"),
    )
    try:
        with pytest.raises(HTTPException) as error:
            cdn._scan_with_clamd(source)
        assert error.value.status_code == 400
    finally:
        source.unlink(missing_ok=True)


def test_clamd_ping_uses_configured_unix_socket(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "CDN_ANTIVIRUS_ENABLED", True)
    monkeypatch.setattr(settings, "CDN_ANTIVIRUS_SOCKET", "/run/clamav/clamd.ctl")
    monkeypatch.setattr(cdn.socket, "AF_UNIX", 1, raising=False)
    connected_paths = []

    class FakeUnixClamd(FakeClamd):
        def __init__(self, family, socket_type):
            assert family == cdn.socket.AF_UNIX
            assert socket_type == cdn.socket.SOCK_STREAM
            super().__init__(b"PONG\0")

        def connect(self, path):
            connected_paths.append(path)

    monkeypatch.setattr(cdn.socket, "socket", FakeUnixClamd)
    monkeypatch.setattr(
        cdn.socket,
        "create_connection",
        lambda *args, **kwargs: pytest.fail("TCP must not be used when a socket is configured"),
    )

    assert cdn.check_antivirus_available()
    assert connected_paths == ["/run/clamav/clamd.ctl"]
    assert cdn.antivirus_health_status() == "available"


def test_eicar_scan_uses_configured_unix_socket(
    cdn_root: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "CDN_ANTIVIRUS_SOCKET", "/run/clamav/clamd.ctl")
    monkeypatch.setattr(cdn.socket, "AF_UNIX", 1, raising=False)
    connected_paths = []

    class FakeUnixClamd(FakeClamd):
        def __init__(self, family, socket_type):
            assert family == cdn.socket.AF_UNIX
            assert socket_type == cdn.socket.SOCK_STREAM
            super().__init__(b"stream: Eicar-Test-Signature FOUND\0")

        def connect(self, path):
            connected_paths.append(path)

    monkeypatch.setattr(cdn.socket, "socket", FakeUnixClamd)
    monkeypatch.setattr(
        cdn.socket,
        "create_connection",
        lambda *args, **kwargs: pytest.fail("TCP must not be used when a socket is configured"),
    )
    eicar = cdn_root / "eicar.com"
    eicar.write_bytes(b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*")

    try:
        with pytest.raises(HTTPException) as error:
            cdn._scan_with_clamd(eicar)
        assert error.value.status_code == 400
        assert connected_paths == ["/run/clamav/clamd.ctl"]
    finally:
        eicar.unlink(missing_ok=True)


def test_unavailable_unix_socket_fails_closed(
    cdn_root: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "CDN_ANTIVIRUS_ENABLED", True)
    monkeypatch.setattr(settings, "CDN_ANTIVIRUS_SOCKET", "/run/clamav/clamd.ctl")
    monkeypatch.setattr(
        cdn,
        "_connect_to_clamd",
        lambda timeout: (_ for _ in ()).throw(FileNotFoundError("clamd socket unavailable")),
    )

    assert not cdn.check_antivirus_available()
    assert cdn.antivirus_health_status() == "unavailable"
    with pytest.raises(HTTPException) as error:
        _upload(image_bytes(), "image/jpeg")
    assert error.value.status_code == 503
    assert not list((cdn_root / cdn.TEMP_FOLDER).iterdir())


def test_clean_upload_scans_through_configured_unix_socket(
    cdn_root: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "CDN_ANTIVIRUS_ENABLED", True)
    monkeypatch.setattr(settings, "CDN_ANTIVIRUS_SOCKET", "/run/clamav/clamd.ctl")
    connected_paths = []

    def connect_to_scanner(timeout):
        connected_paths.append(settings.CDN_ANTIVIRUS_SOCKET)
        return FakeClamd(b"stream: OK\0")

    monkeypatch.setattr(cdn, "_connect_to_clamd", connect_to_scanner)

    result = _upload(image_bytes(), "image/jpeg")

    assert result["path"].startswith(f"{cdn.TEMP_FOLDER}/")
    assert connected_paths == ["/run/clamav/clamd.ctl"]


def test_antivirus_unavailable_fails_closed(cdn_root: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "CDN_ANTIVIRUS_ENABLED", True)
    monkeypatch.setattr(cdn.socket, "create_connection", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    with pytest.raises(HTTPException) as error:
        _upload(image_bytes(), "image/jpeg")
    assert error.value.status_code == 503
    assert not list((cdn_root / cdn.TEMP_FOLDER).iterdir())


def test_antivirus_startup_check_reports_unavailable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "CDN_ANTIVIRUS_ENABLED", True)
    monkeypatch.setattr(cdn, "_clamd_command", lambda command: (_ for _ in ()).throw(OSError()))
    assert not cdn.check_antivirus_available()
    assert cdn.antivirus_health_status() == "unavailable"


def test_malformed_pdf_rejected(cdn_root: Path):
    with pytest.raises(HTTPException) as error:
        _upload(b"%PDF-1.7\nnot a PDF structure\n%%EOF", "application/pdf")
    assert error.value.status_code == 422


def test_temporary_file_promotion(cdn_root: Path):
    filename = f"{uuid.uuid4().hex}.jpg"
    source = cdn_root / cdn.TEMP_FOLDER / filename
    source.write_bytes(b"validated image")
    result = cdn.promote_temp_file(f"{cdn.TEMP_FOLDER}/{filename}", "profile-picture")
    assert result["path"] == f"profile-picture/{filename}"
    assert not source.exists()
    assert (cdn_root / result["path"]).read_bytes() == b"validated image"


def test_cdn_promotion_accepts_temp_url(cdn_root: Path):
    filename = f"{uuid.uuid4().hex}.jpg"
    source = cdn_root / cdn.TEMP_FOLDER / filename
    source.write_bytes(b"validated image")
    result = asyncio.run(
        cdn.promote_cdn_asset(
            f"https://cdn.example.test/{cdn.TEMP_FOLDER}/{filename}",
            "customer-documents",
        )
    )
    assert result["url"].endswith(f"customer-documents/{filename}")
    assert result["path"] == f"customer-documents/{filename}"
    assert not source.exists()


@pytest.mark.parametrize(
    "temp_path",
    ["profile-picture/file.jpg", "temporary-uploads/../file.jpg", "temporary-uploads/nested/file.jpg"],
)
def test_promotion_rejects_non_temp_paths(cdn_root: Path, temp_path: str):
    with pytest.raises(HTTPException):
        cdn.promote_temp_file(temp_path, "profile-picture")


def test_upload_rate_limit_returns_429(monkeypatch: pytest.MonkeyPatch):
    engine = create_engine("sqlite://")
    CDNUploadRateLimit.__table__.create(engine)
    monkeypatch.setattr(settings, "CDN_UPLOAD_RATE_LIMIT", 1)
    monkeypatch.setattr(settings, "CDN_UPLOAD_RATE_WINDOW_SECONDS", 3600)
    actor = (SimpleNamespace(id=uuid.uuid4()), "CUSTOMER")
    with Session(engine) as db:
        cdn.enforce_upload_rate_limit(db, actor, "192.0.2.1")
        with pytest.raises(HTTPException) as error:
            cdn.enforce_upload_rate_limit(db, actor, "192.0.2.1")
    assert error.value.status_code == 429


@pytest.mark.parametrize("actor_type", ["ADMIN", "STAFF", "CUSTOMER"])
def test_authenticated_upload_response_contract(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, actor_type: str
):
    client.app.dependency_overrides[get_current_actor] = lambda: (
        SimpleNamespace(id=uuid.uuid4()), actor_type
    )
    monkeypatch.setattr(
        "app.api.v1.public.uploads.enforce_upload_rate_limit", lambda db, actor, ip: None
    )

    async def fake_upload(file):
        return {
            "path": "temporary-uploads/0123456789abcdef0123456789abcdef.jpg",
            "url": "https://cdn.example.test/temporary-uploads/0123456789abcdef0123456789abcdef.jpg",
            "filename": "0123456789abcdef0123456789abcdef.jpg",
            "content_type": "image/jpeg",
            "bytes": 123,
        }

    monkeypatch.setattr("app.api.v1.public.uploads.upload_file_to_cdn", fake_upload)
    try:
        response = client.post(
            "/api/v1/public/files/upload",
            files={"file": ("photo.jpg", image_bytes(), "image/jpeg")},
        )
    finally:
        client.app.dependency_overrides.pop(get_current_actor, None)
    assert response.status_code == 201
    assert response.json()["message"] == "File uploaded successfully"
    assert response.json()["data"]["bytes"] == 123


def test_upload_route_returns_429(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    client.app.dependency_overrides[get_current_actor] = lambda: (
        SimpleNamespace(id=uuid.uuid4()), "CUSTOMER"
    )

    def limited(db, actor, ip):
        raise HTTPException(status_code=429, detail="Upload rate limit exceeded")

    monkeypatch.setattr("app.api.v1.public.uploads.enforce_upload_rate_limit", limited)
    response = client.post(
        "/api/v1/public/files/upload",
        files={"file": ("photo.jpg", image_bytes(), "image/jpeg")},
    )
    client.app.dependency_overrides.pop(get_current_actor, None)
    assert response.status_code == 429