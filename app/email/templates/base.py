import html
from urllib.parse import urlsplit

from app.email.social_links import EXPLORE_LINKS, SOCIAL_LINKS


def _social_footer() -> str:
    links = []
    for label, url in SOCIAL_LINKS:
        parsed_url = urlsplit(url) if url else None
        safe_url = (
            url
            if parsed_url and parsed_url.scheme in {"http", "https"} and parsed_url.netloc
            else None
        )
        escaped_label = html.escape(label)
        if safe_url:
            links.append(
                f'<a href="{html.escape(safe_url, quote=True)}" '
                f'style="display:inline-block;margin:0 4px 4px;color:#315c76;'
                f'text-decoration:none;white-space:nowrap">'
                f"{escaped_label}</a>"
            )
        else:
            links.append(
                f'<span style="display:inline-block;margin:0 4px 4px;color:#6b7780;'
                f'white-space:nowrap">{escaped_label}</span>'
            )

    return " ".join(links)


def _explore_footer() -> str:
    links = "&nbsp;·&nbsp;".join(
        f'<a href="{html.escape(url, quote=True)}" '
        f'style="color:#315c76;text-decoration:none;white-space:nowrap">'
        f"{html.escape(label)}</a>"
        for label, url in EXPLORE_LINKS
    )
    return f'<strong style="color:#52666d;">Explore more:</strong>&nbsp;{links}'


def render_base_email(content_html: str) -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<style>'
        'body{margin:0;padding:0;background:#f2f5f4;}'
        '.email-card{width:100%;max-width:600px;}'
        '.email-content{padding:36px 40px;}'
        '.email-footer{padding:22px 24px;}'
        '.explore-links{line-height:2.2!important;}'
        '@media only screen and (max-width:600px){'
        '.email-card{width:100%!important;}'
        '.email-content{padding:28px 22px!important;}'
        '.email-footer{padding:20px 12px!important;}'
        '.social-links{line-height:2.2!important;}'
        '}'
        '</style></head>'
        '<body style="margin:0;padding:0;background:#f2f5f4;'
        'font-family:Arial,Helvetica,sans-serif;color:#20343b;">'
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
        'border="0" style="background:#f2f5f4;"><tr><td align="center" '
        'style="padding:28px 12px;">'
        '<table role="presentation" class="email-card" width="600" cellspacing="0" '
        'cellpadding="0" border="0" style="width:100%;max-width:600px;'
        'background:#ffffff;border:1px solid #e0e8e5;border-radius:8px;overflow:hidden;">'
        '<tr><td align="center" style="padding:16px 24px;border-bottom:1px solid #e8eeeb;">'
        '<img src="cid:gantabyaa-logo" alt="Gantabyaa" width="128" height="128" '
        'style="display:block;width:128px;height:128px;max-width:100%;object-fit:contain;border:0;">'
        '</td></tr>'
        f'<tr><td class="email-content" style="padding:36px 40px;">{content_html}</td></tr>'
        '<tr><td class="email-footer" align="center" style="padding:22px 24px;'
        'background:#f7f9f8;border-top:1px solid #e8eeeb;">'
        f'<div class="social-links" style="font-size:12px;line-height:1.8;">{_social_footer()}</div>'
        f'<div class="explore-links" style="padding-top:10px;color:#87928e;font-size:12px;line-height:1.8;">{_explore_footer()}</div>'
        '<div style="padding-top:10px;color:#87928e;font-size:11px;line-height:1.5;">'
        'Gantabyaa · Travel with confidence</div>'
        '</td></tr></table></td></tr></table></body></html>'
    )


def render_plain_text_email(body: str) -> str:
    escaped_body = html.escape(body).replace("\n", "<br>")
    return f'<div style="font-size:15px;line-height:1.7;color:#34474e;">{escaped_body}</div>'


def render_detail_table(rows: tuple[tuple[str, str], ...]) -> str:
    rendered_rows = "".join(
        '<tr><td style="padding:12px 0;color:#718087;font-size:13px;'
        f'border-bottom:1px solid #e8eeeb;">{html.escape(label)}</td>'
        '<td align="right" style="padding:12px 0;color:#20343b;font-size:14px;'
        f'font-weight:600;border-bottom:1px solid #e8eeeb;">{html.escape(value)}</td></tr>'
        for label, value in rows
    )
    return (
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
        f'border="0" style="margin:0 0 20px;">{rendered_rows}</table>'
    )