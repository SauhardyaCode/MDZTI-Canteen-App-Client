from __future__ import annotations
from typing import Union, Dict, Any
from PyQt6.QtCore import Qt, QDate, QTime, QTimer, pyqtSignal
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QIntValidator, QShowEvent, QHideEvent, QPixmap, QResizeEvent
from datetime import datetime

import sys
from core.client_network import ClientNetworkThread
from core.cache_manager import CacheManager
from core.scanner_manager import ScannerManager
from core.utils import *
from styles import *

class SuccessStatusFrame(QFrame):
    def __init__(self, parent: CanteenWindow):
        super().__init__()
        self.__parent = parent
        self.setStyleSheet("background-color: transparent;")
        size = 50
        self.veg_logo = QPixmap("assets/veg-logo.png")
        self.veg_logo = self.veg_logo.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.non_veg_logo = QPixmap("assets/non-veg-logo.png")
        self.non_veg_logo = self.non_veg_logo.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(80)

        label = QLabel("VALID TOKEN")
        label.setStyleSheet(SUCCESS_LABEL_STYLESHEET)

        details_frame = QFrame()
        details_frame.setStyleSheet(SUCCESS_STYLESHEET)
        details_layout = QGridLayout(details_frame)
        details_layout.setSpacing(8)
        details_layout.setColumnMinimumWidth(1, 40)

        name_label = QLabel("<b>Name:</b>")
        desg_label = QLabel("<b>Desg:</b>")
        token_label = QLabel("<b>Token ID:</b>")

        self.name_value = QLabel()
        self.desg_value = QLabel()
        self.token_value = QLabel()

        details_layout.addWidget(name_label, 0, 0)
        details_layout.addWidget(self.name_value, 0, 2, alignment=Qt.AlignmentFlag.AlignRight)
        details_layout.addWidget(desg_label, 1, 0)
        details_layout.addWidget(self.desg_value, 1, 2, alignment=Qt.AlignmentFlag.AlignRight)
        details_layout.addWidget(token_label, 2, 0)
        details_layout.addWidget(self.token_value, 2, 2, alignment=Qt.AlignmentFlag.AlignRight)

        pref_frame = QFrame()
        pref_layout = QHBoxLayout(pref_frame)
        pref_layout.setSpacing(30)
        self.pref_logo = QLabel()
        self.pref_value = QLabel()
        pref_layout.addWidget(self.pref_logo)
        pref_layout.addWidget(self.pref_value)

        main_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        main_layout.addWidget(details_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(pref_frame, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        if self.pref_value.text().startswith("VEG"):
            self.__parent.right_panel_frame.setStyleSheet(SUCCESS_VEG_STYLESHEET)
        elif self.pref_value.text() == "NON-VEG":
            self.__parent.right_panel_frame.setStyleSheet(SUCCESS_NON_VEG_STYLESHEET)
    
    def setValue(self, token, name, desg, pref):
        self.token_value.setText(str(token))
        self.name_value.setText(name)
        self.desg_value.setText(desg)
        self.pref_value.setText(pref)
        if pref.startswith("VEG"):
            self.__parent.right_panel_frame.setStyleSheet(SUCCESS_VEG_STYLESHEET)
            self.pref_logo.setPixmap(self.veg_logo)
            self.pref_value.setStyleSheet("font-size: 40px; font-weight: 800; color: green;")
        else:
            self.__parent.right_panel_frame.setStyleSheet(SUCCESS_NON_VEG_STYLESHEET)
            self.pref_logo.setPixmap(self.non_veg_logo)
            self.pref_value.setStyleSheet("font-size: 40px; font-weight: 800; color: brown;")

class FailureStatusFrame(QFrame):
    def __init__(self, parent: CanteenWindow):
        super().__init__()
        self.__parent = parent
        self.setStyleSheet("background-color: transparent;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(100)

        label = QLabel("INVALID TOKEN")
        label.setStyleSheet(FAILURE_LABEL_STYLESHEET)

        status_label = QLabel("NO MEALS ALLOTED")
        status_label.setStyleSheet(FAILURE_STATUS_LABEL_STYLESHEET)

        self.details_label = QLabel()
        self.details_label.setStyleSheet("font-size: 18px;")

        main_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        main_layout.addWidget(status_label, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.details_label, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch(stretch=1)
    
    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        self.__parent.right_panel_frame.setStyleSheet(FAILURE_STYLESHEET)
    
    def setValue(self, message):
        self.details_label.setText(message)

class ManualEntryFrame(QFrame):
    token_verified = pyqtSignal(tuple)
    token_not_verified = pyqtSignal(str)

    def __init__(self, parent: CanteenWindow):
        super().__init__()
        self.__parent = parent
        self.setStyleSheet("background-color: transparent;")
        self.loading_overlay = LoadingOverlay(self.__parent.right_panel_frame, "Verifying Token ID...")
        self.worker = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(50)

        label = QLabel("Manual Entry (Scanner not working!)")
        label.setStyleSheet(HEADING_STYLESHEET)

        input_frame = QFrame()
        input_frame.setStyleSheet(GENERATE_PANEL_INPUT_STYLESHEET + GENERATE_PANEL_SUBFRAME_STYLESHEET)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setSpacing(50)

        token_label = QLabel("Enter Token ID:")
        self.token_inp = QLineEdit()
        self.token_inp.setValidator(QIntValidator(1, 1000000))
        self.token_inp.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.token_inp.setMaximumWidth(150)
        self.token_inp.returnPressed.connect(self.verify_typed_token)

        input_layout.addWidget(token_label)
        input_layout.addWidget(self.token_inp)

        self.verify_btn = QPushButton("Verify")
        self.verify_btn.setStyleSheet(SUBMIT_BUTTON_STYLESHEET)
        self.verify_btn.setFixedWidth(200)
        self.verify_btn.clicked.connect(self.verify_typed_token)

        main_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        main_layout.addWidget(input_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.verify_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch(stretch=1)
    
    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        self.__parent.right_panel_frame.setStyleSheet(MANUAL_ENTRY_STYLESHEET)
        self.token_inp.setFocus()
    
    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.loading_overlay.setGeometry(self.__parent.right_panel_frame.rect())
    
    def verify_typed_token(self):
        token_number = self.token_inp.text()
        if not token_number:
            QMessageBox.warning(None, "Empty Field", "Please enter a token ID first!")
            return
        
        token_number = int(token_number)
        self.token_inp.clear()
        self.loading_overlay.show()

        if self.__parent.cache_manager.get_status() == "online":
            self.worker = ClientNetworkThread(
                self, API_ENDPOINTS["verify-qr-token-input-by-manager"], POST, 
                token_number=token_number
            )
            self.worker.bind_and_start(self.on_api_success, self.on_api_failure)
        
        else:
            data = self.__parent.verify_typed_token_offline(token_number)
            status = data.get("status")
            action = "verify-token-manual-offline"
            if status == "success":
                self.on_api_success(action=action, data=data)
            else:
                self.on_api_failure(action=action, error_msg=data.get("message"))
    
    def on_api_success(self, action: str, data: Dict[str, Any]):
        print(f"Success caught for action: {action}")
        self.loading_overlay.hide()

        token_number = data.get("token_number")
        name = data.get("trainee_name")
        desg = data.get("trainee_desg")
        pref = data.get("meal_preference")

        self.token_verified.emit((token_number, name, desg, pref))
    
    def on_api_failure(self, action: str, error_msg: str):
        self.loading_overlay.hide()
        UtilityFunctions.api_failure_coroutine(action, error_msg)
        self.token_not_verified.emit(error_msg)

class AutomaticScannerFrame(QFrame):
    token_verified = pyqtSignal(tuple)
    token_not_verified = pyqtSignal(str)

    def __init__(self, parent: CanteenWindow):
        super().__init__()
        self.__parent = parent
        self.__parent.scanner_manager.scan_completed.connect(self.verify_scanned_token)
        self.loading_overlay = LoadingOverlay(self.__parent.right_panel_frame, "Verifying Token ID...")
        self.setStyleSheet("background-color: transparent;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        status_label = QLabel("No Active Scans right now! Keep Scanning...")

        main_layout.addStretch(stretch=1)
        main_layout.addWidget(status_label, stretch=0, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addStretch(stretch=1)
    
    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        self.__parent.right_panel_frame.setStyleSheet("background-color: #dddddd;")
    
    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.loading_overlay.setGeometry(self.__parent.right_panel_frame.rect())
    
    def verify_scanned_token(self, token_id: str):
        self.loading_overlay.show()

        if self.__parent.cache_manager.get_status() == "online":
            self.worker = ClientNetworkThread(
                self, API_ENDPOINTS["verify-qr-token-scanned-by-trainee"], POST, 
                token_id=token_id
            )
            self.worker.bind_and_start(self.on_api_success, self.on_api_failure)
        
        else:
            data = self.__parent.verify_scanned_token_offline(token_id)
            status = data.get("status")
            action = "verify-token-scanned-offline"
            if status == "success":
                self.on_api_success(action=action, data=data)
            else:
                self.on_api_failure(action=action, error_msg=data.get("message"))
    
    def on_api_success(self, action: str, data: Dict[str, Any]):
        print(f"Success caught for action: {action}")
        self.loading_overlay.hide()

        token_number = data.get("token_number")
        name = data.get("trainee_name")
        desg = data.get("trainee_desg")
        pref = data.get("meal_preference")

        self.token_verified.emit((token_number, name, desg, pref))
    
    def on_api_failure(self, action: str, error_msg: str):
        self.loading_overlay.hide()
        UtilityFunctions.api_failure_coroutine(action, error_msg)
        self.token_not_verified.emit(error_msg)

class CanteenWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.online_icon = QPixmap("assets/connected.png")
        self.online_icon = self.online_icon.scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.offline_icon = QPixmap("assets/disconnected.png")
        self.offline_icon = self.offline_icon.scaled(30, 30, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        self.DISPLAY_TIMEOUT = 6000
        self.LOG_COLORS = ['pink', 'yellow', 'cyan', 'magenta', 'lightgreen']
        self.__last_log_color_idx = 0
        self.SCANNER_STATUS_TEXTS = ("Scanner not working?", "Scanner working again?")
        self.__WINDOWS = (SuccessStatusFrame, FailureStatusFrame, ManualEntryFrame, AutomaticScannerFrame)
        self.__current_window = None
        self.__active_windows = [None for _ in range(len(self.__WINDOWS))]
        self._state_manager = AppStateManager()
        
        self.state_timer = QTimer(self)
        self.state_timer.setSingleShot(True)

        self.cache_manager = CacheManager()
        self.cache_manager.connection_status_changed.connect(self.handle_network_ui_update)
        self.cache_manager.start_sync(30 * 1000) # 30s sync interval

        self.scanner_manager = ScannerManager()

        screen = QApplication.primaryScreen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()
        self.setMinimumSize(screen_width-300, screen_height-200)
        self.setWindowTitle("Canteen Manager App (Canteen)")

        main_central_widget = QWidget(self)
        main_central_widget.setStyleSheet(ROOT_STYLESHEET)
        self.setCentralWidget(main_central_widget)

        outer_layout = QVBoxLayout(main_central_widget)
        outer_layout.setContentsMargins(0,0,0,0)
        outer_layout.setSpacing(0)

        top_panel_frame = QFrame()
        top_panel_frame.setStyleSheet(PANEL_BORDER_STYLESHEET + TITLE_STYLESHEET)
        top_panel_layout = QVBoxLayout(top_panel_frame)

        label = QLabel("Canteen Manager Panel")
        top_panel_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout = QHBoxLayout()

        self.left_panel_layout = QVBoxLayout()
        self.left_panel_layout.setContentsMargins(0, 0, 0, 0)

        self.logs_frame = QFrame()
        self.logs_frame.setStyleSheet(LOGS_FRAME_STYLESHEET)
        self.logs_layout = QVBoxLayout(self.logs_frame)
        self.logs_layout.setContentsMargins(2, 2, 2, 2)

        logs_label = QLabel("Scan History (Today)")
        logs_label.setStyleSheet(SMALL_HEADING_STYLESHEET)

        logs_sub_frame = QFrame()
        logs_sub_frame.setStyleSheet(LOGS_SUB_FRAME_STYLESHEET)
        self.logs_sub_layout = QVBoxLayout(logs_sub_frame)
        self.logs_sub_layout.setContentsMargins(0, 0, 0, 0)
        # all logs appended here

        logs_scroll_area = QScrollArea()
        logs_scroll_area.setWidget(logs_sub_frame)
        logs_scroll_area.setWidgetResizable(True)

        self.no_logs_label = QLabel("No scans yet")
        self.logs_sub_layout.addWidget(self.no_logs_label, alignment=Qt.AlignmentFlag.AlignCenter)

        self.logs_layout.addWidget(logs_label, alignment=Qt.AlignmentFlag.AlignTop)
        self.logs_layout.addWidget(logs_scroll_area, stretch=4)

        self.init_scan_logs()

        self.status_frame = QFrame()
        self.status_frame.setStyleSheet(STATUS_FRAME_STYLESHEET)
        self.status_layout = QVBoxLayout(self.status_frame)
        self.status_layout.setContentsMargins(2, 2, 2, 2)

        status_label = QLabel("Meal Status")
        status_label.setStyleSheet(SMALL_HEADING_STYLESHEET)

        status_sub_frame = QFrame()
        status_sub_frame.setStyleSheet(STATUS_SUB_FRAME_STYLESHEET)
        status_sub_layout = QGridLayout(status_sub_frame)
        status_sub_layout.setColumnMinimumWidth(1, 50)

        veg_label = QLabel("<b>VEG Served:</b>")
        veg_label.setStyleSheet("color: green;")
        self.veg_served = QLabel("6")
        self.veg_total = QLabel("37")
        non_veg_label = QLabel("<b>NON-VEG Served:</b>")
        non_veg_label.setStyleSheet("color: brown;")
        self.non_veg_served = QLabel("31")
        self.non_veg_total = QLabel("74")

        status_sub_layout.addWidget(veg_label, 0, 0)
        status_sub_layout.addWidget(self.veg_served, 0, 2, alignment=Qt.AlignmentFlag.AlignRight)
        status_sub_layout.addWidget(QLabel("/"), 0, 3)
        status_sub_layout.addWidget(self.veg_total, 0, 4, alignment=Qt.AlignmentFlag.AlignRight)
        status_sub_layout.addWidget(non_veg_label, 1, 0)
        status_sub_layout.addWidget(self.non_veg_served, 1, 2, alignment=Qt.AlignmentFlag.AlignRight)
        status_sub_layout.addWidget(QLabel("/"), 1, 3)
        status_sub_layout.addWidget(self.non_veg_total, 1, 4, alignment=Qt.AlignmentFlag.AlignRight)

        self.status_layout.addWidget(status_label, alignment=Qt.AlignmentFlag.AlignTop)
        self.status_layout.addWidget(status_sub_frame)
        self.status_layout.addStretch(stretch=1)

        self.left_panel_layout.addWidget(self.logs_frame, 4)
        self.left_panel_layout.addWidget(self.status_frame, 1)

        self.right_panel_frame = QFrame()
        self.right_panel_frame.setStyleSheet(PANEL_BORDER_STYLESHEET)
        self.right_panel_layout = QVBoxLayout(self.right_panel_frame)
        self.right_panel_layout.setContentsMargins(10, 0, 10, 10)
        self.right_panel_layout.setSpacing(0)

        connection_status_frame = QFrame()
        connection_status_frame.setStyleSheet("border: none;")
        self.connection_status_layout = QHBoxLayout(connection_status_frame)
        self.connection_status_layout.setContentsMargins(0, 0, 0, 0)
        self.connection_status_img = QLabel()
        self.connection_status_text = QLabel()
        self.connection_status_layout.addWidget(self.connection_status_img)
        self.connection_status_layout.addWidget(self.connection_status_text)
        self.connection_status_layout.addStretch(stretch=1)
        self.set_online_UI()

        self.scanner_status_btn = QPushButton(self.SCANNER_STATUS_TEXTS[0])
        self.scanner_status_btn.setStyleSheet("font-size: 14px; color: blue; text-decoration: underline; background-color: #dddddd;")
        self.scanner_status_btn.clicked.connect(self.handle_scanner_status_click)

        self.right_panel_layout.addWidget(connection_status_frame, alignment=Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignTop)

        self.container_layout = QVBoxLayout()
        self.right_panel_layout.addLayout(self.container_layout)

        self.right_panel_layout.addStretch(1)
        hor_stretch_layout = QHBoxLayout()
        hor_stretch_layout.addStretch(1)
        hor_stretch_layout.addWidget(self.scanner_status_btn)
        self.right_panel_layout.addLayout(hor_stretch_layout)

        main_layout.addLayout(self.left_panel_layout, 1)
        main_layout.addWidget(self.right_panel_frame, 4)

        outer_layout.addWidget(top_panel_frame, 1)
        outer_layout.addLayout(main_layout, 9)

        self.switch_window(3)
    
    def switch_window(self, window_sl_no: int):
        if (self.__current_window != window_sl_no):
            self.__current_window = window_sl_no
            if window_sl_no == 2:
                self.scanner_status_btn.setText(self.SCANNER_STATUS_TEXTS[1])
            elif window_sl_no == 3:
                self.scanner_status_btn.setText(self.SCANNER_STATUS_TEXTS[0])

            if (self.__active_windows[window_sl_no] == None):
                newCreatedWindow = self.__WINDOWS[window_sl_no](self) # Create the class object
                self.container_layout.addWidget(newCreatedWindow)
                self.__active_windows[window_sl_no] = newCreatedWindow

                # Manual Entry Frame pyqtSignal
                if window_sl_no == 2 or window_sl_no == 3:
                    newCreatedWindow.token_verified.connect(self.show_token_status_success)
                    newCreatedWindow.token_not_verified.connect(self.show_token_status_failure)
            else:
                self.container_layout.addWidget(self.__active_windows[window_sl_no])
            
            for i in range(len(self.__WINDOWS)):
                if self.__active_windows[i]:
                    self.__active_windows[i].hide()
            self.__active_windows[window_sl_no].show()
    
    def handle_network_ui_update(self, conn_status: str):
        if conn_status == "online":
            self.set_online_UI()
        elif conn_status == "offline":
            self.set_offline_UI()
        elif conn_status == "server down":
            self.set_server_down_UI()
    
    def set_online_UI(self):
        self.connection_status_img.setPixmap(self.online_icon)
        self.connection_status_text.setText("Online")
        self.connection_status_text.setStyleSheet("color: green; font-weight: 800;")
        self.connection_status_layout.setSpacing(4)

    def set_offline_UI(self):
        self.connection_status_img.setPixmap(self.offline_icon)
        self.connection_status_text.setText("Offline")
        self.connection_status_text.setStyleSheet("color: brown; font-weight: 800;")
        self.connection_status_layout.setSpacing(5)

    def set_server_down_UI(self):
        self.connection_status_img.setPixmap(self.offline_icon)
        self.connection_status_text.setText("Server Down")
        self.connection_status_text.setStyleSheet("color: brown; font-weight: 800;")
        self.connection_status_layout.setSpacing(5)
    
    def handle_scanner_status_click(self):
        if self.scanner_status_btn.text() == self.SCANNER_STATUS_TEXTS[0]:
            # check if scanner still connected (tell to disconnect or something)
            self.scanner_status_btn.setText(self.SCANNER_STATUS_TEXTS[1])
            self.switch_window(2)
            self.state_timer.stop()
        else:
            if self.__current_window == 2:
                self.scanner_status_btn.setText(self.SCANNER_STATUS_TEXTS[0])
                self.switch_window(3)
    
    def init_scan_logs(self):
        scans = self.cache_manager.get_data("scans")
        for scan_data in scans:
            self.append_scan_logs(*scan_data)
    
    def append_scan_logs(self, token_number: int, name: str, pref: str, scan_date: str, scan_time: str):
        if self.no_logs_label.isVisibleTo(self.logs_frame):
            self.no_logs_label.hide()
            self.logs_sub_layout.addStretch(stretch=1)
        datetime_obj = datetime.strptime(' '.join((scan_date, scan_time)), "%Y-%m-%d %H:%M:%S")

        log = QLabel(f"ID-{token_number} ({name}) {pref} at {datetime_obj.strftime("%d-%m-%Y %I-%M %p")}")
        log.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        log.setWordWrap(True)
        log.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.__last_log_color_idx = (self.__last_log_color_idx+1)%len(self.LOG_COLORS)
        log.setStyleSheet(f"background-color: {self.LOG_COLORS[self.__last_log_color_idx]};")
        self.logs_sub_layout.insertWidget(0, log)
    
    def show_token_status_success(self, data: tuple):
        self.scanner_status_btn.setText(self.SCANNER_STATUS_TEXTS[0])
        self.switch_window(0)
        self.__active_windows[0].setValue(*data)
        self.state_timer.timeout.connect(lambda: self.switch_window(3))
        self.state_timer.start(self.DISPLAY_TIMEOUT)

        token_number, name, _, pref = data
        current_datetime = UtilityFunctions.get_current_ist_datetime()
        scan_date = current_datetime.strftime("%Y-%m-%d")
        scan_time = current_datetime.strftime("%H:%M:%S")
        self.append_scan_logs(token_number, name, pref, scan_date, scan_time)
        self.cache_manager.add_scan(token_number, scan_date, scan_time)
    
    def show_token_status_failure(self, err: str):
        self.scanner_status_btn.setText(self.SCANNER_STATUS_TEXTS[0])
        self.switch_window(1)
        self.__active_windows[1].setValue(err)
        self.state_timer.timeout.connect(lambda: self.switch_window(3))
        self.state_timer.start(self.DISPLAY_TIMEOUT)
    
    def verify_typed_token_offline(self, token_number: int):
        return self.cache_manager.verify_typed_token(token_number)
    
    def verify_scanned_token_offline(self, token_id: str):
        return self.cache_manager.verify_scanned_token(token_id)
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CanteenWindow()
    window.show()
    sys.exit(app.exec())