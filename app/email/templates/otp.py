import html


def render_otp_email(otp: str, expires_in_minutes: int) -> tuple[str, str]:
    text_body = (
        f"Your Gantabyaa verification code is: {otp}\n\n"
        f"This code expires in {expires_in_minutes} minute(s).\n\n"
        "If you did not request this email, you can ignore it."
    )
    safe_otp = html.escape(otp)
    html_content = (
        '<h1 style="margin:0 0 12px;color:#183b4e;font-size:24px;line-height:1.3;">'
        'Your verification code</h1>'
        '<p style="margin:0 0 24px;color:#52666d;font-size:15px;line-height:1.6;">'
        'Use this one-time code to complete the action you requested with Gantabyaa.</p>'
        '<div style="margin:0 0 22px;padding:20px 12px;background:#eef5f2;'
        'border:1px solid #d9e8e1;border-radius:6px;text-align:center;">'
        f'<div style="color:#183b4e;font-size:32px;font-weight:700;'
        f'letter-spacing:6px;line-height:1.3;">{safe_otp}</div></div>'
        f'<p style="margin:0 0 16px;color:#52666d;font-size:14px;line-height:1.6;">'
        f'This code expires in <strong>{expires_in_minutes} minute(s)</strong>. '
        'For your security, do not share it with anyone.</p>'
        '<p style="margin:0;color:#87928e;font-size:13px;line-height:1.6;">'
        'If you did not request this email, you can safely ignore it.</p>'
    )
    return text_body, html_content