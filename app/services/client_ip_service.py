from fastapi import Request


def get_client_ip(request: Request) -> str | None:
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip and cf_ip.strip():
        return cf_ip.strip()

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        forwarded_ip = forwarded.split(",", 1)[0].strip()
        if forwarded_ip:
            return forwarded_ip

    real_ip = request.headers.get("X-Real-IP")
    if real_ip and real_ip.strip():
        return real_ip.strip()

    return request.client.host if request.client else None