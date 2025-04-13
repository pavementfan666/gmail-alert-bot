import os
import base64
import json
import logging
import datetime
import pytz
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import requests

# Setup logging
logging.basicConfig(level=logging.INFO)

# Load credentials/token from environment secrets
creds_data = os.environ.get("GMAIL_CREDENTIALS")
token_data = os.environ.get("GMAIL_TOKEN_JSON")

if not creds_data or not token_data:
    logging.error("Missing Gmail API credentials or token in environment.")
    exit(1)

# Write them to temporary files (Google client needs real file paths)
with open("credentials_temp.json", "w") as f:
    f.write(creds_data)

with open("token_temp.json", "w") as f:
    f.write(token_data)

# Load credentials
creds = Credentials.from_authorized_user_file("token_temp.json", ["https://www.googleapis.com/auth/gmail.readonly"])

# Build Gmail service
service = build("gmail", "v1", credentials=creds)

def get_unread_messages():
    try:
        result = service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=5).execute()
        messages = result.get('messages', [])
        return messages
    except Exception as e:
        logging.error(f"Error fetching messages: {e}")
        return []

def get_recent_emails():
    los_angeles_tz = pytz.timezone('America/Los_Angeles')
    now_la = datetime.datetime.now(los_angeles_tz)
    two_hours_ago_la = now_la - datetime.timedelta(hours=2)

    now_utc = now_la.astimezone(pytz.utc)
    two_hours_ago_utc = two_hours_ago_la.astimezone(pytz.utc)

    after_ts = int(two_hours_ago_utc.timestamp())
    before_ts = int(now_utc.timestamp())

    print(f"Querying emails received between:\n  {two_hours_ago_utc} (timestamp: {after_ts})\n  {now_utc} (timestamp: {before_ts})")

    allowed_senders = ['dominicchavarria@icloud.com', 'redlabfungi@gmail.com']
    query = f"after:{after_ts} before:{before_ts} ({' OR '.join([f'from:{addr}' for addr in allowed_senders])})"
    #query = f"after:{after_ts} before:{before_ts}"
    results = service.users().messages().list(userId='me', q=query).execute()
    
    message_refs = results.get('messages') or []
    email_data = []

    for message in message_refs:
        message_id = message.get('id')
        if not message_id:
            continue

        msg = service.users().messages().get(userId='me', id=message_id).execute()
        headers = msg.get("payload", {}).get("headers", [])
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        from_field = next((h["value"] for h in headers if h["name"] == "From"), "Unknown sender")
        received_ts = int(msg['internalDate']) / 1000
        received_dt_la = datetime.datetime.fromtimestamp(received_ts, los_angeles_tz)
        email_data.append({
            'message_id': msg['id'],
            'subject': subject,
            'from': from_field,
            'received_at': received_dt_la.strftime('%Y-%m-%d %I:%M %p'),
            'received_at_dt': received_dt_la,
        })

    return email_data




def send_telegram_alert(message):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_ids_raw = os.environ.get("TELEGRAM_CHAT_ID", "")
    
    # Support single ID or comma-separated list
    chat_ids = [cid.strip() for cid in chat_ids_raw.split(",") if cid.strip()]

    if not bot_token or not chat_ids:
        logging.error("Missing Telegram credentials or chat IDs.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    for chat_id in chat_ids:
        payload = {"chat_id": chat_id, "text": message}
        r = requests.post(url, data=payload)

        if r.status_code != 200:
            logging.error(f"Telegram failed for {chat_id}: {r.text}")

def main():
    messages = get_recent_emails()
    if not messages:
        logging.info("No recent messages.")
        return

    for msg in messages:
        alert_msg = f"📬 New Email:\nFrom: {msg['from']}\nSubject: {msg['subject']}\nReceived: {msg['received_at']}"
        send_telegram_alert(alert_msg)

if __name__ == "__main__":
    main()