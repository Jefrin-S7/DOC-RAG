import io
import os 
import json
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, "token.pickle")
CREDENTIALS_FILE = os.path.join(BASE_DIR, os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"))

load_dotenv(os.path.join(BASE_DIR, "../.env.local"))

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

GOOGLE_DOC_TYPES = [
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
]

#auth

def get_drive_service():
    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if service_account_json:

        from google.oauth2 import service_account
        info = json.loads(service_account_json)
        creds = service_account.Credentials.from_service_account_info( info, scopes=SCOPES )
        print("[Drive] Using Sevice Account")
    
    else:

        creds = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                print("[Drive] Token Refreshed")
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                print("[Drive] OAuth login complete")
                with open(TOKEN_FILE, "wb") as token:
                    pickle.dump(creds, token)
    return build('drive', 'v3', credentials=creds)
    
#List files

def list_files_in_folder(service, folder_id: str) -> list:
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(q= query, fields="files(id, name, mimeType)").execute()
    files = results.get('files', [])

    print(f"\n[Drive] files found: {len(files)}")
    print("-" * 50)
    for f in files:
        print(f" {f['name']}")
    print("_" * 50)
    return files


#Download PDF


def download_pdf(service, file_id: str) -> bytes:
    file_info = service.files().get(fileId=file_id, fields="mimeType, name").execute()
    mime_type = file_info.get("mimeType", "")
    print(f"[Drive] Downloading: {file_info.get('name')}, flush=True")

    if mime_type in GOOGLE_DOC_TYPES:
        request = service.files().export_media(fileId=file_id, mimeType='application/pdf')
    else:
        request = service.files().get_media(fileId=file_id)

    buffer =io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        status, done =  downloader.next_chunk()
        print(f" Downloading... {int(status.progress() * 100)}%", flush=True)

    return buffer.getvalue()

#Get all pdf from folder


def get_all_pdfs(folder_id: str) -> list:

    service = get_drive_service()
    files = list_files_in_folder(service, folder_id)

    pdf_files = [f for f in files if 'pdf' in f['mimeType'] or f['mimeType'] in GOOGLE_DOC_TYPES]

    if not pdf_files:
        print("[Drive] No PDF files found!")
        return []

    results = []
    for pdf in pdf_files:
        pdf_bytes = download_pdf(service, pdf['id'])
        results.append({
            "id": pdf["id"],
            "name": pdf["name"], 
            "bytes": pdf_bytes,
        })
    return results


if __name__ == "__main__":
    FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    print(f"Connecting to Google Drive...")
    print(f"Folder: {FOLDER_ID}")

    service = get_drive_service()
    files = list_files_in_folder(service, FOLDER_ID)
    pdf_files = [
        f for f in files
        if "pdf" in f["mimeType"] or f["mimeType"] in GOOGLE_DOC_TYPES
    ]
    print(f"\nPDF files: {len(pdf_files)}")
    for f in pdf_files:
        print(f" {f['name']}")