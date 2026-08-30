"""Google Sheets Adapter for Step 2 - Tab hanzidegushi."""
import logging
from typing import Optional, Any, Dict, List
from src.secret_manager import SecretManager

logger = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]


class SheetsAdapter:
    """Handles Google Sheets row lookups and updates Col G (Voice) & Status='Voice'."""

    def __init__(self, spreadsheet_id: Optional[str] = None):
        self.spreadsheet_id = spreadsheet_id or SecretManager.get_spreadsheet_id()
        self.client: Any = None
        self._authenticate()

    def _authenticate(self) -> None:
        try:
            import gspread
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
                self.client = gspread.authorize(creds)
                logger.info("Authenticated with Google Sheets API (User OAuth2).")
            elif sa_dict:
                from google.oauth2.service_account import Credentials as SACredentials
                creds = SACredentials.from_service_account_info(sa_dict, scopes=SCOPES)
                self.client = gspread.authorize(creds)
                logger.info("Authenticated with Google Sheets API (Service Account).")
        except Exception as e:
            logger.warning(f"Sheets auth error: {e}")

    def get_worksheet(self, tab_name: str = "hanzidegushi"):
        if not self.client or not self.spreadsheet_id:
            return None
        sh = self.client.open_by_key(self.spreadsheet_id)
        return sh.worksheet(tab_name)

    def get_row_by_index(self, row_idx: int, tab_name: str = "hanzidegushi") -> Optional[Dict[str, Any]]:
        ws = self.get_worksheet(tab_name)
        if not ws:
            return None
        try:
            vals = ws.row_values(row_idx)
            if len(vals) < 2 or not vals[1].strip():
                return None
            return {
                "row_idx": row_idx,
                "character": vals[1].strip(),
                "status": vals[3].strip() if len(vals) > 3 else "",
                "gfolder_url": vals[4].strip() if len(vals) > 4 else ""
            }
        except Exception as e:
            logger.error(f"Error reading row {row_idx}: {e}")
            return None

    def get_pending_voice_rows(self, tab_name: str = "hanzidegushi") -> List[Dict[str, Any]]:
        """Finds rows ready for Step 2 (Status == 'Script')."""
        ws = self.get_worksheet(tab_name)
        if not ws:
            return []
        try:
            all_vals = ws.get_all_values()
            ready_rows = []
            for idx, row in enumerate(all_vals[1:], start=2):
                status = row[3].strip() if len(row) > 3 else ""
                char = row[1].strip() if len(row) > 1 else ""
                gfolder = row[4].strip() if len(row) > 4 else ""
                if status == "Script" and char:
                    ready_rows.append({"row_idx": idx, "character": char, "status": status, "gfolder_url": gfolder})
            return ready_rows
        except Exception as e:
            logger.error(f"Error finding pending voice rows: {e}")
            return []

    def update_voice_complete(self, row_idx: int, voice_url: str, tab_name: str = "hanzidegushi") -> bool:
        """Updates Col G (Voice URL) and Col D (Status -> 'Voice')."""
        ws = self.get_worksheet(tab_name)
        if not ws:
            return True
        try:
            from gspread.cell import Cell
            cells = [Cell(row=row_idx, col=4, value="Voice"), Cell(row=row_idx, col=7, value=voice_url)]
            ws.update_cells(cells)
            logger.info(f"Row {row_idx} updated: Status='Voice', Col G='{voice_url}'.")
            return True
        except Exception as e:
            logger.error(f"Failed to update Voice status at row {row_idx}: {e}")
            return False
