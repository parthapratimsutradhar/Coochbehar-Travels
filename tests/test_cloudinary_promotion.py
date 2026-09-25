import httpx
import pytest
import cloudinary.uploader
from app.core.config import settings
from app.services.cloudinary_service import (
    extract_cloudinary_asset_info,
    promote_cloudinary_asset,
    upload_content_to_cloudinary,
)


@pytest.mark.anyio
async def test_upload_content_to_cloudinary_includes_signed_account_defaults(monkeypatch):
    monkeypatch.setattr(settings, "CLOUDINARY_CLOUD_NAME", "demo-cloud")
    monkeypatch.setattr(settings, "CLOUDINARY_API_KEY", "test-key")
    monkeypatch.setattr(settings, "CLOUDINARY_API_SECRET", "test-secret")

    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"secure_url": "https://res.cloudinary.com/demo-cloud/raw/upload/abc.pdf", "public_id": "abc"}

    async def fake_post(self, url, data, files):
        captured["url"] = url
        captured["data"] = data
        captured["files"] = files
        return FakeResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await upload_content_to_cloudinary(
        content=b"%PDF-1.4\n",
        filename="test.pdf",
        content_type="application/pdf",
        sub_folder="temporary-uploads/quotations",
    )

    assert result["secure_url"].startswith("https://res.cloudinary.com/demo-cloud/")
    assert captured["data"]["access_mode"] == "public"
    assert captured["data"]["public_id_prefix"] == "Coochbehar-travels/temporary-uploads/quotations"
    assert captured["data"]["folder"] == "Coochbehar-travels/temporary-uploads/quotations"


def test_extract_cloudinary_asset_info():
    # Temporary image URL
    temp_url = "https://res.cloudinary.com/testcloud/image/upload/v1726000000/Coochbehar-travels/temporary-uploads/temp-photo-123.jpg"
    info = extract_cloudinary_asset_info(temp_url)
    assert info["is_temporary"] is True
    assert info["public_id"] == "Coochbehar-travels/temporary-uploads/temp-photo-123"
    assert info["resource_type"] == "image"

    # Temporary video URL
    video_url = "https://res.cloudinary.com/testcloud/video/upload/v1726000000/Coochbehar-travels/temporary-uploads/temp-vid-456.mp4"
    info = extract_cloudinary_asset_info(video_url)
    assert info["is_temporary"] is True
    assert info["public_id"] == "Coochbehar-travels/temporary-uploads/temp-vid-456"
    assert info["resource_type"] == "video"

    # Already permanent URL
    perm_url = "https://res.cloudinary.com/testcloud/image/upload/v1726000000/Coochbehar-travels/tour-packages/tour-1.jpg"
    info = extract_cloudinary_asset_info(perm_url)
    assert info["is_temporary"] is False
    assert info["public_id"] == "Coochbehar-travels/tour-packages/tour-1"

    # Raw PDF URL
    raw_url = "https://res.cloudinary.com/testcloud/raw/upload/v1726000000/Coochbehar-travels/temporary-uploads/doc-passport.pdf"
    info = extract_cloudinary_asset_info(raw_url)
    assert info["is_temporary"] is True
    assert info["public_id"] == "Coochbehar-travels/temporary-uploads/doc-passport.pdf"
    assert info["resource_type"] == "raw"

    # External URL
    external_url = "https://images.unsplash.com/photo-1506744038136-46273834b3fb"
    info = extract_cloudinary_asset_info(external_url)
    assert info["is_temporary"] is False
    assert info["public_id"] is None

    # Empty / None
    assert extract_cloudinary_asset_info(None)["public_id"] is None
    assert extract_cloudinary_asset_info("")["public_id"] is None


@pytest.mark.anyio
async def test_promote_cloudinary_asset_skips_external_and_permanent():
    external = "https://external.com/photo.jpg"
    res = await promote_cloudinary_asset(external, "destination-images")
    assert res["url"] == external

    permanent = "https://res.cloudinary.com/testcloud/image/upload/v1726000000/Coochbehar-travels/destination-images/delhi.jpg"
    res = await promote_cloudinary_asset(permanent, "destination-images")
    assert res["url"] == permanent


@pytest.mark.anyio
async def test_promote_cloudinary_asset_renames_temporary_file(monkeypatch):
    called = {}

    def fake_rename(from_public_id, to_public_id, resource_type, overwrite, type):
        called["from"] = from_public_id
        called["to"] = to_public_id
        called["resource_type"] = resource_type
        return {
            "public_id": to_public_id,
            "secure_url": f"https://res.cloudinary.com/testcloud/{resource_type}/upload/v1726000000/{to_public_id}.jpg",
        }

    monkeypatch.setattr(cloudinary.uploader, "explicit", lambda **kwargs: {})
    monkeypatch.setattr(cloudinary.uploader, "rename", fake_rename)

    temp_url = "https://res.cloudinary.com/testcloud/image/upload/v1726000000/Coochbehar-travels/temporary-uploads/banner_img.jpg"
    result = await promote_cloudinary_asset(temp_url, "tour-packages")

    assert called["from"] == "Coochbehar-travels/temporary-uploads/banner_img"
    assert called["to"] == "Coochbehar-travels/tour-packages/banner_img"
    assert called["resource_type"] == "image"
    assert "Coochbehar-travels/tour-packages/banner_img" in result["url"]
    assert result["public_id"] == "Coochbehar-travels/tour-packages/banner_img"
