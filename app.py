from __future__ import annotations
import sys
import re
from datetime import timedelta
from PyQt6.QtCore import QPropertyAnimation, QPoint, QEasingCurve, QTimer, Qt, QRegularExpression, pyqtSignal
from PyQt6.QtGui import QShowEvent, QRegularExpressionValidator, QIntValidator, QKeyEvent, QResizeEvent
from PyQt6.QtWidgets import *
from styles import *
from core.utils import API_ENDPOINTS, POST, GET, UtilityFunctions, LoadingOverlay
from core.client_network import ClientNetworkThread
from core.password_hasher import PasswordHasher
from views.admin import AdminWindow
from views.canteen import CanteenWindow

class SlidingBackgroundFrame(QFrame):
    def __init__(self, img1_path, img2_path, change_interval=5000, parent=None):
        super().__init__(parent)
        
        # Save file paths to cycle through them
        self.images = [img1_path, img2_path]
        self.current_idx = 0
        
        # Giant canvas to hold current and incoming images side-by-side
        self.canvas = QWidget(self)
        
        # Create two placeholder frames inside the canvas
        self.bg_left = QFrame(self.canvas)
        self.bg_right = QFrame(self.canvas)
        
        self.update_image_styles()

        # Timer to trigger the slide
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.slide_left)
        self.timer.start(change_interval)

    def update_image_styles(self):
        """Applies the background images based on the current index tracker."""
        img1 = self.images[self.current_idx]
        img2 = self.images[(self.current_idx + 1) % len(self.images)]
        
        self.bg_left.setStyleSheet(f"border-image: url('{img1}') 0 0 0 0 stretch stretch;")
        self.bg_right.setStyleSheet(f"border-image: url('{img2}') 0 0 0 0 stretch stretch;")

    def resizeEvent(self, event):
        """Dynamically ensures elements match window size on resize."""
        w = self.width()
        h = self.height()
        
        self.canvas.resize(w * 2, h)
        self.bg_left.setGeometry(0, 0, w, h)
        self.bg_right.setGeometry(w, 0, w, h)
        self.canvas.move(0, 0)
        
        super().resizeEvent(event)

    def slide_left(self):
        w = self.width()
        
        # Configure the slide animation moving left (-w)
        self.anim = QPropertyAnimation(self.canvas, b"pos")
        self.anim.setDuration(1200) # 1.2 seconds slide transition
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.anim.setStartValue(QPoint(0, 0))
        self.anim.setEndValue(QPoint(-w, 0))
        
        # Crucial: When the slide ends, snap positions back seamlessly
        self.anim.finished.connect(self.on_animation_finished)
        self.anim.start()

    def on_animation_finished(self):
        # 1. Disconnect the signal to prevent compounding triggers
        self.anim.finished.disconnect()
        
        # 2. Increment image tracker pointer index
        self.current_idx = (self.current_idx + 1) % len(self.images)
        
        # 3. Update the sheets so the new background is now set to bg_left
        self.update_image_styles()
        
        # 4. Instant stealth teleportation back to the origin coordinates
        self.canvas.move(0, 0)

class OTPInput(QLineEdit):
    backspace_pressed = pyqtSignal()

    def keyPressEvent(self, event: QKeyEvent):
        valid_keys = [ Qt.Key.Key_0, Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3, Qt.Key.Key_4, Qt.Key.Key_5, Qt.Key.Key_6, Qt.Key.Key_7, Qt.Key.Key_8, Qt.Key.Key_9]
        if event.key() == Qt.Key.Key_Backspace:
            self.backspace_pressed.emit()
        elif event.key() in valid_keys:
            self.clear()
        super().keyPressEvent(event)

