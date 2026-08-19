from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from app.core.config import settings

# Full access to send emails on behalf of user
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def main():
  flow = InstalledAppFlow.from_client_secrets_file(settings.GMAIL_CREDENTIALS_FILE, SCOPES)
  # Replace flow.run_local_server(port=0) with:
  creds = flow.run_local_server(
    port=8080,
    access_type="offline",
    prompt="consent",
  )

  Path(settings.GMAIL_TOKEN_FILE).write_text(creds.to_json(), encoding="utf-8")
  print(f"{settings.GMAIL_TOKEN_FILE} successfully generated!")


if __name__ == "__main__":
  main()