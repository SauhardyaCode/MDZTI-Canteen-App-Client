from datetime import datetime, timedelta, timezone
from PyQt6.QtWidgets import QMessageBox

POST = "POST"
GET = "GET"

API_ENDPOINTS = {
    "configure-settings-key-value-pair": "configure-settings",
    "generate-new-physical-qr-token": "generate-new-token",
    "assign-existing-token-to-trainee": "assign-token",
    "verify-qr-token-scanned-by-trainee": "verify-token",
    "fetch-physical-token-stats": "get-existing-token-stats",
    "fetch-available-token-list": "get-available-tokens",
    "fetch-active-trainee-list": "get-trainee-list",
    "change-course-interval-of-trainees": "change-course-interval"
}

class UtilityFunctions:
    def get_current_ist_datetime(self) -> datetime:
        aware_current_time_utc = datetime.now(timezone.utc)
        aware_current_time_ist = aware_current_time_utc + timedelta(hours=5, minutes=30)
        current_time_ist = aware_current_time_ist.replace(tzinfo=None)
        return current_time_ist
    
    def api_failure_coroutine(self, action: str, error_msg: str) -> None:
        print(f"Error caught on action: {action}")
        print(f"Error: {error_msg}")
        # error_title = error_msg.split(":")[0].strip()
        # QMessageBox.warning(None, error_title, f"{error_title}! Try reopening the panel or the app!", QMessageBox.StandardButton.Ok)