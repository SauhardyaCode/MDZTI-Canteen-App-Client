import sys
from PyQt6.QtCore import pyqtSignal, QObject, Qt, QThread
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from pynput import keyboard
import time
import os
import requests
from dotenv import load_dotenv
from password_hasher import PasswordHasher
from datetime import datetime
import re

API_ENDPOINTS = {"configure-settings-key-value-pair": "configure-settings",
                 "generate-new-physical-qr-token": "generate-new-token",
                 "assign-existing-token-to-trainee": "assign-token",
                 "verify-qr-token-scanned-by-trainee": "verify-token",}

class ClientNetworkThread(QThread):
    operation_success = pyqtSignal(str, dict) # action name, res_json
    operation_failed = pyqtSignal(str, str) # action name, error_msg

    def __init__(self, action: str, **kwargs):
        super().__init__()
        self.action = action
        self.payload = kwargs or {}

        load_dotenv()
        self.__SERVER_URL = os.getenv("SERVER_URL")
        self.__API_BASE_URL = f"{self.__SERVER_URL}/api"
        self.__SECRET_KEY = os.getenv("MUTUAL_SECRET_KEY")
        self.__hasher = PasswordHasher()
    
    def run(self):
        headers = self.__generate_security_headers()

        if self.action in API_ENDPOINTS.values():
            try:
                endpoint = self.__API_BASE_URL + "/" + self.action                    
                response = requests.post(endpoint, headers=headers, params=self.payload, timeout=10.0)

                print(response.text)

                if response.status_code == 200:
                    self.operation_success.emit(self.action, response.json())
                else:
                    error_detail = response.json().get("detail", "Central Node server rejected access constraints.")
                    self.operation_failed.emit(self.action, f"[{response.status_code}] {error_detail}")

            except requests.exceptions.Timeout:
                self.operation_failed.emit(self.action, "Network Timeout: Central Node server is taking too long to respond.")
            except requests.exceptions.RequestException as e:
                self.operation_failed.emit(self.action, f"Network Link Error: {str(e)}")
        
        else:
            self.operation_failed.emit(self.action, f"Invalid API endpoint requested")


    def __generate_security_headers(self) -> dict:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        combined_payload = f"{self.__SECRET_KEY}||{timestamp}"
        network_signature = self.__hasher.create_hash(combined_payload)

        return {
            "x-app-timestamp": timestamp,
            "x-app-signature": network_signature,
            "Content-Type": "application/json"
        }

# ==========================================
# 1. THREAD-SAFE GLOBAL KEYBOARD LISTENER
# ==========================================
class GlobalScanSignalEmitter(QObject):
    """Safely forwards global keystrokes to the PyQt6 GUI thread."""
    scan_completed = pyqtSignal(str)

class GlobalScannerListener:
    def __init__(self, emitter):
        self.emitter = emitter
        self.buffer = []
        self.scan_start_time = None  # Track when the scan begins
        
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()

    def on_press(self, key):
        try:
            # Start timing on the very first character of a potential scan
            if not self.buffer:
                self.scan_start_time = time.time()

            if key == keyboard.Key.enter:
                token = "".join(self.buffer).strip()
                
                if token:
                    # Calculate total time taken to input the string
                    elapsed_time = time.time() - self.scan_start_time
                    
                    # Industrial scanners easily dump data under 0.1 seconds (100ms)
                    # If it takes longer, it's a human typing—ignore it to prevent buffer corruption!
                    if elapsed_time < 0.15: 
                        self.emitter.scan_completed.emit(token)
                    else:
                        print(f"[REJECTED] Input took too long ({elapsed_time:.2f}s). Likely human typing.")
                        
                self.buffer = [] # Reset
                self.scan_start_time = None
                
            elif hasattr(key, 'char') and key.char is not None:
                self.buffer.append(key.char)
                
            elif hasattr(key, 'vk') and 96 <= key.vk <= 105:
                self.buffer.append(str(key.vk - 96))
                
        except Exception as e:
            print(f"Listener error: {e}")

