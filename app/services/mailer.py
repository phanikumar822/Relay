from email.message import EmailMessage
import aiosmtplib
from app.core.config import settings

async def send_event_digest(recipient_email: str, events: list, username: str = ""):
    if not events:
        return

    high_priority = [e for e in events if e.get("priority") == "HIGH"]
    med_priority = [e for e in events if e.get("priority") == "MEDIUM"]
    low_priority = [e for e in events if e.get("priority") == "LOW"]

    def build_items(items):
        if not items:
            return "<p><em>Nothing as of now I'll update you as they are available enjoy the day</em></p>"
        html = "<ul>"
        for item in items:
            html += f"""
            <li style="margin-bottom: 10px;">
                <strong><a href="{item.get('url')}">{item.get('title')}</a></strong><br/>
                <span>Organizer: {item.get('organizer', 'N/A')} | Date: {item.get('date', 'N/A')}</span><br/>
                <span>{item.get('summary', '')}</span>
            </li>
            """
        html += "</ul>"
        return html

    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #222;">
            <h2>Hey {username}! Hope You're Good</h2>
            <p>Here are the latest events we found matching your request:</p>
            <h3 style="color: #d9381e;">1) High Priority</h3>
            {build_items(high_priority)}
            <h3 style="color: #e67e22;">2) Medium Priority</h3>
            {build_items(med_priority)}
            <h3 style="color: #7f8c8d;">3) Low Priority</h3>
            {build_items(low_priority)}
        </body>
    </html>
    """

    if getattr(settings, "RESEND_API_KEY", None) and settings.RESEND_API_KEY.strip():
        import httpx
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY.strip()}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": "Relay <onboarding@resend.dev>",
                    "to": [recipient_email],
                    "subject": f"Welcome {len(events)} New Events Found",
                    "html": html_content
                },
                timeout=12.0
            )
            if res.status_code >= 400:
                raise RuntimeError(f"Resend HTTP error ({res.status_code}): {res.text}")
            return

    message = EmailMessage()
    message["From"] = settings.SMTP_USER
    message["To"] = recipient_email
    message["Subject"] = f"Welcome {len(events)} New Events Found"
    message.set_content(html_content, subtype="html")

    use_ssl = int(settings.SMTP_PORT) == 465
    start_tls = int(settings.SMTP_PORT) == 587

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=int(settings.SMTP_PORT),
        start_tls=start_tls,
        use_tls=use_ssl,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        timeout=12
    )
