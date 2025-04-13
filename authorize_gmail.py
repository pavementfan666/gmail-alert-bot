from __future__ import print_function
import os.path
import pickle
import json

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these SCOPES, delete token.json
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    creds = None
    if os.path.exists('token.json'):
        print("Token already exists. Delete it if you want to re-authenticate.")
        return

    # Load credentials.json
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)

    # Save the token
    with open('token.json', 'w') as token:
        token.write(creds.to_json())
    print("✅ token.json has been generated!")

if __name__ == '__main__':
    main()