from typing import Callable, Dict, Any
from PyQt6.QtCore import pyqtSignal, QThread, QObject
from dotenv import load_dotenv
import os
import requests
from core.password_hasher import PasswordHasher
from core.utils import UtilityFunctions, API_ENDPOINTS

class ClientNetworkThread(QThread):
    operation_success = pyqtSignal(str, dict) # action name, res_json
    operation_failed = pyqtSignal(str, str) # action name, error_msg
    __utilities = UtilityFunctions()

    def __init__(self, parent: QObject, action: str, request_type: str, **kwargs) -> None:
        super().__init__(parent)
        self.finished.connect(self.deleteLater)
        
        self.action = action
        self.request_type = request_type
        self.payload = kwargs or {}

        load_dotenv()
        self.__SERVER_URL = os.getenv("SERVER_URL")
        self.__API_BASE_URL = f"{self.__SERVER_URL}/api"
        self.__SECRET_KEY = os.getenv("MUTUAL_SECRET_KEY")
        self.__hasher = PasswordHasher()
    
    def run(self) -> None:
        headers = self.__generate_security_headers()

        if self.action in API_ENDPOINTS.values():
            try:
                endpoint = self.__API_BASE_URL + "/" + self.action
                if self.request_type == "POST":
                    response = requests.post(endpoint, headers=headers, params=self.payload, timeout=10.0)
                elif self.request_type == "GET":
                    response = requests.get(endpoint, headers=headers, timeout=10.0)

                if response.status_code == 200:
                    self.operation_success.emit(self.action, response.json())
                else:
                    error_detail = response.json().get("detail", "Central Node server rejected access constraints.")
                    self.operation_failed.emit(self.action, f"[{response.status_code}] {error_detail}")
            except requests.exceptions.Timeout:
                self.operation_failed.emit(self.action, "Network Timeout: Central Node server is taking too long to respond.")
                self.run()
            except requests.exceptions.RequestException as e:
                self.operation_failed.emit(self.action, f"Network Link Error: {str(e)}")
        
        else:
            self.operation_failed.emit(self.action, f"Invalid API endpoint requested")

    def __generate_security_headers(self) -> dict:
        timestamp = self.__utilities.get_current_ist_datetime().strftime("%Y-%m-%d %H:%M:%S")
        combined_payload = f"{self.__SECRET_KEY}||{timestamp}"
        network_signature = self.__hasher.create_hash(combined_payload)

        return {
            "x-app-timestamp": timestamp,
            "x-app-signature": network_signature,
            "Content-Type": "application/json"
        }
    
    def bind_and_start(
        self,
        success_coroutine: Callable[[str, Dict[str, Any]], None],
        failure_coroutine: Callable[[str, str], None],
    ):
        self.operation_success.connect(success_coroutine)
        self.operation_failed.connect(failure_coroutine)
        self.start()
        self.finished.connect(self.deleteLater)