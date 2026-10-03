from starlette.requests import Request

from app.services.client_ip_service import get_client_ip


def make_request(headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers or [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
        }
    )


def test_get_client_ip_prefers_cloudflare_header() -> None:
    request = make_request(
        [
            (b"cf-connecting-ip", b" 203.0.113.1 "),
            (b"x-forwarded-for", b"198.51.100.2, 10.0.0.1"),
            (b"x-real-ip", b"192.0.2.3"),
        ]
    )

    assert get_client_ip(request) == "203.0.113.1"


def test_get_client_ip_uses_first_forwarded_address() -> None:
    request = make_request(
        [(b"x-forwarded-for", b" 198.51.100.2, 10.0.0.1")]
    )

    assert get_client_ip(request) == "198.51.100.2"


def test_get_client_ip_falls_back_to_real_ip_then_socket() -> None:
    real_ip_request = make_request([(b"x-real-ip", b" 192.0.2.3 ")])
    socket_request = make_request()

    assert get_client_ip(real_ip_request) == "192.0.2.3"
    assert get_client_ip(socket_request) == "127.0.0.1"