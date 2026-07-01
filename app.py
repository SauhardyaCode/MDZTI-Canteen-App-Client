from __future__ import annotations
from typing import Optional
import sys
import re
from datetime import timedelta
from PyQt6.QtCore import Qt, QRegularExpression, QRect
from PyQt6.QtGui import QShowEvent, QRegularExpressionValidator, QIntValidator, QResizeEvent, QIcon
from PyQt6.QtWidgets import *
from styles import *
from core.utils import API_ENDPOINTS, POST, GET, UtilityFunctions, LoadingOverlay, OTPSenderThread, OTPInput, SlidingBackgroundFrame
from core.client_network import ClientNetworkThread
from core.password_hasher import PasswordHasher
from core.cache_manager import CacheManager
from views.admin import AdminWindow
from views.canteen import CanteenWindow

class RoleChoiceFrame(QFrame):
    def __init__(self, parent: LandingWindow):
        super().__init__()
        self.__parent = parent
        self.setStyleSheet("background-color: transparent;")
        self.__cache_manager = self.__parent.cache_manager

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
    
    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        self.__parent.home_btn.hide()
    
    def handle_admin_click(self):
        if self.__cache_manager.check_login("system admin"):
            self.__parent.render_authorized_window("system admin")
        else:
            self.__parent.switch_window(1)

    def handle_canteen_click(self):
        if self.__cache_manager.check_login("canteen supervisor"):
            self.__parent.render_authorized_window("canteen supervisor")
        else:
            self.__parent.switch_window(2)

