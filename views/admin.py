from __future__ import annotations
from typing import Union, Dict, Any
from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QIntValidator, QShowEvent

import sys
from core.client_network import ClientNetworkThread
from core.utils import *
from styles import *
import json

__all__ = ["AdminWindow"]

_utilities = UtilityFunctions()

_token_stats = {}
_token_available = []
_active_trainees = []
_settings = []
_dirty_bits = {"token_stats": False, "token_available": False, "active_trainees": False, "settings": False}

class _GenerationFrame(QWidget):
    def __init__(self, parent: AdminWindow) -> None:
        super().__init__()
        self.__parent = parent
        self.gen_worker = None
        self.fetch_worker = None
        self.loading_overlay = LoadingOverlay(self, "Generating the tokens...")

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.__parent._window_frame.setStyleSheet(GENERATE_PANEL_STYLESHEET)

        title = QLabel("Generate New QR Coded Tokens")
        title.setObjectName("heading")
        input_frame = QFrame()
        input_frame.setStyleSheet(GENERATE_PANEL_SUBFRAME_STYLESHEET)
        input_layout = QVBoxLayout(input_frame)

        input_sub_frame = QFrame()
        input_sub_frame.setStyleSheet(GENERATE_PANEL_INPUT_STYLESHEET)
        input_sub_layout = QHBoxLayout(input_sub_frame)
        input_label = QLabel("Enter no. of tokens to generate: ")
        self.input_field = QLineEdit()
        self.input_field.setValidator(QIntValidator(1, 100000))
        self.input_field.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.input_field.setMaximumWidth(150)

        input_sub_layout.addStretch()
        input_sub_layout.addWidget(input_label, 0)
        input_sub_layout.addWidget(self.input_field, 0)
        input_sub_layout.addStretch()

        self.generate_btn = QPushButton("Generate")
        self.generate_btn.clicked.connect(self.generate_new_token)
        self.generate_btn.setFixedWidth(200)
        self.generate_btn.setStyleSheet(SUBMIT_BUTTON_STYLESHEET)

        input_layout.addWidget(input_sub_frame)
        input_layout.addWidget(self.generate_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        input_layout.addStretch()

        info_frame = QFrame()
        info_frame.setStyleSheet(INFO_FRAME_STYLESHEET)
        info_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        info_layout = QVBoxLayout(info_frame)
        sub_title = QLabel("<b>---------------------- Existing Token Info ----------------------</b>")
        sub_title.setObjectName("heading")
        self.info_sub_layout = QGridLayout()
        self.info_loader = QLabel("Loading...")
        self.fetch_token_info()

        self.info_sub_layout.addWidget(self.info_loader, 0, 0)
        info_layout.addWidget(sub_title)
        info_layout.addLayout(self.info_sub_layout)

        self.main_layout.addWidget(title, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(input_frame, stretch=4, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addStretch(stretch=1)
        self.main_layout.addWidget(info_frame, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.loading_overlay.setGeometry(self.rect())
    
    def showEvent(self, event: QShowEvent):
        self.fetch_token_info()
        super().showEvent(event)
    
    def generate_new_token(self) -> None:
        if (not self.input_field.text()):
            QMessageBox.warning(None, "Warning", "Please enter the number of tokens to be generated")
            return
        self.generate_btn.setDisabled(True)
        self.loading_overlay.show()
        self.gen_worker = ClientNetworkThread(self, API_ENDPOINTS["generate-new-physical-qr-token"], POST, total_tokens=int(self.input_field.text()))
        self.gen_worker.bind_and_start(self.on_api_success, _utilities.api_failure_coroutine)
    
    def fetch_token_info(self) -> None:
        self.fetch_worker = ClientNetworkThread(self, API_ENDPOINTS["fetch-physical-token-stats"], GET)
        self.fetch_worker.bind_and_start(self.on_api_success, _utilities.api_failure_coroutine)

    def destroy_layout_children(self, layout: Union[QHBoxLayout, QVBoxLayout, QGridLayout]):
        while layout.count()>0:
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                continue
            child_layout = item.layout()
            self.destroy_layout_children(child_layout)
            child_layout.deleteLater()
    
    def on_api_success(self, action: str, data: Dict[str, Any]):
        print(f"Success caught for action: {action}")

        if action == API_ENDPOINTS["generate-new-physical-qr-token"]:
            self.loading_overlay.hide()
            self.fetch_token_info()
            total_inserted = data.get("inserted_count")
            tokens = data.get("tokens")

            with open("logs.txt", "w") as f:
                json.dump(tokens, f, indent=4)
            
            self.generate_btn.setDisabled(False)
            QMessageBox.information(None, "Success", f"Successfully generated {total_inserted} new tokens!")
        
        elif action == API_ENDPOINTS["fetch-physical-token-stats"]:
            total = data.get("total")
            available = data.get("available")
            assigned = data.get("assigned")
            max_token = data.get("max_number")

            info_total = QLabel(f"Total Tokens: <b>{total}</b>")
            info_largest = QLabel(f"Largest Token Number: <b>{max_token if max_token>0 else None}</b>")
            info_available = QLabel(f"Available Tokens: <b>{available}</b>")
            info_assigned = QLabel(f"Assigned Tokens: <b>{assigned}</b>")

            self.destroy_layout_children(self.info_sub_layout)
            self.info_sub_layout.addWidget(info_total, 0, 0)
            self.info_sub_layout.addWidget(info_largest, 0, 2)
            self.info_sub_layout.addWidget(info_available, 1, 0)
            self.info_sub_layout.addWidget(info_assigned, 1, 2)

            self.info_sub_layout.setColumnStretch(0, 0)
            self.info_sub_layout.setColumnStretch(1, 1)
            self.info_sub_layout.setColumnStretch(2, 0)

class _AssignmentFrame(QWidget):
    def __init__(self, parent: AdminWindow) -> None:
        super().__init__()
        self.__parent = parent
        self.assign_worker = None
        self.fetch_worker = None
        self.loading_overlay = LoadingOverlay(self, "Assigning the token...")

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.__parent._window_frame.setStyleSheet(GENERATE_PANEL_STYLESHEET) # can set special stylesheet also (Assignment)

        title = QLabel("Assign Available Tokens To Trainee")
        title.setObjectName("heading")
        input_frame = QFrame()
        input_frame.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        input_frame.setStyleSheet(ASSIGNMENT_PANEL_SUBFRAME_STYLESHEET) # can set special stylesheet also (Assignment)
        input_layout = QVBoxLayout(input_frame)
        input_sub_frame = QFrame()
        input_sub_frame.setStyleSheet(GENERATE_PANEL_INPUT_STYLESHEET) # can set special stylesheet also (Assignment)
        input_sub_layout = QGridLayout(input_sub_frame)
        input_sub_layout.setVerticalSpacing(50)
        input_sub_layout.setColumnMinimumWidth(2, 80)

        name_label = QLabel("Trainee Name:")
        desg_label = QLabel("Trainee Designation:")
        start_label = QLabel("Course Start Date:")
        end_label = QLabel("Course End Date:")
        token_label = QLabel("Select Token ID:")
        pref_label = QLabel("Meal Preference:")

        self.name_inp = SingleLineEdit()
        self.desg_inp = SingleLineEdit()
        self.start_inp = QDateEdit()
        self.end_inp = QDateEdit()
        self.token_inp = QComboBox()
        self.token_inp.addItem("Loading Token IDs...", "loading")
        self.token_inp.setEnabled(False)
        self.fetch_available_tokens()
        self.pref_inp = QComboBox()
        self.pref_inp.addItem("- Select -", "select")
        self.pref_inp.addItems(("VEG", "NON-VEG"))

        current_qdate = QDate.currentDate()
        self.start_inp.setCalendarPopup(True)
        self.end_inp.setCalendarPopup(True)
        self.start_inp.setMinimumDate(current_qdate)
        self.start_inp.dateChanged.connect(lambda new_date: self.end_inp.setMinimumDate(new_date))
        self.start_inp.setDate(current_qdate)
        self.end_inp.setDate(current_qdate)

        self.assign_btn = QPushButton("Assign")
        self.assign_btn.setFixedWidth(200)
        self.assign_btn.setStyleSheet(SUBMIT_BUTTON_STYLESHEET)
        self.assign_btn.clicked.connect(self.assign_token_to_trainee)

        input_sub_layout.addWidget(name_label, 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.name_inp, 0, 1)
        input_sub_layout.addWidget(desg_label, 0, 3, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.desg_inp, 0, 4)
        input_sub_layout.addWidget(start_label, 1, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.start_inp, 1, 1)
        input_sub_layout.addWidget(end_label, 1, 3, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.end_inp, 1, 4)
        input_sub_layout.addWidget(token_label, 2, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.token_inp, 2, 1)
        input_sub_layout.addWidget(pref_label, 2, 3, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.pref_inp, 2, 4)

        input_layout.addWidget(input_sub_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        input_layout.addWidget(self.assign_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addWidget(title, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(input_frame, stretch=3, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addStretch(stretch=2)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.loading_overlay.setGeometry(self.rect())

    def showEvent(self, event: QShowEvent):
        self.fetch_available_tokens()
        super().showEvent(event)
    
    def assign_token_to_trainee(self) -> None:
        name = self.name_inp.toPlainText()
        desg = self.desg_inp.toPlainText()
        start = self.start_inp.date().toString("yyyy-MM-dd")
        end = self.end_inp.date().toString("yyyy-MM-dd")
        token = self.token_inp.currentData()
        pref = self.pref_inp.currentText()

        if token == "loading":
            QMessageBox.warning(None, "Wait", "Hold on! The available token-IDs are being fetched!")
            return
        elif token == "no data":
            QMessageBox.warning(None, "Not Available", "No tokens are available for assignment! Generate new ones first!")
            return

        if all((name, desg, start, end, token!="select", self.pref_inp.currentData()!="select")):
            if (start < end):
                self.loading_overlay.show()
                self.assign_worker = ClientNetworkThread(
                    self, API_ENDPOINTS["assign-existing-token-to-trainee"], POST,
                    token_number=int(token), trainee_name=name, trainee_desg=desg,
                    course_start=start, course_end=end, meal_preference=pref
                )
                self.assign_worker.bind_and_start(self.on_api_success, _utilities.api_failure_coroutine)
            else:
                QMessageBox.warning(None, "Warning", "Please select a valid date (Course End Date)!")
                return
        else:
            QMessageBox.warning(None, "Incomplete Form", "Please fill out all the fields first!")
            return
    
    def fetch_available_tokens(self):
        self.fetch_worker = ClientNetworkThread(self, API_ENDPOINTS["fetch-available-token-list"], GET)
        self.fetch_worker.bind_and_start(self.on_api_success, _utilities.api_failure_coroutine)
    
    def on_api_success(self, action: str, data: Dict[str, Any]):
        print(f"Success caught for action: {action}")

        if action == API_ENDPOINTS["fetch-available-token-list"]:
            token_numbers = data.get("token_numbers")
            self.token_inp.clear()

            if token_numbers:
                self.token_inp.addItem("- Select -", "select")
                for token_number in token_numbers:
                    self.token_inp.addItem(f"Token ID ({token_number})", token_number)
                self.token_inp.setEnabled(True)
            else:
                self.token_inp.addItem("No Available Tokens!", "no data")
            
            self.assign_btn.setDisabled(False)

        elif action == API_ENDPOINTS["assign-existing-token-to-trainee"]:
            self.loading_overlay.hide()
            self.fetch_available_tokens()
            token_number = data.get("token_number")
            trainee_name = data.get("trainee_name")
            self.name_inp.clear()
            self.desg_inp.clear()
            QMessageBox.information(None, "Success", f"Successfully assigned Token ID ({token_number}) to {trainee_name}!")

class _CourseIntervalUpdateFrame(QWidget):
    def __init__(self, parent: AdminWindow) -> None:
        super().__init__()
        self.__parent = parent
        self.course_worker = None
        self.fetch_worker = None
        self.loading_overlay = LoadingOverlay(self, "Updating Course Interval...")
        self.trainee_rows = []

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.__parent._window_frame.setStyleSheet(GENERATE_PANEL_STYLESHEET) # can set special stylesheet also (Assignment)

        title = QLabel("Update Course Interval Of Trainees")
        title.setObjectName("heading")
        input_frame = QFrame()
        input_frame.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        input_frame.setStyleSheet(ASSIGNMENT_PANEL_SUBFRAME_STYLESHEET) # can set special stylesheet also (Assignment)
        input_layout = QVBoxLayout(input_frame)

        input_sub_frame = QFrame()
        input_sub_frame.setStyleSheet(GENERATE_PANEL_INPUT_STYLESHEET) # can set special stylesheet also (Assignment)
        input_sub_layout = QGridLayout(input_sub_frame)
        input_sub_layout.setVerticalSpacing(30)
        input_sub_layout.setColumnMinimumWidth(1, 50)

        date_label = QLabel("Select Updated Course End Date:")
        self.date_inp = QDateEdit()
        trainee_label = QLabel("Choose Trainees:")
        self.trainee_inp = QComboBox()
        self.add_btn = QPushButton(" + Add")

        current_qdate = QDate.currentDate()
        self.date_inp.setMinimumDate(current_qdate)
        self.date_inp.setDate(current_qdate)
        self.date_inp.setCalendarPopup(True)

        self.trainee_inp.addItem("Fetching Trainees...")
        self.trainee_inp.setEnabled(False)
        self.fetch_trainees()

        self.add_btn.setFixedWidth(100)
        self.add_btn.setStyleSheet(ADD_BUTTON_STYLESHEET)
        self.add_btn.clicked.connect(self.add_trainee)

        input_sub_layout.addWidget(date_label, 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.date_inp, 0, 2)
        input_sub_layout.addWidget(trainee_label, 1, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.trainee_inp, 1, 2)
        input_sub_layout.addWidget(self.add_btn, 1, 3)

        self.course_btn = QPushButton("Update")
        self.course_btn.setFixedWidth(200)
        self.course_btn.setStyleSheet(SUBMIT_BUTTON_STYLESHEET)
        self.course_btn.clicked.connect(self.update_course_interval)

        self.trainee_frame = QFrame()
        trainee_layout = QVBoxLayout(self.trainee_frame)
        trainee_list_label = QLabel("Trainees Selected")
        trainee_list_label.setStyleSheet(SUB_HEADING_STYLESHEET)

        self.trainee_list_layout = QGridLayout()
        self.trainee_list_layout.addWidget(QLabel("<b>Token ID</b>"), 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.trainee_list_layout.addWidget(QLabel("<b>Trainee Name</b>"), 0, 2, alignment=Qt.AlignmentFlag.AlignLeft)
        self.trainee_list_layout.addWidget(QLabel("<b>Designation</b>"), 0, 4, alignment=Qt.AlignmentFlag.AlignLeft)

        self.trainee_list_layout.setVerticalSpacing(30)
        self.trainee_list_layout.setColumnMinimumWidth(1, 100)
        self.trainee_list_layout.setColumnMinimumWidth(3, 100)

        trainee_layout.addWidget(trainee_list_label, alignment=Qt.AlignmentFlag.AlignCenter)
        trainee_layout.addLayout(self.trainee_list_layout)
        self.trainee_frame.hide()

        input_layout.addWidget(input_sub_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        input_layout.addWidget(self.course_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        input_layout.addWidget(self.trainee_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addWidget(title, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(input_frame, stretch=3, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addStretch(stretch=2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.loading_overlay.setGeometry(self.rect())

    def showEvent(self, event: QShowEvent):
        self.fetch_trainees()
        super().showEvent(event)
    
    def fetch_trainees(self):
        self.fetch_worker = ClientNetworkThread(self, API_ENDPOINTS["fetch-active-trainee-list"], GET)
        self.fetch_worker.bind_and_start(self.on_api_success, _utilities.api_failure_coroutine)
    
    def add_trainee(self):
        trainee_info = self.trainee_inp.currentData()

        if trainee_info == "loading":
            QMessageBox.warning(None, "Wait", "Hold on! The available token-IDs are being fetched!")
            return
        elif trainee_info == "no data":
            QMessageBox.warning(None, "Not Available", "No trainees have been assigned tokens yet!")
            return
        elif trainee_info == "select":
            QMessageBox.warning(None, "Not Selected", "Please select a trainee first!")
            return

        self.trainee_inp.setCurrentIndex(0)
        token, name, desg = trainee_info
        if token in [data["id"] for data in self.trainee_rows]:
            QMessageBox.warning(None, "Duplicate Entry", f"{name} (ID-{token}) has already been selected!")
            return

        rem_btn = QPushButton("Remove")
        rem_btn.setStyleSheet(ADD_BUTTON_STYLESHEET)
        trainee_dict = {
            "id": token,
            "token": QLabel(str(token)),
            "name": QLabel(name),
            "desg": QLabel(desg),
            "remove": rem_btn
        }
        rem_btn.clicked.connect(lambda: self.remove_trainee(trainee_dict))

        self.trainee_rows.append(trainee_dict)
        self.rebuild_grid()

    def remove_trainee(self, data: Dict[str, Union[int, QWidget]]):
        self.trainee_rows.remove(data)
        for item in data.values():
            if type(item)!=int:
                item.deleteLater()
        self.rebuild_grid()

    def rebuild_grid(self):
        while self.trainee_list_layout.count()>3:
            self.trainee_list_layout.takeAt(3)
        
        current_row = 1
        for row in self.trainee_rows:
            self.trainee_list_layout.addWidget(row["token"], current_row, 0)
            self.trainee_list_layout.addWidget(row["name"], current_row, 2)
            self.trainee_list_layout.addWidget(row["desg"], current_row, 4)
            self.trainee_list_layout.addWidget(row["remove"], current_row, 5)
            current_row += 1
        
        if self.trainee_rows:
            self.trainee_frame.show()
        else:
            self.trainee_frame.hide()
    
    def update_course_interval(self):
        if not self.trainee_rows:
            QMessageBox.warning(None, "Not Selected", "Please select at least one trainee to update!")
            return
        if self.date_inp.date() < QDate.currentDate():
            QMessageBox.warning(None, "Invalid Date", "Please select a valid end date for course!")
            return
        
        token_number_arr = [data["id"] for data in self.trainee_rows]
        new_end_date = self.date_inp.date().toString("yyyy-MM-dd")
        self.loading_overlay.show()
        self.course_worker = ClientNetworkThread(
            self, API_ENDPOINTS["change-course-interval-of-trainees"], POST,
            token_number_arr=token_number_arr, new_end_date=new_end_date
        )
        self.course_worker.bind_and_start(self.on_api_success, _utilities.api_failure_coroutine)

    def on_api_success(self, action: str, data: dict):
        print(f"Success caught for action: {action}")

        if action == API_ENDPOINTS["fetch-active-trainee-list"]:
            trainees = data.get("trainees")
            self.trainee_inp.clear()

            if trainees:
                self.trainee_inp.addItem("- Select -", "select")
                for token, name, desg in trainees:
                    self.trainee_inp.addItem(f"{name} (ID-{token})", (token, name, desg))
                self.trainee_inp.setEnabled(True)
            else:
                self.trainee_inp.addItem("No Trainees Found!", "no data")
        
        elif action == API_ENDPOINTS["change-course-interval-of-trainees"]:
            self.loading_overlay.hide()
            self.trainee_rows.clear()
            self.rebuild_grid()
            QMessageBox.information(None, "Success", data.get("message"))

class _SpecialConfigFrame(QWidget):
    def __init__(self, parent: AdminWindow) -> None:
        super().__init__()
        self.__parent = parent
        self.config_worker = None
        self.fetch_trainee_worker = None
        self.fetch_settings_worker = None
        self.loading_overlay = LoadingOverlay(self, "Creating new configurations...")
        self.trainee_rows = []

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.__parent._window_frame.setStyleSheet(GENERATE_PANEL_STYLESHEET) # can set special stylesheet also (Assignment)

        title = QLabel("Set Special Configuration For Trainees")
        title.setObjectName("heading")
        input_frame = QFrame()
        input_frame.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        input_frame.setStyleSheet(ASSIGNMENT_PANEL_SUBFRAME_STYLESHEET) # can set special stylesheet also (Assignment)
        input_layout = QVBoxLayout(input_frame)

        input_sub_frame = QFrame()
        input_sub_frame.setStyleSheet(SPECIAL_PANEL_INPUT_STYLESHEET) # can set special stylesheet also (Assignment)
        input_sub_layout = QGridLayout(input_sub_frame)
        input_sub_layout.setVerticalSpacing(30)
        input_sub_layout.setColumnMinimumWidth(1, 50)
        input_sub_layout.setRowMinimumHeight(1, 50)
        input_sub_layout.setRowMinimumHeight(7, 50)

        date_label = QLabel("Select Dates to apply configurations:")
        self.date_inp = ClickableColorCalendar()

        config_label = QLabel("<b><u><i>Edit Configurations</i></u></b>")
        breakfast_label = QLabel("Breakfast Slot:")
        self.breakfast_start_inp = QTimeEdit()
        self.breakfast_end_inp = QTimeEdit()
        lunch_label = QLabel("Lunch Slot:")
        self.lunch_start_inp = QTimeEdit()
        self.lunch_end_inp = QTimeEdit()
        dinner_label = QLabel("Dinner Slot:")
        self.dinner_start_inp = QTimeEdit()
        self.dinner_end_inp = QTimeEdit()
        suspend_label = QLabel("Suspend Trainee?")
        self.suspend_inp = ToggleSwitch()
        trainee_label = QLabel("Choose Trainees:")
        self.trainee_inp = QComboBox()
        self.add_btn = QPushButton(" + Add")

        self.time_inputs = (self.breakfast_start_inp, self.breakfast_end_inp, self.lunch_start_inp, self.lunch_end_inp, self.dinner_start_inp, self.dinner_end_inp)
        for inp in self.time_inputs:
            inp.setDisplayFormat("hh:mm AP")
        self.fetch_settings()

        self.suspend_inp.setChecked(False)

        self.trainee_inp.addItem("Fetching Trainees...")
        self.trainee_inp.setEnabled(False)
        self.fetch_trainees()

        self.add_btn.setFixedWidth(100)
        self.add_btn.setStyleSheet(ADD_BUTTON_STYLESHEET)
        self.add_btn.clicked.connect(self.add_trainee)

        input_sub_layout.addWidget(date_label, 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.date_inp, 0, 2)
        input_sub_layout.addWidget(config_label, 2, 0, alignment=Qt.AlignmentFlag.AlignLeft)

        input_sub_layout.addWidget(breakfast_label, 3, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.breakfast_start_inp, 3, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.breakfast_end_inp, 3, 2, alignment=Qt.AlignmentFlag.AlignRight)

        input_sub_layout.addWidget(lunch_label, 4, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.lunch_start_inp, 4, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.lunch_end_inp, 4, 2, alignment=Qt.AlignmentFlag.AlignRight)

        input_sub_layout.addWidget(dinner_label, 5, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.dinner_start_inp, 5, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.dinner_end_inp, 5, 2, alignment=Qt.AlignmentFlag.AlignRight)

        input_sub_layout.addWidget(suspend_label, 6, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.suspend_inp, 6, 1, alignment=Qt.AlignmentFlag.AlignLeft)

        input_sub_layout.addWidget(trainee_label, 8, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.trainee_inp, 8, 1, alignment=Qt.AlignmentFlag.AlignLeft)

        input_sub_layout.addWidget(self.add_btn, 8, 2)

        self.config_btn = QPushButton("Update")
        self.config_btn.setFixedWidth(200)
        self.config_btn.setStyleSheet(SUBMIT_BUTTON_STYLESHEET)
        self.config_btn.clicked.connect(self.set_special_config)

        self.trainee_frame = QFrame()
        trainee_layout = QVBoxLayout(self.trainee_frame)
        trainee_list_label = QLabel("Trainees Selected")
        trainee_list_label.setStyleSheet(SUB_HEADING_STYLESHEET)

        self.trainee_list_layout = QGridLayout()
        self.trainee_list_layout.addWidget(QLabel("<b>Token ID</b>"), 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.trainee_list_layout.addWidget(QLabel("<b>Trainee Name</b>"), 0, 2, alignment=Qt.AlignmentFlag.AlignLeft)
        self.trainee_list_layout.addWidget(QLabel("<b>Designation</b>"), 0, 4, alignment=Qt.AlignmentFlag.AlignLeft)

        self.trainee_list_layout.setVerticalSpacing(30)
        self.trainee_list_layout.setColumnMinimumWidth(1, 100)
        self.trainee_list_layout.setColumnMinimumWidth(3, 100)

        trainee_layout.addWidget(trainee_list_label, alignment=Qt.AlignmentFlag.AlignCenter)
        trainee_layout.addLayout(self.trainee_list_layout)
        self.trainee_frame.hide()

        input_layout.addWidget(input_sub_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        input_layout.addWidget(self.config_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        input_layout.addWidget(self.trainee_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addWidget(title, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(input_frame, stretch=3, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addStretch(stretch=2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.loading_overlay.setGeometry(self.rect())

    def showEvent(self, event: QShowEvent):
        self.fetch_trainees()
        self.fetch_settings()
        super().showEvent(event)
    
    def fetch_trainees(self):
        self.fetch_trainee_worker = ClientNetworkThread(self, API_ENDPOINTS["fetch-active-trainee-list"], GET)
        self.fetch_trainee_worker.bind_and_start(self.on_api_success, _utilities.api_failure_coroutine)
    
    def fetch_settings(self):
        self.fetch_settings_worker = ClientNetworkThread(self, API_ENDPOINTS["fetch-current-settings"], GET)
        self.fetch_settings_worker.bind_and_start(self.on_api_success, _utilities.api_failure_coroutine)
    
    def set_special_config(self):
        if not self.trainee_rows:
            QMessageBox.warning(None, "Not Selected", "Please select at least one trainee to update!")
            return
        
        get_time = lambda inp: inp.time().toString("HH:mm:ss")
        
        token_number_arr = [data["id"] for data in self.trainee_rows]
        dates_arr = [date.toString("yyyy-MM-dd") for date in self.date_inp.selected_dates]
        date_interval_arr = _utilities.generate_date_intervals(dates_arr)
        breakfast_time_slot = f"{get_time(self.breakfast_start_inp)}-{get_time(self.breakfast_end_inp)}"
        lunch_time_slot = f"{get_time(self.lunch_start_inp)}-{get_time(self.lunch_end_inp)}"
        dinner_time_slot = f"{get_time(self.dinner_start_inp)}-{get_time(self.dinner_end_inp)}"
        is_suspended = self.suspend_inp.isChecked()

        if not date_interval_arr:
            QMessageBox.warning(None, "Not Selected", "Please select at least one date to update!")
            return

        self.loading_overlay.show()
        self.config_worker = ClientNetworkThread(
            self, API_ENDPOINTS["configure-special-settings-for-trainees"], POST,
            token_number_arr=token_number_arr, date_interval_arr=date_interval_arr,
            breakfast_time_slot=breakfast_time_slot, lunch_time_slot=lunch_time_slot,
            dinner_time_slot=dinner_time_slot, is_suspended=is_suspended
        )
        self.config_worker.bind_and_start(self.on_api_success, _utilities.api_failure_coroutine)

    def add_trainee(self):
        trainee_info = self.trainee_inp.currentData()

        if trainee_info == "loading":
            QMessageBox.warning(None, "Wait", "Hold on! The available token-IDs are being fetched!")
            return
        elif trainee_info == "no data":
            QMessageBox.warning(None, "Not Available", "No trainees have been assigned tokens yet!")
            return
        elif trainee_info == "select":
            QMessageBox.warning(None, "Not Selected", "Please select a trainee first!")
            return

        self.trainee_inp.setCurrentIndex(0)
        token, name, desg = trainee_info
        if token in [data["id"] for data in self.trainee_rows]:
            QMessageBox.warning(None, "Duplicate Entry", f"{name} (ID-{token}) has already been selected!")
            return

        rem_btn = QPushButton("Remove")
        rem_btn.setStyleSheet(ADD_BUTTON_STYLESHEET)
        trainee_dict = {
            "id": token,
            "token": QLabel(str(token)),
            "name": QLabel(name),
            "desg": QLabel(desg),
            "remove": rem_btn
        }
        rem_btn.clicked.connect(lambda: self.remove_trainee(trainee_dict))

        self.trainee_rows.append(trainee_dict)
        self.rebuild_grid()

    def remove_trainee(self, data: Dict[str, Union[int, QWidget]]):
        self.trainee_rows.remove(data)
        for item in data.values():
            if type(item)!=int:
                item.deleteLater()
        self.rebuild_grid()

    def rebuild_grid(self):
        while self.trainee_list_layout.count()>3:
            self.trainee_list_layout.takeAt(3)
        
        self.current_row = 1
        for row in self.trainee_rows:
            self.trainee_list_layout.addWidget(row["token"], self.current_row, 0)
            self.trainee_list_layout.addWidget(row["name"], self.current_row, 2)
            self.trainee_list_layout.addWidget(row["desg"], self.current_row, 4)
            self.trainee_list_layout.addWidget(row["remove"], self.current_row, 5)
            self.current_row += 1
        
        if self.trainee_rows:
            self.trainee_frame.show()
        else:
            self.trainee_frame.hide()

    def on_api_success(self, action: str, data: dict):
        print(f"Success caught for action: {action}")

        if action == API_ENDPOINTS["fetch-active-trainee-list"]:
            trainees = data.get("trainees")
            self.trainee_inp.clear()

            if trainees:
                self.trainee_inp.addItem("- Select -", "select")
                for token, name, desg in trainees:
                    self.trainee_inp.addItem(f"{name} (ID-{token})", (token, name, desg))
                self.trainee_inp.setEnabled(True)
            else:
                self.trainee_inp.addItem("No Trainees Found!", "no data")
      
        elif action == API_ENDPOINTS["fetch-current-settings"]:
            if data:
                breakfast = data.get(ALLOWED_CONFIG_KEYS[0])
                lunch = data.get(ALLOWED_CONFIG_KEYS[1])
                dinner = data.get(ALLOWED_CONFIG_KEYS[2])

                convert = lambda s,f: QTime.fromString(s, f)
                form = "HH:mm:ss"

                if breakfast:
                    start, end = breakfast.split('-')
                    self.breakfast_start_inp.setTime(convert(start, form))
                    self.breakfast_end_inp.setTime(convert(end, form))
                if lunch:
                    start, end = lunch.split('-')
                    self.lunch_start_inp.setTime(convert(start, form))
                    self.lunch_end_inp.setTime(convert(end, form))
                if dinner:
                    start, end = dinner.split('-')
                    self.dinner_start_inp.setTime(convert(start, form))
                    self.dinner_end_inp.setTime(convert(end, form))
        elif action == API_ENDPOINTS["configure-special-settings-for-trainees"]:
            self.loading_overlay.hide()
            self.fetch_settings()
            self.suspend_inp.setChecked(False)
            self.trainee_rows.clear()
            self.rebuild_grid()
            QMessageBox.information(None, "Success", data.get("message"))

class _SettingsFrame(QWidget):
    def __init__(self, parent: AdminWindow) -> None:
        super().__init__()
        self.__parent = parent
        self.settings_worker = None
        self.fetch_worker = None
        self.loading_overlay = LoadingOverlay(self, "Updating Settings...")

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.__parent._window_frame.setStyleSheet(GENERATE_PANEL_STYLESHEET) # can set special stylesheet also (Assignment)

        title = QLabel("Update Settings")
        title.setObjectName("heading")
        input_frame = QFrame()
        input_frame.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        input_frame.setStyleSheet(ASSIGNMENT_PANEL_SUBFRAME_STYLESHEET) # can set special stylesheet also (Assignment)
        input_layout = QVBoxLayout(input_frame)

        input_sub_frame = QFrame()
        input_sub_frame.setStyleSheet(SPECIAL_PANEL_INPUT_STYLESHEET) # can set special stylesheet also (Assignment)
        input_sub_layout = QGridLayout(input_sub_frame)
        input_sub_layout.setVerticalSpacing(30)
        input_sub_layout.setColumnMinimumWidth(1, 50)
        input_sub_layout.setColumnMinimumWidth(3, 50)

        breakfast_label = QLabel("Breakfast Time Slot:") #breakfast_time_slot
        self.breakfast_start_inp = QTimeEdit()
        self.breakfast_end_inp = QTimeEdit()
        lunch_label = QLabel("Lunch Time Slot:") #lunch_time_slot
        self.lunch_start_inp = QTimeEdit()
        self.lunch_end_inp = QTimeEdit()
        dinner_label = QLabel("Dinner Time Slot:") #dinner_time_slot
        self.dinner_start_inp = QTimeEdit()
        self.dinner_end_inp = QTimeEdit()
        veg_label = QLabel("Select Only Veg Days:") #only_veg_days
        self.veg_inp = DaySelectionMapping()

        self.time_inputs = (self.breakfast_start_inp, self.breakfast_end_inp, self.lunch_start_inp, self.lunch_end_inp, self.dinner_start_inp, self.dinner_end_inp)
        for inp in self.time_inputs:
            inp.setDisplayFormat("hh:mm AP")
        self.fetch_settings()

        input_sub_layout.addWidget(breakfast_label, 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.breakfast_start_inp, 0, 2)
        input_sub_layout.addWidget(self.breakfast_end_inp, 0, 4)
        input_sub_layout.addWidget(lunch_label, 1, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.lunch_start_inp, 1, 2)
        input_sub_layout.addWidget(self.lunch_end_inp, 1, 4)
        input_sub_layout.addWidget(dinner_label, 2, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.dinner_start_inp, 2, 2)
        input_sub_layout.addWidget(self.dinner_end_inp, 2, 4)
        input_sub_layout.addWidget(veg_label, 4, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        input_sub_layout.addWidget(self.veg_inp, 4, 2, 1, 3)

        self.set_btn = QPushButton("Update")
        self.set_btn.setFixedWidth(200)
        self.set_btn.setStyleSheet(SUBMIT_BUTTON_STYLESHEET)
        self.set_btn.clicked.connect(self.update_settings)

        input_layout.addWidget(input_sub_frame, alignment=Qt.AlignmentFlag.AlignCenter)
        input_layout.addWidget(self.set_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.main_layout.addWidget(title, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(input_frame, stretch=3, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addStretch(stretch=2)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.loading_overlay.setGeometry(self.rect())

    def showEvent(self, event: QShowEvent):
        self.fetch_settings()
        super().showEvent(event)

    def fetch_settings(self):
        self.fetch_settings_worker = ClientNetworkThread(self, API_ENDPOINTS["fetch-current-settings"], GET)
        self.fetch_settings_worker.bind_and_start(self.on_api_success, _utilities.api_failure_coroutine)

    def update_settings(self):
        convert = lambda inp: inp.time().toString("HH:mm:ss")
        breakfast = f"{convert(self.breakfast_start_inp)}-{convert(self.breakfast_end_inp)}"
        lunch = f"{convert(self.lunch_start_inp)}-{convert(self.lunch_end_inp)}"
        dinner = f"{convert(self.dinner_start_inp)}-{convert(self.dinner_end_inp)}"
        veg_days = ",".join(self.veg_inp.get_selected_days())

        self.loading_overlay.show()
        self.settings_worker = ClientNetworkThread(
            self, API_ENDPOINTS["configure-settings-key-value-pairs"], POST,
            keys=ALLOWED_CONFIG_KEYS, values=(breakfast, lunch, dinner, veg_days)
        )
        self.settings_worker.bind_and_start(self.on_api_success, _utilities.api_failure_coroutine)

    def on_api_success(self, action: str, data: dict):
        print(f"Success caught for action: {action}")

        if action == API_ENDPOINTS["fetch-current-settings"]:
            if data:
                breakfast = data.get(ALLOWED_CONFIG_KEYS[0])
                lunch = data.get(ALLOWED_CONFIG_KEYS[1])
                dinner = data.get(ALLOWED_CONFIG_KEYS[2])
                only_veg = data.get(ALLOWED_CONFIG_KEYS[3])

                convert = lambda s,f: QTime.fromString(s, f)
                form = "HH:mm:ss"

                if breakfast:
                    start, end = breakfast.split('-')
                    self.breakfast_start_inp.setTime(convert(start, form))
                    self.breakfast_end_inp.setTime(convert(end, form))
                if lunch:
                    start, end = lunch.split('-')
                    self.lunch_start_inp.setTime(convert(start, form))
                    self.lunch_end_inp.setTime(convert(end, form))
                if dinner:
                    start, end = dinner.split('-')
                    self.dinner_start_inp.setTime(convert(start, form))
                    self.dinner_end_inp.setTime(convert(end, form))
                if only_veg:
                    self.veg_inp.set_selected_days(only_veg.split(','))
        
        elif action == API_ENDPOINTS["configure-settings-key-value-pairs"]:
            self.loading_overlay.hide()
            QMessageBox.information(None, "Success", data.get("message"))

class AdminWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.__WINDOWS = (_GenerationFrame, _AssignmentFrame, _CourseIntervalUpdateFrame, _SpecialConfigFrame, _SettingsFrame)
        self.__current_window = None
        self.__active_windows = [None for _ in range(len(self.__WINDOWS))]

        screen = QApplication.primaryScreen().geometry()
        screen_width = screen.width()
        screen_height = screen.height()
        self.setMinimumSize(screen_width-300, screen_height-200)
        self.setWindowTitle("Canteen Manager App (Admin)")

        main_central_widget = QWidget(self)
        main_central_widget.setStyleSheet(ROOT_STYLESHEET)
        self.setCentralWidget(main_central_widget)

        outer_layout = QVBoxLayout(main_central_widget)
        outer_layout.setContentsMargins(0,0,0,0)
        outer_layout.setSpacing(0)

        top_panel_frame = QFrame()
        top_panel_frame.setStyleSheet(PANEL_BORDER_STYLESHEET + TITLE_STYLESHEET)
        top_panel_layout = QVBoxLayout(top_panel_frame)

        label = QLabel("Admin Panel")
        top_panel_layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout = QHBoxLayout()
        left_panel_frame = QFrame()
        left_panel_frame.setStyleSheet(PANEL_BORDER_STYLESHEET + SIDE_PANEL_STYLESHEET)
        left_panel_layout = QVBoxLayout(left_panel_frame)
        
        generate_tab_switch_btn = QPushButton("Generate New QR Tokens")
        assign_tab_switch_btn = QPushButton("Assign Token To Trainee")
        course_tab_switch_btn = QPushButton("Edit Course Interval")
        special_tab_switch_btn = QPushButton("Set Special Configurations")
        settings_tab_switch_btn = QPushButton("Settings")
        self.__window_switch_buttons = (generate_tab_switch_btn, assign_tab_switch_btn, course_tab_switch_btn, special_tab_switch_btn, settings_tab_switch_btn)

        for i, btn in enumerate(self.__window_switch_buttons):
            btn.clicked.connect(lambda checked, idx=i: self.__switch_window(idx))
            left_panel_layout.addWidget(btn)

        left_panel_layout.addStretch(1)
        left_panel_layout.setSpacing(0)
        left_panel_layout.setContentsMargins(0,0,0,0)

        self._window_frame = QFrame()
        self._window_frame.setStyleSheet(PANEL_BORDER_STYLESHEET)
        self.__window_layout = QVBoxLayout(self._window_frame)
        self.__window_layout.setContentsMargins(10, 10, 10, 10)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidget(self._window_frame)
        self._scroll_area.setWidgetResizable(True)

        main_layout.addWidget(left_panel_frame, 1)
        main_layout.addWidget(self._scroll_area, 4)

        outer_layout.addWidget(top_panel_frame, 1)
        outer_layout.addLayout(main_layout, 9)

        self.__switch_window(4)

    def __switch_window(self, window_sl_no: int) -> None:
        if (self.__current_window != window_sl_no):
            self.__current_window = window_sl_no

            if (self.__active_windows[window_sl_no] == None):
                newCreatedWindow = self.__WINDOWS[window_sl_no](self) # Create the class object
                self.__window_layout.addWidget(newCreatedWindow)
                self.__active_windows[window_sl_no] = newCreatedWindow
            else:
                self.__window_layout.addWidget(self.__active_windows[window_sl_no])
            
            for i in range(len(self.__WINDOWS)):
                if self.__active_windows[i]:
                    self.__active_windows[i].hide()
                    self.__window_switch_buttons[i].setStyleSheet(SIDE_PANEL_STYLESHEET)
            self.__active_windows[window_sl_no].show()
            self.__window_switch_buttons[window_sl_no].setStyleSheet(SIDE_PANEL_STYLESHEET + SELECTED_WINDOW_BUTTON_STYLESHEET)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AdminWindow()
    window.show()
    sys.exit(app.exec())