# ==========================================
# 2. THE MAIN CANTEEN TERMINAL GUI
# ==========================================
class CanteenTerminalApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
        # Initialize our global interceptor safely
        self.signal_emitter = GlobalScanSignalEmitter()
        self.signal_emitter.scan_completed.connect(self.process_token)
        self.background_listener = GlobalScannerListener(self.signal_emitter)
        self.__hasher = PasswordHasher()

    def init_ui(self):
        self.setWindowTitle("Canteen Terminal Middleware")
        self.resize(450, 220)
        
        # Styling the window clean and functional
        layout = QVBoxLayout()
        
        self.title_label = QLabel("<b>CANTEEN STATUS: ACTIVE</b>", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        self.status_label = QLabel("Ready for input...\nYou can freely minimize or background this window.", self)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #555; font-size: 13px;")
        layout.addWidget(self.status_label)

        self.generate_btn = QPushButton("Generate Token", self)
        self.generate_btn.clicked.connect(self.generate_token)
        layout.addWidget(self.generate_btn)

        self.assign_btn = QPushButton("Assign Token", self)
        self.assign_btn.clicked.connect(lambda checked: self.assign_token("2956/16", "Dhreet Haldar", "GS/MDZTI", "2026-06-15", "2026-07-10", "non-veg"))
        layout.addWidget(self.assign_btn)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def __on_api_success(self, action: str, data: dict):
        """
        Executes safely back on the Main UI Thread ONLY when the server responds with 200 OK.
        'action' tells you which route finished. 'data' is your decoded response JSON.
        """
        print(f"Success caught for action: {action}")
        
        if action == API_ENDPOINTS["verify-qr-token-scanned-by-trainee"]:
            # Read the student details returned by your unified query parameters server endpoint
            student_name = data.get("trainee_name", "Trainee")
            meal = data.get("meal_preference", "Veg")
            
            self.status_label.setText(f"✅ APPROVED\nWelcome, {student_name}!\nMeal: {meal}")
            # Run thermal printing logic here...
        
        elif action == API_ENDPOINTS["generate-new-physical-qr-token"]:
            token_no = data.get("token_id_no")
            token_id_qr = data.get("final_token_id")
            token_id_card = f"{token_no}/{re.findall(r"\$(\d+)\$", token_id_qr)[0]}"

            print("Token ID genarated (for QR):", token_id_qr)
            print("Token ID:", token_id_card)
        
        elif action == API_ENDPOINTS["assign-existing-token-to-trainee"]:
            print(f"Assigned Token No. ({data.get("token_id")}) to Trainee")
            del data["status"]
            del data["token_id"]
            print("Trainee Data:", data)

    def __on_api_failure(self, action: str, error_msg: str):
        """
        Executes safely back on the Main UI Thread ONLY when the server responds with 200 OK.
        'action' tells you which route finished. 'data' is your decoded response JSON.
        """
        print(f"Error caught on action: {action}")
        self.status_label.setText(f"Error: {error_msg}")
    
    def __bind_client(self):
        self.client.operation_success.connect(self.__on_api_success)
        self.client.operation_failed.connect(self.__on_api_failure)

    def generate_token(self):
        print("Generating a new QR Token ID...")
        self.client = ClientNetworkThread(API_ENDPOINTS["generate-new-physical-qr-token"])
        self.__bind_client()
        self.client.start()

    def assign_token(
            self,
            token_id_card: str,
            trainee_name: str,
            trainee_desg: str,
            course_start: str,
            course_end: str,
            meal_preference: str,
            alloted_room_number: str = ""
    ):
        token_no, token_hash_code = token_id_card.split('/')
        token_hash = self.__hasher.generate_particular_hash(token_no, int(token_hash_code))
        token_id = f"{token_no}.{token_hash}"
        self.client = ClientNetworkThread(API_ENDPOINTS["assign-existing-token-to-trainee"], token_id=token_id,
                                          trainee_name=trainee_name, trainee_desg=trainee_desg,
                                          course_start=course_start, course_end=course_end,
                                          meal_preference=meal_preference, alloted_room_number=alloted_room_number
                                        )
        self.__bind_client()
        self.client.start()

    def process_token(self, token_id):
        """Core execution point where tokens are caught."""
        # Update UI text in real-time2956.$16$D9bQY4I8nI5N9SUOnKGEaJX9nLRD0kEOh44Mcb8K31UjQJl4W6Tmp0U5OZFHGwaI

        self.status_label.setText(f"Last Token Processed:\n--> {token_id} <--")
        print(f"\n[BACKGROUND SCAN CAUGHT] Processing Token: {token_id}")

        self.client = ClientNetworkThread(API_ENDPOINTS["verify-qr-token-scanned-by-trainee"], token_id=token_id)
        self.__bind_client()
        self.client.start()
        
        # TODO: Add your SQLite/PostgreSQL count decrement logic here
        # TODO: Send formatted receipt text to the physical thermal printer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CanteenTerminalApp()
    window.show()
    sys.exit(app.exec())