from PyQt6.QtCore import pyqtSignal, QObject
from pynput import keyboard
import time

class ScannerManager(QObject):
    # Connected slots in your CanteenWindow UI will execute safely on the Main UI Thread
    scan_completed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.buffer = []
        self.scan_start_time = None  
        self.last_key_time = None  # Track time between consecutive keystrokes
        
        # Start the background keyboard intercept hook
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()

    def on_press(self, key):
        try:
            current_time = time.time()

            # --- STALE BUFFER EXPIRATION ---
            # If the last keystroke was more than 1.0 second ago, a human likely typed 
            # something earlier and left it. Clear it completely to prevent corruption!
            if self.buffer and self.last_key_time and (current_time - self.last_key_time > 1.0):
                self.buffer = []
                self.scan_start_time = None

            self.last_key_time = current_time

            # Start timing on the absolute first character of an entry sequence
            if not self.buffer:
                self.scan_start_time = current_time

            # --- HANDLE TERMINATION RULE (ENTER KEY) ---
            if key == keyboard.Key.enter:
                token = "".join(self.buffer).strip()
                
                if token:
                    elapsed_time = current_time - self.scan_start_time
                    
                    # Scanners easily dump 20+ chars in < 50ms. 0.15s (150ms) is safe and solid.
                    if elapsed_time < 0.15: 
                        # FIX 1: Fixed attribute reference crash name
                        self.scan_completed.emit(token) 
                    else:
                        print(f"[REJECTED] Input took too long ({elapsed_time:.2f}s). Rejected as human entry.")
                        
                # Ensure state is reset completely on EVERY enter loop
                self.buffer = [] 
                self.scan_start_time = None
                
            # --- HANDLE REGULAR CHARACTERS ---
            elif hasattr(key, 'char') and key.char is not None:
                self.buffer.append(key.char)
                
            # --- HANDLE NUMPAD KEYS (Windows Virtual Keys fallback) ---
            elif hasattr(key, 'vk') and 96 <= key.vk <= 105:
                self.buffer.append(str(key.vk - 96))
                
            # --- PROTECT AGAINST MANUALLY MODIFIED INTERRUPTS ---
            elif key in (keyboard.Key.backspace, keyboard.Key.delete, keyboard.Key.esc):
                # If a human edits input, instantly purge the buffer to prevent scanner corruption
                self.buffer = []
                self.scan_start_time = None

        except Exception as e:
            print(f"Scanner Listener Error Exception caught: {e}")

    def stop_listener(self):
        """Always stop the background keyboard hook thread clean when closing the window!"""
        if self.listener:
            self.listener.stop()