class LoginFrame(QFrame):
    def __init__(self, parent: LandingWindow, role: str):
        super().__init__()
        self.__parent = parent
        self.role = role
        self.setStyleSheet("background-color: transparent;")
        self.loading_overlay_login = LoadingOverlay(self, "Logging in...")
        self.loading_overlay_otp = LoadingOverlay(self, "Sending OTP...")
        self.loading_overlay_verify = LoadingOverlay(self, "Verifying Email ID...")
        self.loading_overlay_pswd = LoadingOverlay(self, "Updating password...")

        self.__cache_manager = self.__parent.cache_manager
        role = role.split()[-1]

        self.otp_code = None
        self.expiry_time = None
        self.retries = 0
        self.email = None
        self.email_regex_string = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        login_card = QFrame()
        login_card.setFixedSize(650, 480)
        login_card.setStyleSheet(LOGIN_CARD_STYLESHEET)
        
        card_layout = QVBoxLayout(login_card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Heading Form Labels
        form_title = QLabel(f"{self.role.title()} Sign In")
        form_title.setObjectName("heading")


        self.register_frame = QFrame()
        self.register_frame.setStyleSheet(".QFrame { background-color: transparent; padding: 0px; margin: 0px; }")
        register_layout = QVBoxLayout(self.register_frame)

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

        login_btn = QPushButton("Log In")
        login_btn.setStyleSheet(LOGIN_BUTTON_STYLESHEET)
        login_btn.setFixedWidth(200)
        login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        login_btn.clicked.connect(self.handle_login)

        register_layout.addWidget(username_label)
        register_layout.addWidget(self.username_inp)
        register_layout.addWidget(password_label)
        register_layout.addWidget(self.password_inp)
        register_layout.addLayout(small_layout)
        register_layout.addStretch(stretch=1)
        register_layout.addWidget(login_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        register_layout.addStretch(stretch=1)




        self.email_frame = QFrame()
        self.email_frame.setStyleSheet(".QFrame { background-color: transparent; padding: 0px; margin: 0px; }")
        email_layout = QVBoxLayout(self.email_frame)

        email_label = QLabel("Email used for signup (to get OTP)")
        email_label.setStyleSheet("font-size: 13px; color: #666666")
        self.email_inp = QLineEdit()
        self.email_inp.setPlaceholderText(f"Enter {role} email")
        self.email_inp.returnPressed.connect(self.handle_send_otp)

        cancel_forgot_btn = QPushButton("Log in with password instead")
        cancel_forgot_btn.setStyleSheet(SMALL_BUTTON_STYLESHEET)
        cancel_forgot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_forgot_btn.clicked.connect(lambda: self.screen_stack.setCurrentIndex(0))

        send_otp_btn = QPushButton("Send OTP")
        send_otp_btn.setStyleSheet(LOGIN_BUTTON_STYLESHEET)
        send_otp_btn.setFixedWidth(200)
        send_otp_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_otp_btn.clicked.connect(self.handle_send_otp)
        
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_inp)
        email_layout.addWidget(cancel_forgot_btn, alignment=Qt.AlignmentFlag.AlignRight)
        email_layout.addStretch(stretch=1)
        email_layout.addWidget(send_otp_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        email_layout.addStretch(stretch=1)




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
            inp.returnPressed.connect(self.handle_verification)
            otp_inp_layout.addWidget(inp)

        self.resend_otp_btn = QPushButton("Resend OTP?")
        self.resend_otp_btn.setStyleSheet(SMALL_BUTTON_STYLESHEET)
        self.resend_otp_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.resend_otp_btn.clicked.connect(self.handle_verification)
        self.resend_otp_btn.setEnabled(False)

        verify_btn = QPushButton("Verify Email")
        verify_btn.setStyleSheet(LOGIN_BUTTON_STYLESHEET)
        verify_btn.setFixedWidth(200)
        verify_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # verify_btn.clicked.connect(self.handle_signup)

        otp_layout.addWidget(otp_label)
        otp_layout.addLayout(otp_inp_layout)
        otp_layout.addWidget(self.resend_otp_btn, alignment=Qt.AlignmentFlag.AlignRight)
        otp_layout.addStretch(stretch=1)
        otp_layout.addWidget(verify_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        otp_layout.addStretch(stretch=1)



        
        self.password_set_frame = QFrame()
        self.password_set_frame.setStyleSheet(".QFrame { background-color: transparent; padding: 0px; margin: 0px; }")
        password_set_layout = QVBoxLayout(self.password_set_frame)

        create_label = QLabel("Create New Password")
        create_label.setStyleSheet("font-size: 13px; color: #666666")
        self.create_password_inp = QLineEdit()
        self.create_password_inp.setPlaceholderText(f"Enter new {role} password")
        self.create_password_inp.setEchoMode(QLineEdit.EchoMode.Password)
        self.create_password_inp.returnPressed.connect(self.handle_change_password)

        confirm_label = QLabel("Confirm Password")
        confirm_label.setStyleSheet("font-size: 13px; color: #666666")
        self.cnf_password_inp = QLineEdit()
        self.cnf_password_inp.setPlaceholderText(f"Confirm new password")
        self.cnf_password_inp.setEchoMode(QLineEdit.EchoMode.Password)
        self.cnf_password_inp.returnPressed.connect(self.handle_change_password)

        small_layout = QHBoxLayout()

        cancel_forgot_btn = QPushButton("Log in with password instead")
        cancel_forgot_btn.setStyleSheet(SMALL_BUTTON_STYLESHEET)
        cancel_forgot_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_forgot_btn.clicked.connect(lambda: self.screen_stack.setCurrentIndex(0))

        small_layout.addStretch(stretch=1)
        small_layout.addWidget(cancel_forgot_btn)

        change_password_btn = QPushButton("Change Password")
        change_password_btn.setStyleSheet(LOGIN_BUTTON_STYLESHEET)
        change_password_btn.setFixedWidth(200)
        change_password_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_password_btn.clicked.connect(self.handle_change_password)

        password_set_layout.addWidget(create_label)
        password_set_layout.addWidget(self.create_password_inp)
        password_set_layout.addWidget(confirm_label)
        password_set_layout.addWidget(self.cnf_password_inp)
        password_set_layout.addLayout(small_layout)
        password_set_layout.addStretch(stretch=1)
        password_set_layout.addWidget(change_password_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        password_set_layout.addStretch(stretch=1)




        def get_input_focus(current: int):
            if current == 0:
                self.email_inp.setFocus()
            elif current == 1:
                self.otp_inp_1.setFocus()

        self.screen_stack = QStackedWidget(login_card)
        self.screen_stack.addWidget(self.register_frame)
        self.screen_stack.addWidget(self.email_frame)
        self.screen_stack.addWidget(self.otp_frame)
        self.screen_stack.addWidget(self.password_set_frame)
        self.screen_stack.currentChanged.connect(get_input_focus)
        self.screen_stack.setCurrentIndex(0)

        card_layout.addWidget(form_title, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.screen_stack)
        card_layout.addStretch(stretch=1)

        main_layout.addWidget(login_card, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def showEvent(self, event: QShowEvent):
        super().showEvent(event)
        self.username_inp.setFocus()
        self.__parent.home_btn.show()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.loading_overlay_login.setGeometry(self.rect())
        self.loading_overlay_otp.setGeometry(self.rect())
        self.loading_overlay_verify.setGeometry(self.rect())
        self.loading_overlay_pswd.setGeometry(self.rect())
    
    def clear_inputs(self):
        for inp in self.otp_inputs:
            inp.clear()
        self.username_inp.clear()
        self.password_inp.clear()
        self.email_inp.clear()
        self.create_password_inp.clear()
        self.cnf_password_inp.clear()
    
    def handle_login(self):
        email_or_username = self.username_inp.text()
        password = self.password_inp.text()
        email = None
        username = None

        if "@" in email_or_username:
            email = email_or_username
        else:
            username = email_or_username
        
        self.loading_overlay_login.show()
        worker = ClientNetworkThread(
            self, API_ENDPOINTS["verify-user-by-role"], GET,
            json_data = {
                "role": self.role, "email": email, "username": username, "password": password
            }
        )

        def on_success(action: str, data: dict):
            print(f"Success caught for action: {action}")
            self.loading_overlay_login.hide()
            self.__cache_manager.add_user(data.get("role"), data.get("email"))
            self.__parent.render_authorized_window(self.role)
        
        def on_failure(action: str, error_msg: str):
            self.loading_overlay_login.hide()
            UtilityFunctions.api_failure_coroutine(action, error_msg)
            QMessageBox.warning(None, "Cannot signin", error_msg)
        
        worker.bind_and_start(on_success, on_failure)

    def handle_no_account(self):
        if self.role == "system admin":
            self.__parent.switch_window(3)
        else:
            self.__parent.switch_window(4)
    
    def handle_forgot_password(self):
        self.screen_stack.setCurrentIndex(1)

    def send_new_otp(self):
        self.clear_inputs()
        self.resend_otp_btn.setEnabled(False)
        self.retries = 0

        self.loading_overlay_otp.show()
        self.loading_overlay_otp.setFocus()
        self.otp_worker = OTPSenderThread(self, self.email, self.role)

        def on_success(otp_code: str):
            self.loading_overlay_otp.hide()
            self.otp_code = otp_code
            self.expiry_time = UtilityFunctions.get_current_ist_datetime() + timedelta(seconds=(5*60))
            self.screen_stack.setCurrentIndex(2)

        def on_failure(err_msg: str):
            self.loading_overlay_otp.hide()
            QMessageBox.warning(None, "OTP Not Sent", err_msg)

        self.otp_worker.bind_and_start(on_success, on_failure)
    
    def handle_send_otp(self):
        self.email = self.email_inp.text()

        if not self.email:
            QMessageBox.warning(None, "Input Required", "Please provide the email ID signed up with!")
        elif re.match(self.email_regex_string, self.email) is None:
            QMessageBox.warning(None, "Invalid Input", "Not a valid email. Please verify your entry!")
        else:
            self.send_new_otp()
    
    def handle_verification(self):
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
                self.loading_overlay_verify.show()
                worker = ClientNetworkThread(
                    self, API_ENDPOINTS["verify-user-email-for-forget-password"], GET,
                    role=self.role, email=self.email
                )

                def on_success(action: str, data: dict):
                    print(f"Success caught for action: {action}")
                    self.loading_overlay_verify.hide()
                    self.screen_stack.setCurrentIndex(3)
                    self.clear_inputs()
                
                def on_failure(action: str, error_msg: str):
                    self.loading_overlay_verify.hide()
                    UtilityFunctions.api_failure_coroutine(action, error_msg)
                    QMessageBox.warning(None, "Cannot verify", error_msg)
                    self.screen_stack.setCurrentIndex(1)
                    self.clear_inputs()

                worker.bind_and_start(on_success, on_failure)
    
    def handle_change_password(self):
        new_password = self.create_password_inp.text()
        cnf_password = self.cnf_password_inp.text()

        if not all((new_password, cnf_password)):
            QMessageBox.warning(None, "Input Required", "Please fill out all the fields!")
        elif len(new_password) < 8:
            QMessageBox.warning(None, "Short Password", "Password must be atleast 8 characters long!")
        elif new_password != cnf_password:
            QMessageBox.warning(None, "Invalid Input", "Passwords do not match. Please try again!")
        else:
            self.loading_overlay_pswd.show()
            hasher = PasswordHasher()
            password_hash = hasher.create_hash(new_password)
            worker = ClientNetworkThread(
                self, API_ENDPOINTS["change-user-password-by-role"], POST,
                role=self.role, email=self.email, password_hash=password_hash
            )

            def on_success(action: str, data: dict):
                print(f"Success caught for action: {action}")
                self.loading_overlay_pswd.hide()
                QMessageBox.information(None, "Password Updated", f"{self.role.title()} Password updated successfully!")
                self.screen_stack.setCurrentIndex(0)
                self.clear_inputs()

            def on_failure(action: str, error_msg: str):
                self.loading_overlay_pswd.hide()
                UtilityFunctions.api_failure_coroutine(action, error_msg)
                QMessageBox.warning(None, "Cannot update password", error_msg)

            worker.bind_and_start(on_success, on_failure)


class SignupFrame(QFrame):
    def __init__(self, parent: LandingWindow, role: str):
        super().__init__()
        self.__parent = parent
        self.role = role
        self.setStyleSheet("background-color: transparent;")
        self.loading_overlay_otp = LoadingOverlay(self, "Sending OTP...")
        self.loading_overlay_signup = LoadingOverlay(self, "Signing up...")

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

        self.get_otp_btn = QPushButton("Get OTP")
        self.get_otp_btn.setStyleSheet(LOGIN_BUTTON_STYLESHEET)
        self.get_otp_btn.setFixedWidth(200)
        self.get_otp_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.get_otp_btn.clicked.connect(self.handle_get_otp)

        info_layout.addWidget(email_label)
        info_layout.addWidget(self.email_inp)
        info_layout.addLayout(username_layout)
        info_layout.addLayout(password_layout)
        info_layout.addWidget(already_created_btn, alignment=Qt.AlignmentFlag.AlignRight)
        info_layout.addStretch(stretch=1)
        info_layout.addWidget(self.get_otp_btn, alignment=Qt.AlignmentFlag.AlignCenter)
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
            inp.returnPressed.connect(self.handle_signup)
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
        self.__parent.home_btn.show()
    
    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        self.loading_overlay_otp.setGeometry(self.rect())
        self.loading_overlay_signup.setGeometry(self.rect())
    
    def clear_inputs(self):
        for inp in self.otp_inputs:
            inp.clear()
        self.email_inp.clear()
        self.username_inp.clear()
        self.cnf_username_inp.clear()
        self.password_inp.clear()
        self.cnf_password_inp.clear()
    
    def send_new_otp(self):
        self.clear_inputs()
        self.resend_otp_btn.setEnabled(False)
        self.retries = 0

        self.loading_overlay_otp.show()
        self.loading_overlay_otp.setFocus()
        self.otp_worker = OTPSenderThread(self, self.email, self.role)

        def on_success(otp_code: str):
            self.loading_overlay_otp.hide()
            self.otp_code = otp_code
            self.expiry_time = UtilityFunctions.get_current_ist_datetime() + timedelta(seconds=(5*60))
            self.screen_stack.setCurrentIndex(1)

        def on_failure(err_msg: str):
            self.loading_overlay_otp.hide()
            QMessageBox.warning(None, "OTP Not Sent", err_msg)

        self.otp_worker.bind_and_start(on_success, on_failure)
    
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
            self.send_new_otp()
    
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
                self.loading_overlay_signup.show()
                hasher = PasswordHasher()
                password_hash = hasher.create_hash(self.password)
                worker = ClientNetworkThread(
                    self, API_ENDPOINTS["add-new-user-role"], POST,
                    role=self.role, email=self.email, username=self.username, password_hash=password_hash
                )

                def on_success(action: str, data: dict):
                    print(f"Success caught for action: {action}")
                    self.loading_overlay_signup.hide()
                    QMessageBox.information(
                        None, "Signup Success",
                        f"Hooray! Your email has been verified. You are the {data.get("role")} now!"
                    )
                    self.screen_stack.setCurrentIndex(0)
                    self.clear_inputs()
                    self.__parent.switch_window(1)
                
                def on_failure(action: str, error_msg: str):
                    self.loading_overlay_signup.hide()
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
    def __init__(self, geometry: Optional[QRect] = None):
        super().__init__()
        self.__WINDOWS = (RoleChoiceFrame, AdminLoginFrame, CanteenLoginFrame, AdminSignupFrame, CanteenSignupFrame)
        self.__current_window = None
        self.__active_windows = [None for _ in range(len(self.__WINDOWS))]
        self.admin_window = AdminWindow
        self.supervisor_window = CanteenWindow
        self.cache_manager = CacheManager()

        screen = QApplication.primaryScreen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()
        self.setMinimumSize(screen_width-300, screen_height-200)
        self.setWindowTitle("Canteen Manager App (User Login)")
        self.setWindowIcon(QIcon(UtilityFunctions.resource_path("assets/desktop-icon.png")))
        if geometry:
            self.setGeometry(geometry)
        
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

        home_stretch_layout = QHBoxLayout()
        self.home_btn = QPushButton("Return To Roles")
        self.home_btn.setStyleSheet(HOME_RETURN_BUTTON_STYLESHEET)
        self.home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.home_btn.clicked.connect(lambda: self.switch_window(0))
        home_stretch_layout.addWidget(self.home_btn)
        home_stretch_layout.addStretch(stretch=1)

        self.container_layout = QVBoxLayout()

        stretch_layout = QHBoxLayout()
        footer = QLabel("© Canteen Management App | Developed by Sauhardya Haldar")
        footer.setStyleSheet("font-size: 10px; color: #ffffff; font-style: italic;")
        stretch_layout.addStretch(stretch=1)
        stretch_layout.addWidget(footer, alignment=Qt.AlignmentFlag.AlignLeft)

        main_layout.addLayout(home_stretch_layout)
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
    
    def render_authorized_window(self, role):
        isMaximized = self.isMaximized()
        geometry = self.geometry()
        self.destroy()
        if role == "system admin":
            self.authorized_window = self.admin_window(geometry)
        else:
            self.authorized_window = self.supervisor_window(geometry)

        if isMaximized:
            self.authorized_window.showMaximized()
        else:
            self.authorized_window.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LandingWindow()
    window.showMaximized()
    sys.exit(app.exec())