class RoleChoiceFrame(QFrame):
    def __init__(self, parent: LandingWindow):
        super().__init__()
        self.__parent = parent
        self.setStyleSheet("background-color: transparent;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(80)

        label = QLabel("Choose Your Role")
        label.setStyleSheet(ROLE_TITLE_STYLESHEET)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(0)

        admin_btn = QPushButton("System Admin")
        admin_btn.setStyleSheet(ROLE_BUTTON_STYLESHEET)
        admin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        admin_btn.setFixedWidth(400)
        admin_btn.clicked.connect(self.handle_admin_click)

        canteen_btn = QPushButton("Canteen Supervisor")
        canteen_btn.setStyleSheet(ROLE_BUTTON_STYLESHEET)
        canteen_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        canteen_btn.setFixedWidth(400)
        canteen_btn.clicked.connect(self.handle_canteen_click)

        btn_layout.addWidget(admin_btn)
        btn_layout.addWidget(canteen_btn)

        main_layout.addStretch(stretch=1)
        main_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        main_layout.addLayout(btn_layout)
        main_layout.addStretch(stretch=1)
    
    def handle_admin_click(self):
        self.__parent.switch_window(1)

    def handle_canteen_click(self):
        self.__parent.switch_window(2)

class LoginFrame(QFrame):
    def __init__(self, parent: LandingWindow, role: str):
        super().__init__()
        self.__parent = parent
        self.role = role
        self.setStyleSheet("background-color: transparent;")
        self.loading_overlay = LoadingOverlay(self, "Logging in...")
        role = role.split()[-1]

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        login_card = QFrame()
        login_card.setFixedSize(650, 450)
        login_card.setStyleSheet(LOGIN_CARD_STYLESHEET)
        
        card_layout = QVBoxLayout(login_card)
        card_layout.setSpacing(0)

        # Heading Form Labels
        form_title = QLabel(f"{self.role.title()} Sign In")
        form_title.setObjectName("heading")

        username_label = QLabel("Username / Email")
        username_label.setStyleSheet("font-size: 13px; color: #666666")
        self.username_inp = QLineEdit()
        self.username_inp.setPlaceholderText(f"Enter {role} username or email")
        self.username_inp.returnPressed.connect(self.handle_login)

        password_label = QLabel("Password")
        password_label.setStyleSheet("font-size: 13px; color: #666666")
        self.password_inp = QLineEdit()
        self.password_inp.setPlaceholderText(f"Enter {role} password")
        self.password_inp.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_inp.returnPressed.connect(self.handle_login)

        small_layout = QHBoxLayout()

        no_account_btn = QPushButton("Don't have an account?")
        no_account_btn.setStyleSheet(SMALL_BUTTON_STYLESHEET)
        no_account_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        no_account_btn.clicked.connect(self.handle_no_account)

        forgot_pswd_btn = QPushButton("Forgot Password?")
        forgot_pswd_btn.setStyleSheet(SMALL_BUTTON_STYLESHEET)
        forgot_pswd_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        forgot_pswd_btn.clicked.connect(self.handle_forgot_password)

        small_layout.addWidget(no_account_btn)
        small_layout.addStretch(stretch=1)
        small_layout.addWidget(forgot_pswd_btn)

        login_button = QPushButton("Log In")
        login_button.setStyleSheet(LOGIN_BUTTON_STYLESHEET)
        login_button.setFixedWidth(200)
        login_button.setCursor(Qt.CursorShape.PointingHandCursor)
        login_button.clicked.connect(self.handle_login)

        card_layout.addWidget(form_title, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)

        card_layout.addWidget(username_label)
        card_layout.addWidget(self.username_inp)
        card_layout.addWidget(password_label)
        card_layout.addWidget(self.password_inp)
        card_layout.addLayout(small_layout)
        card_layout.addStretch(stretch=1)
        card_layout.addWidget(login_button, alignment=Qt.AlignmentFlag.AlignCenter)
        card_layout.addStretch(stretch=1)

        main_layout.addWidget(login_card, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        self.username_inp.setFocus()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.loading_overlay.setGeometry(self.rect())
    
    def handle_login(self):
        email_or_username = self.username_inp.text()
        password = self.password_inp.text()
        email = None
        username = None

        if "@" in email_or_username:
            email = email_or_username
        else:
            username = email_or_username
        
        self.loading_overlay.show()
        worker = ClientNetworkThread(
            self, API_ENDPOINTS["verify-user-by-role"], GET,
            json_data = {
                "role": self.role, "email": email, "username": username, "password": password
            }
        )

        def on_success(action: str, data: dict):
            print(f"Success caught for action: {action}")
            self.loading_overlay.hide()
            isMaximized = self.__parent.isMaximized()
            geometry = self.__parent.geometry()
            self.__parent.destroy()
            if self.role == "system admin":
                authorized_window = self.__parent.admin_window(geometry)
            else:
                authorized_window = self.__parent.supervisor_window(geometry)

            if isMaximized:
                authorized_window.showMaximized()
            else:
                authorized_window.show()
        
        def on_failure(action: str, error_msg: str):
            self.loading_overlay.hide()
            UtilityFunctions.api_failure_coroutine(action, error_msg)
            QMessageBox.warning(None, "Cannot signin", error_msg)
        
        worker.bind_and_start(on_success, on_failure)

    def handle_no_account(self):
        if self.role == "system admin":
            self.__parent.switch_window(3)
        else:
            self.__parent.switch_window(4)
    
    def handle_forgot_password(self):
        pass

class SignupFrame(QFrame):
    def __init__(self, parent: LandingWindow, role: str):
        super().__init__()
        self.__parent = parent
        self.role = role
        self.setStyleSheet("background-color: transparent;")
        self.loading_overlay = LoadingOverlay(self, "Signing up...")

        self.email = None
        self.username = None
        self.password = None
        self.otp_code = None
        self.expiry_time = None
        self.retries = 0
        self.email_regex_string = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        email_regex = QRegularExpression(self.email_regex_string)
        username_regex = QRegularExpression(r"^[a-zA-Z0-9_]+$")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.signup_card = QFrame()
        self.signup_card.setFixedSize(600, 550)
        self.signup_card.setStyleSheet(SIGNUP_CARD_STYLESHEET)
        
        card_layout = QVBoxLayout(self.signup_card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Heading Form Labels
        form_title = QLabel(f"{self.role.title()} Sign Up")
        form_title.setObjectName("heading")

        self.info_frame = QFrame()
        self.info_frame.setStyleSheet(".QFrame { background-color: transparent; padding: 0px; margin: 0px; }")
        info_layout = QVBoxLayout(self.info_frame)

        email_label = QLabel("Email")
        email_label.setStyleSheet("font-size: 13px; color: #666666")
        self.email_inp = QLineEdit()
        self.email_inp.setPlaceholderText(f"Enter Email Address (for OTP)")
        self.email_inp.setValidator(QRegularExpressionValidator(email_regex))
        self.email_inp.returnPressed.connect(self.handle_get_otp)

        username_layout = QGridLayout()
        username_layout.setHorizontalSpacing(50)

        username_label = QLabel("Username")
        username_label.setStyleSheet("font-size: 13px; color: #666666")
        self.username_inp = QLineEdit()
        self.username_inp.setPlaceholderText(f"Create Username")
        self.username_inp.setValidator(QRegularExpressionValidator(username_regex))
        self.username_inp.returnPressed.connect(self.handle_get_otp)

        cnf_username_label = QLabel("Confirm Username")
        cnf_username_label.setStyleSheet("font-size: 13px; color: #666666")
        self.cnf_username_inp = QLineEdit()
        self.cnf_username_inp.setPlaceholderText(f"Confirm Username")
        self.cnf_username_inp.setValidator(QRegularExpressionValidator(username_regex))
        self.cnf_username_inp.returnPressed.connect(self.handle_get_otp)
        
        username_layout.addWidget(username_label, 0, 0)
        username_layout.addWidget(cnf_username_label, 0, 1)
        username_layout.addWidget(self.username_inp, 1, 0)
        username_layout.addWidget(self.cnf_username_inp, 1, 1)

        password_layout = QGridLayout()
        password_layout.setHorizontalSpacing(50)

        password_label = QLabel("Password")
        password_label.setStyleSheet("font-size: 13px; color: #666666")
        self.password_inp = QLineEdit()
        self.password_inp.setPlaceholderText(f"Create Password")
        self.password_inp.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_inp.returnPressed.connect(self.handle_get_otp)

        cnf_password_label = QLabel("Confirm Password")
        cnf_password_label.setStyleSheet("font-size: 13px; color: #666666")
        self.cnf_password_inp = QLineEdit()
        self.cnf_password_inp.setPlaceholderText(f"Confirm Password")
        self.cnf_password_inp.setEchoMode(QLineEdit.EchoMode.Password)
        self.cnf_password_inp.returnPressed.connect(self.handle_get_otp)

        password_layout.addWidget(password_label, 0, 0)
        password_layout.addWidget(cnf_password_label, 0, 1)
        password_layout.addWidget(self.password_inp, 1, 0)
        password_layout.addWidget(self.cnf_password_inp, 1, 1)

        already_created_btn = QPushButton("Already signed up?")
        already_created_btn.setStyleSheet(SMALL_BUTTON_STYLESHEET)
        already_created_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        already_created_btn.clicked.connect(self.handle_already_created)

        get_otp_btn = QPushButton("Get OTP")
        get_otp_btn.setStyleSheet(LOGIN_BUTTON_STYLESHEET)
        get_otp_btn.setFixedWidth(200)
        get_otp_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        get_otp_btn.clicked.connect(self.handle_get_otp)

        info_layout.addWidget(email_label)
        info_layout.addWidget(self.email_inp)
        info_layout.addLayout(username_layout)
        info_layout.addLayout(password_layout)
        info_layout.addWidget(already_created_btn, alignment=Qt.AlignmentFlag.AlignRight)
        info_layout.addStretch(stretch=1)
        info_layout.addWidget(get_otp_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        info_layout.addStretch(stretch=1)

        self.otp_frame = QFrame()
        self.otp_frame.setStyleSheet(".QFrame { background-color: transparent; padding: 0px; margin: 0px; }")
        otp_layout = QVBoxLayout(self.otp_frame)

        otp_label = QLabel(f"OTP (Sent to {role} email address)")
        otp_label.setStyleSheet("font-size: 13px; color: #666666")

        otp_inp_layout = QHBoxLayout()
        otp_inp_layout.setSpacing(40)

        self.otp_inp_1 = OTPInput()
        self.otp_inp_2 = OTPInput()
        self.otp_inp_3 = OTPInput()
        self.otp_inp_4 = OTPInput()
        self.otp_inp_5 = OTPInput()
        self.otp_inp_6 = OTPInput()
        self.otp_inputs = [self.otp_inp_1, self.otp_inp_2, self.otp_inp_3, self.otp_inp_4, self.otp_inp_5, self.otp_inp_6]

        def input_next(text: str, current: int):
            if self.otp_inputs[current].hasAcceptableInput() and len(text) == 1:
                if current+1 < len(self.otp_inputs):
                    self.otp_inputs[current+1].setFocus()
                else:
                    self.otp_inputs[current].clearFocus()
        
        def clear_prev(current: int):
            if current-1 >= 0:
                self.otp_inputs[current-1].setFocus()

        for i, inp in enumerate(self.otp_inputs):
            inp.setStyleSheet("font-size: 30px;")
            inp.setValidator(QIntValidator(0, 9))
            inp.setFixedWidth(60)
            inp.setAlignment(Qt.AlignmentFlag.AlignCenter)
            inp.textChanged.connect(lambda text, idx=i: input_next(text, idx))
            inp.backspace_pressed.connect(lambda idx=i: clear_prev(idx))
            otp_inp_layout.addWidget(inp)

        self.resend_otp_btn = QPushButton("Resend OTP?")
        self.resend_otp_btn.setStyleSheet(SMALL_BUTTON_STYLESHEET)
        self.resend_otp_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resend_otp_btn.clicked.connect(self.send_new_otp)
        self.resend_otp_btn.setEnabled(False)

        signup_btn = QPushButton("Sign Up")
        signup_btn.setStyleSheet(LOGIN_BUTTON_STYLESHEET)
        signup_btn.setFixedWidth(200)
        signup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        signup_btn.clicked.connect(self.handle_signup)

        otp_layout.addWidget(otp_label)
        otp_layout.addLayout(otp_inp_layout)
        otp_layout.addWidget(self.resend_otp_btn, alignment=Qt.AlignmentFlag.AlignRight)
        otp_layout.addStretch(stretch=1)
        otp_layout.addWidget(signup_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        otp_layout.addStretch(stretch=1)

        def get_input_focus(current: int):
            if current == 0:
                self.email_inp.setFocus()
            elif current == 1:
                self.otp_inp_1.setFocus()

        self.screen_stack = QStackedWidget(self.signup_card)
        self.screen_stack.addWidget(self.info_frame)
        self.screen_stack.addWidget(self.otp_frame)
        self.screen_stack.currentChanged.connect(get_input_focus)
        self.screen_stack.setCurrentIndex(0)

        card_layout.addWidget(form_title, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.screen_stack)
        card_layout.addStretch(stretch=1)

        main_layout.addWidget(self.signup_card, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        self.email_inp.setFocus()
    
    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.loading_overlay.setGeometry(self.rect())
    
    def clear_inputs(self):
        for inp in self.otp_inputs:
            inp.clear()
        self.email_inp.clear()
        self.username_inp.clear()
        self.cnf_username_inp.clear()
        self.password_inp.clear()
        self.cnf_password_inp.clear()
    
    def send_new_otp(self) -> bool:
        self.clear_inputs()
        self.resend_otp_btn.setEnabled(False)
        self.retries = 0
        self.otp_code = UtilityFunctions.send_otp_email(self.email, self.role)
        if self.otp_code is None:
            QMessageBox.warning(None, "OTP Not Sent", "OTP couldn't be sent. Please verify your email or try again later!")
            return False
        self.expiry_time = UtilityFunctions.get_current_ist_datetime() + timedelta(seconds=(5*60))
        return True
    
    def handle_get_otp(self):
        self.email = self.email_inp.text().strip()
        self.username = self.username_inp.text().strip()
        cnf_username = self.cnf_username_inp.text().strip()
        self.password = self.password_inp.text()
        cnf_password = self.cnf_password_inp.text()

        if not all((self.email, self.username, cnf_username, self.password, cnf_password)):
            QMessageBox.warning(None, "Input Required", "Please fill out all the fields!")
        elif re.match(self.email_regex_string, self.email) is None:
            QMessageBox.warning(None, "Invalid Input", "Not a valid email. Please verify your entry!")
        elif len(self.password) < 8:
            QMessageBox.warning(None, "Short Password", "Password must be atleast 8 characters long!")
        elif self.username != cnf_username:
            QMessageBox.warning(None, "Invalid Input", "Usernames do not match. Please verify your entry!")
        elif self.password != cnf_password:
            QMessageBox.warning(None, "Invalid Input", "Passwords do not match. Please try again!")
        else:
            if self.send_new_otp():
                self.screen_stack.setCurrentIndex(1)
    
    def handle_signup(self):
        otp_code = ""
        for inp in self.otp_inputs:
            if not inp.text():
                QMessageBox.warning(None, "Input Required", "Please fill out the 6 digit OTP!")
                return
            otp_code += inp.text()
        
        if self.otp_code and self.expiry_time:
            if self.expiry_time < UtilityFunctions.get_current_ist_datetime():
                QMessageBox.warning(None, "OTP Expired", "The last sent OTP has expired. Please issue new one!")
                self.resend_otp_btn.setEnabled(True)
            elif self.retries >= 3:
                QMessageBox.warning(None, "Retry Limit Exceeded", "Three consecutive retries. Please issue new OTP!")
                self.resend_otp_btn.setEnabled(True)
            elif otp_code != self.otp_code:
                QMessageBox.warning(None, "Invalid OTP", "The OTP provided is wrong. Please verify!")
                self.retries += 1
            else:
                self.loading_overlay.show()
                hasher = PasswordHasher()
                password_hash = hasher.create_hash(self.password)
                worker = ClientNetworkThread(
                    self, API_ENDPOINTS["add-new-user-role"], POST,
                    role=self.role, email=self.email, username=self.username, password_hash=password_hash
                )

                def on_success(action: str, data: dict):
                    print(f"Success caught for action: {action}")
                    self.loading_overlay.hide()
                    QMessageBox.information(
                        None, "Signup Success",
                        f"Hooray! Your email has been verified. You are the {data.get("role")} now!"
                    )
                    self.screen_stack.setCurrentIndex(0)
                    self.clear_inputs()
                    self.__parent.switch_window(1)
                
                def on_failure(action: str, error_msg: str):
                    self.loading_overlay.hide()
                    UtilityFunctions.api_failure_coroutine(action, error_msg)
                    QMessageBox.warning(None, "Cannot signup", error_msg)

                worker.bind_and_start(on_success, on_failure)
                

    def handle_already_created(self):
        if self.role == "system admin":
            self.__parent.switch_window(1)
        else:
            self.__parent.switch_window(2)

class AdminLoginFrame(LoginFrame):
    def __init__(self, parent: LandingWindow):
        super().__init__(parent, "system admin")

class CanteenLoginFrame(LoginFrame):
    def __init__(self, parent: LandingWindow):
        super().__init__(parent, "canteen supervisor")

class AdminSignupFrame(SignupFrame):
    def __init__(self, parent: LandingWindow):
        super().__init__(parent, "system admin")

class CanteenSignupFrame(SignupFrame):
    def __init__(self, parent: LandingWindow):
        super().__init__(parent, "canteen supervisor")

class LandingWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.__WINDOWS = (RoleChoiceFrame, AdminLoginFrame, CanteenLoginFrame, AdminSignupFrame, CanteenSignupFrame)
        self.__current_window = None
        self.__active_windows = [None for _ in range(len(self.__WINDOWS))]
        self.admin_window = AdminWindow
        self.supervisor_window = CanteenWindow

        screen = QApplication.primaryScreen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()
        self.setMinimumSize(screen_width-300, screen_height-200)
        self.setWindowTitle("Canteen Manager App (User Login)")
        
        main_central_widget = QWidget(self)
        main_central_widget.setStyleSheet(ROOT_STYLESHEET)
        self.setCentralWidget(main_central_widget)

        # ... inside your Window UI setup code ...
        main_central_widget = QWidget(self)
        main_central_widget.setStyleSheet(ROOT_STYLESHEET)
        self.setCentralWidget(main_central_widget)

        outer_layout = QVBoxLayout(main_central_widget)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # --- Top Panel ---
        top_panel_frame = QFrame()
        top_panel_frame.setStyleSheet(PANEL_BORDER_STYLESHEET + TITLE_STYLESHEET)
        top_panel_layout = QVBoxLayout(top_panel_frame)
        label = QLabel("MDZTI/APDJ Canteen Management App")
        top_panel_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)

        # --- NEW: Use the Sliding Background Frame ---
        # Switches between your background assets every 6 seconds (6000ms)
        main_frame = SlidingBackgroundFrame('assets/background-1.jpeg', 'assets/background-2.jpeg', 6000)
        main_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Main frame layout (0 margins so overlay stretches fully over the slider)
        main_frame_layout = QVBoxLayout(main_frame)
        main_frame_layout.setContentsMargins(0, 0, 0, 0)
        main_frame_layout.setSpacing(0)

        # --- The Overlay Frame ---
        self.overlay_frame = QFrame()
        self.overlay_frame.setObjectName("DarkOverlay")
        self.overlay_frame.setStyleSheet(LOGIN_SCREEN_OVERLAY_STYLESHEET)
        self.overlay_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        main_frame_layout.addWidget(self.overlay_frame)

        # --- Contents inside Overlay (Login Interface) ---
        main_layout = QVBoxLayout(self.overlay_frame)
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.container_layout = QVBoxLayout()

        stretch_layout = QHBoxLayout()
        footer = QLabel("© Canteen Management App | Developed by Sauhardya Haldar")
        footer.setStyleSheet("font-size: 10px; color: #ffffff; font-style: italic;")
        stretch_layout.addStretch(stretch=1)
        stretch_layout.addWidget(footer, alignment=Qt.AlignmentFlag.AlignLeft)

        main_layout.addStretch(stretch=1)
        main_layout.addLayout(self.container_layout)
        main_layout.addStretch(stretch=1)
        main_layout.addLayout(stretch_layout)

        # Put pieces together
        outer_layout.addWidget(top_panel_frame, 1)
        outer_layout.addWidget(main_frame, 9)

        self.switch_window(0)
    
    def switch_window(self, window_sl_no: int):
        if (self.__current_window != window_sl_no):
            self.__current_window = window_sl_no

            if (self.__active_windows[window_sl_no] == None):
                newCreatedWindow = self.__WINDOWS[window_sl_no](self) # Create the class object
                self.container_layout.addWidget(newCreatedWindow)
                self.__active_windows[window_sl_no] = newCreatedWindow
            else:
                self.container_layout.addWidget(self.__active_windows[window_sl_no])
            
            for i in range(len(self.__WINDOWS)):
                if self.__active_windows[i]:
                    self.__active_windows[i].hide()
            self.__active_windows[window_sl_no].show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LandingWindow()
    window.show()
    sys.exit(app.exec())