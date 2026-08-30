"""Secret Manager - Manages environment variables and credentials for Step 2."""
import base64
import json
import os
from typing import Optional, Dict, Any, List


class SecretManager:
    """Manages User OAuth2, Service Accounts, and API Keys."""

    @staticmethod
    def get_spreadsheet_id() -> str:
        return os.environ.get("SPREADSHEET_ID", "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0")

    @staticmethod
    def get_user_oauth2_dict() -> Optional[Dict[str, Any]]:
        raw_b64 = os.environ.get("USER_OAUTH2_BASE64", "")
        if raw_b64:
            try:
                return json.loads(base64.b64decode(raw_b64).decode("utf-8"))
            except Exception:
                pass
        local_path = "/Users/hanario/Documents/lelehoctiengtrung/Pipeline_lelehoctiengtrung/gitignore/user_oauth2.json"
        if os.path.exists(local_path):
            try:
                with open(local_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return None

    @staticmethod
    def get_gcp_service_account_dict() -> Optional[Dict[str, Any]]:
        raw_b64 = os.environ.get("GCP_SERVICE_ACCOUNT_BASE64", "")
        if raw_b64:
            try:
                return json.loads(base64.b64decode(raw_b64).decode("utf-8"))
            except Exception:
                pass
        return None

    @staticmethod
    def get_gemini_api_keys() -> List[str]:
        raw = os.environ.get("GEMINI_API_KEYS") or os.environ.get("GEMINI_API_KEY", "")
        return [k.strip() for k in raw.replace("\n", ",").split(",") if k.strip()]

    @staticmethod
    def get_openrouter_api_keys() -> List[str]:
        raw = os.environ.get("OPENROUTER_API_KEYS") or os.environ.get("OPENROUTER_API_KEY", "")
        return [k.strip() for k in raw.replace("\n", ",").split(",") if k.strip()]
