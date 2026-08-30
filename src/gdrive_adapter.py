"""Google Drive Adapter for Step 2 - Uploads Audio.zip and Stroke assets."""
import io
import json
import logging
from typing import Dict, Any, Optional
from src.secret_manager import SecretManager

logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/drive"]


class GDriveAdapter:
    """Handles GDrive interactions for Step 2 assets."""

    def __init__(self):
        self.service = None
        self._authenticate()

    def _authenticate(self) -> None:
        try:
            from googleapiclient.discovery import build
            oauth_dict = SecretManager.get_user_oauth2_dict()
            sa_dict = SecretManager.get_gcp_service_account_dict()
            if oauth_dict:
                from google.oauth2.credentials import Credentials as UserCredentials
                creds = UserCredentials(
                    token=None,
                    refresh_token=oauth_dict.get("refresh_token"),
                    token_uri=oauth_dict.get("token_uri", "https://oauth2.googleapis.com/token"),
                    client_id=oauth_dict.get("client_id"),
                    client_secret=oauth_dict.get("client_secret"),
                    scopes=SCOPES
                )
                self.service = build("drive", "v3", credentials=creds)
                logger.info("Authenticated with Google Drive API v3 (User OAuth2).")
            elif sa_dict:
                from google.oauth2.service_account import Credentials as SACredentials
                creds = SACredentials.from_service_account_info(sa_dict, scopes=SCOPES)
                self.service = build("drive", "v3", credentials=creds)
                logger.info("Authenticated with Google Drive API v3 (Service Account).")
        except Exception as e:
            logger.warning(f"GDrive auth error: {e}")

    def upload_file_from_disk(self, local_path: str, filename: str, folder_id: str, mime_type: str) -> Dict[str, str]:
        if not self.service:
            return {"id": f"id_{filename}", "url": f"https://drive.google.com/file/d/id_{filename}/view"}
        try:
            from googleapiclient.http import MediaFileUpload
            meta = {"name": filename, "parents": [folder_id]}
            media = MediaFileUpload(local_path, mimetype=mime_type, resumable=True)
            res = self.service.files().create(body=meta, media_body=media, fields="id, webViewLink", supportsAllDrives=True).execute()
            fid = res.get("id")
            furl = res.get("webViewLink", f"https://drive.google.com/file/d/{fid}/view?usp=drivesdk")
            logger.info(f"Uploaded '{filename}' to GDrive folder {folder_id} -> ID: {fid}")
            return {"id": fid, "url": furl}
        except Exception as e:
            logger.error(f"Failed to upload '{filename}': {e}")
            return {"id": "", "url": ""}

    def download_config_json(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """Finds and reads config.json in the character's GDrive folder."""
        if not self.service:
            return None
        try:
            q = f"'{folder_id}' in parents and name = 'config.json' and trashed = false"
            res = self.service.files().list(q=q, fields="files(id, name)", supportsAllDrives=True).execute()
            files = res.get("files", [])
            if not files:
                return None
            fid = files[0]["id"]
            content = self.service.files().get_media(fileId=fid, supportsAllDrives=True).execute()
            return json.loads(content.decode("utf-8"))
        except Exception as e:
            logger.warning(f"Download config.json note: {e}")
            return None
