from typing import Dict, Any
import sys
from PyQt6.QtCore import pyqtSignal, QObject, Qt
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from pynput import keyboard
import time
from core.client_network import ClientNetworkThread
from core.password_hasher import PasswordHasher
from core.utils import UtilityFunctions, API_ENDPOINTS

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
        layout.addWidget(self.assign_btn)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def __on_api_success(self, action: str, data: Dict[str, Any]):
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

    def __on_api_failure(self, action: str, error_msg: str):
        """
        Executes safely back on the Main UI Thread ONLY when the server responds with 200 OK.
        'action' tells you which route finished. 'data' is your decoded response JSON.
        """
        print(f"Error caught on action: {action}")
        self.status_label.setText(f"Error: {error_msg}")

    def process_token(self, token_id):
        """Core execution point where tokens are caught."""
        # Update UI text in real-time2956.$16$D9bQY4I8nI5N9SUOnKGEaJX9nLRD0kEOh44Mcb8K31UjQJl4W6Tmp0U5OZFHGwaI

        self.status_label.setText(f"Last Token Processed:\n--> {token_id} <--")
        print(f"\n[BACKGROUND SCAN CAUGHT] Processing Token: {token_id}")

        self.client = ClientNetworkThread(API_ENDPOINTS["verify-qr-token-scanned-by-trainee"], token_id=token_id)
        self.client.bind_and_start(self.__on_api_success, self.__on_api_failure)
        
        # TODO: Add your SQLite/PostgreSQL count decrement logic here
        # TODO: Send formatted receipt text to the physical thermal printer

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CanteenTerminalApp()
    window.show()
    sys.exit(app.exec())