from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
from PyQt6.QtCore import QRectF, QSize, Qt, pyqtProperty, QPropertyAnimation, QDate, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QColor, QKeyEvent, QMovie, QPainter, QTextCharFormat
from PyQt6.QtWidgets import (
    QAbstractButton,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
    QCalendarWidget,
    QPushButton,
    QHBoxLayout,
    QFileDialog
)

import os
import io
import qrcode
from reportlab.lib.pagesizes import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.colors import HexColor

__all__ = [
    "POST", "GET", "WEEKDAYS", "WEEKDAYS_ABBR", "API_ENDPOINTS", "ALLOWED_CONFIG_KEYS",
    "UtilityFunctions", "AppStateManager",
    "ToggleSwitch", "SingleLineEdit", "LoadingOverlay",
    "ClickableColorCalendar", "DaySelectionMapping"
]

POST = "POST"
GET = "GET"
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
WEEKDAYS_ABBR = (day[:3] for day in WEEKDAYS)

API_ENDPOINTS = {
    "fetch-physical-token-stats": "get-existing-token-stats",
    "fetch-status-wise-token-list": "get-tokens-by-status",
    "fetch-unassigned-token-numbers-and-ids": "get-available-tokens-number-and-id",
    "fetch-active-trainee-list": "get-trainee-list",
    "fetch-current-settings": "get-settings",
    "fetch-total-meal-preferences-count": "get-total-meal-data",
    "fetch-scanned-meal-preferences-count": "get-scanned-meal-data",
    "configure-settings-key-value-pairs": "configure-settings",
    "generate-new-physical-qr-token": "generate-new-token",
    "assign-existing-token-to-trainee": "assign-token",
    "verify-qr-token-scanned-by-trainee": "verify-token",
    "verify-qr-token-input-by-manager": "verify-token-manual",
    "change-course-interval-of-trainees": "change-course-interval",
    "configure-special-settings-for-trainees": "apply-special-config",
    "destroy-wasted-tokens-and-replace-if-assigned": "destroy-token",
    "nudge-backend-to-save-to-local-cache": "sync-nudge"
}

ALLOWED_CONFIG_KEYS = ("breakfast_time_slot", "lunch_time_slot", "dinner_time_slot", "only_veg_days")

class UtilityFunctions:
    @staticmethod
    def get_current_ist_datetime() -> datetime:
        aware_current_time_utc = datetime.now(timezone.utc)
        aware_current_time_ist = aware_current_time_utc + timedelta(hours=5, minutes=30)
        current_time_ist = aware_current_time_ist.replace(tzinfo=None)
        return current_time_ist
    
    @staticmethod
    def is_time_in_slot(check_time: str, time_slot: str) -> bool:
        start_time, end_time = tuple(map(lambda x: datetime.strptime(x.strip(), "%H:%M:%S").time(), time_slot.split('-')))
        measurable_check_time = datetime.strptime(check_time.strip(), "%H:%M:%S").time()

        if start_time <= end_time:
            return (start_time <= measurable_check_time <= end_time)
        else:
            return (start_time <= measurable_check_time or measurable_check_time <= end_time)
    
    @staticmethod
    def api_failure_coroutine(action: str, error_msg: str) -> None:
        print(f"Error caught on action: {action}")
        print(f"Error: {error_msg}")
    
    @staticmethod
    def generate_date_intervals(dates_arr: List[str]) -> List[str]:
        if not dates_arr:
            return []
        
        form = "yyyy-MM-dd"
        intervals = []

        qdates = sorted(list(set([QDate.fromString(d, form) for d in dates_arr])))
        start_date = qdates[0]
        prev_date = qdates[0]

        for current_date in qdates[1:]:
            if prev_date.addDays(1) == current_date:
                prev_date = current_date
            else:
                intervals.append(f"{start_date.toString(form)}T{prev_date.toString(form)}")
                start_date = current_date
                prev_date = current_date

        intervals.append(f"{start_date.toString(form)}T{prev_date.toString(form)}")
        return intervals
    
    @staticmethod
    def get_save_path(parent: QWidget, caption: str, default_filename: str, file_filter: str):
        """Opens a native file dialog drawer and returns a string path."""
        # Setup optional configuration constraints

        # Arguments: parent, window title, default path/file name, file extensions allowed
        file_path, selected_filter = QFileDialog.getSaveFileName(parent, caption, default_filename, file_filter)

        if not file_path:
            print("User cancelled the save operation.")
            return None

        print(f"Target save path selected: {file_path}")
        return file_path
    
    @staticmethod
    def draw_background_color(canvas, doc):
        """Fires automatically on every page before layout flowables are drawn."""
        canvas.saveState()
        canvas.setFillColor(HexColor("#FAF7F2")) 
        
        # Draw a rectangle covering the absolute boundaries of the page surface area
        canvas.rect(0, 0, doc.pagesize[0], doc.pagesize[1], fill=1, stroke=0)
        canvas.restoreState()
    
    @staticmethod
    def generate_pdf(tokens_list: List[Dict[str, Any]], path: str) -> bool:
        try:
            tokens_list = sorted(tokens_list, key=lambda token: token["token_number"])

            # Build the template document object structure
            ID_CARD_SIZE = (2.125 * inch, 2.750 * inch)
            doc = SimpleDocTemplate(
                path, 
                pagesize=ID_CARD_SIZE,
                rightMargin=10, leftMargin=10, topMargin=10, bottomMargin=10
            )
            
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'TokenTitle', parent=styles['Heading1'], fontSize=8, leading=11, 
                textColor='#7A1E1E', alignment=TA_CENTER, spaceAfter=4
            )
            detail_style = ParagraphStyle(
                'TokenDetail', parent=styles['Normal'], fontSize=7, leading=8, 
                textColor='#333333', alignment=TA_CENTER, spaceAfter=4
            )
            footer_style = ParagraphStyle(
                'TokenFooter', parent=styles['Italic'], fontSize=4, leading=6, 
                textColor='#777777', alignment=TA_CENTER, spaceBefore=4
            )

            story = []

            for idx, token_data in enumerate(tokens_list):
                token_num = token_data.get("token_number")
                token_id_str = token_data.get("token_id")

                # Layout spacing & title blocks
                story.append(Spacer(1, 4))
                story.append(Paragraph("CANTEEN CARD\n(MDZTI/APDJ)", title_style))
                story.append(Spacer(1, 2))
                
                # Metadata metrics text structures
                story.append(Paragraph(f"<b>TOKEN NUMBER:</b> {token_num}", detail_style))
                story.append(Spacer(1, 2))

                # Build the matrix canvas payload structure 
                qr = qrcode.QRCode(version=1, box_size=4, border=4)
                qr.add_data(token_id_str)
                qr.make(fit=True)
                qr_img = qr.make_image(fill_color="#000000", back_color="white")
                
                # Compress image block matrix down to a memory bytes segment
                img_buffer = io.BytesIO()
                qr_img.save(img_buffer, format="PNG")
                img_buffer.seek(0)
                
                # Add image component object to file layout queue
                reportlab_qr = Image(img_buffer, width=80, height=80)
                story.append(reportlab_qr)
                
                story.append(Paragraph("Notice: This token is property of the Hostel Management. Verification required upon entry.", footer_style))
                
                # Slice page boundary canvas profiles sequentially 
                if idx < len(tokens_list) - 1:
                    story.append(PageBreak())

            doc.build(
                story,
                onFirstPage=UtilityFunctions.draw_background_color,
                onLaterPages=UtilityFunctions.draw_background_color
            )
            print(f"PDF created successfully at: {path}")
            return True

        except Exception as e:
            print(f"Failed to generate local client report template: {e}")
            return False

class ToggleSwitch(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setSizePolicy(self.sizePolicy().Policy.Fixed, self.sizePolicy().Policy.Fixed)
        
        # Define internal geometry properties
        self._thumb_position = 3.0
        self._track_opacity = 0.5
        
        # Color palettes
        self._track_checked_color = QColor("#0078d4")
        self._track_unchecked_color = QColor("#cccccc")
        self._thumb_color = QColor("#ffffff")
        
        # Connect toggle signal to kick off the sliding track animation
        self.toggled.connect(self._animate_toggle)

    @pyqtProperty(float)
    def thumb_position(self) -> float:
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos: float):
        self._thumb_position = pos
        self.update() # Force repaint canvas frame layout

    def sizeHint(self) -> QSize:
        return QSize(50, 28)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Setup layout canvas boundaries
        w = self.width()
        h = self.height()
        
        # 2. Assign dynamic active track state coloring configurations
        track_color = self._track_checked_color if self.isChecked() else self._track_unchecked_color
        
        # 3. Paint the slider pill track capsule background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(QRectF(0, 0, w, h), h / 2.0, h / 2.0)
        
        # 4. Paint the sliding handle circle (Thumb)
        painter.setBrush(self._thumb_color)
        thumb_diameter = h - 6.0
        painter.drawEllipse(QRectF(self._thumb_position, 3.0, thumb_diameter, thumb_diameter))
        
        painter.end()

    def _animate_toggle(self, checked: bool):
        # Calculate start/end track limits based on runtime widths
        start_pos = 3.0
        end_pos = self.width() - (self.height() - 6.0) - 3.0
        
        # Configure interpolation target positions
        self.anim = QPropertyAnimation(self, b"thumb_position")
        self.anim.setDuration(200) # Smooth speed layout latency duration in milliseconds
        self.anim.setStartValue(start_pos if checked else end_pos)
        self.anim.setEndValue(end_pos if checked else start_pos)
        self.anim.start()

class SingleLineEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.document().setMaximumBlockCount(1)
        self.document().setDocumentMargin(0)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(40)
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.accept()
        elif event.key() == Qt.Key.Key_Tab:
            self.focusNextChild()
            event.accept()
        elif event.key() == Qt.Key.Key_Backtab:
            self.focusPreviousChild()
            event.accept()
        else:
            super().keyPressEvent(event)

class LoadingOverlay(QWidget):
    def __init__(self, parent: QWidget, message: str = "Processing request..."):
        super().__init__(parent)
        
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.label = QLabel(message)
        self.label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 14px; background: transparent;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.spinner = QLabel()
        self.movie = QMovie("assets/loader.gif")
        self.movie.setScaledSize(QSize(100, 100))
        self.spinner.setMovie(self.movie)
        self.movie.start()
        main_layout.addStretch()
        main_layout.addWidget(self.spinner, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.label)
        main_layout.addStretch()
        
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Black backdrop with 40% transparency layer
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        painter.end()

    def resizeEvent(self, event):
        # Ensure the overlay stretches to match the parent frame dynamically
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())
        super().resizeEvent(event)
    
    def show(self):
        super().show()
        self.raise_()

class ClickableColorCalendar(QWidget):
    def __init__(self):
        super().__init__()
        self.fmt = QTextCharFormat()
        self.selected_dates: set[QDate] = set()
        layout = QVBoxLayout(self)
        
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self.handle_date_click)
        
        layout.addWidget(self.calendar)

    def handle_date_click(self, date: QDate):
        if date < QDate.currentDate():
            return

        if date in self.selected_dates:
            self.selected_dates.remove(date)
            # Setting background to transparent restores the default calendar style
            self.fmt.setBackground(QColor(Qt.GlobalColor.transparent))
            self.fmt.setForeground(QColor(Qt.GlobalColor.black)) # Reset text to black
        else:
            self.selected_dates.add(date)
            # Apply your custom highlight color theme
            self.fmt.setBackground(QColor("#6388a4")) # Modern blue accent
            self.fmt.setForeground(QColor(Qt.GlobalColor.white)) # Crisp white text digits
            
        # Apply the format to the specific grid cell row layout
        self.calendar.setDateTextFormat(date, self.fmt)
    
    def clear(self):
        self.fmt.setBackground(QColor(Qt.GlobalColor.transparent))
        self.fmt.setForeground(QColor(Qt.GlobalColor.black))
        for date in self.selected_dates:
            self.calendar.setDateTextFormat(date, self.fmt)
        self.selected_dates.clear()

class DaySelectionMapping(QWidget):
    # Custom signal that emits a list of selected day strings whenever a change occurs
    selection_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6) # Tight, clean spacing between pills
        
        self.days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        self.buttons = {}

        for day in self.days:
            btn = QPushButton(day)
            btn.setCheckable(True) 
            
            # Modern pill design
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f5f5f5;
                    border: 1px solid #dcdcdc;
                    border-radius: 16px; /* High radius forms a perfect pill shape */
                    color: #333333;
                    font-weight: bold;
                    min-width: 45px;
                    min-height: 32px;
                    padding: 4px;
                }
                QPushButton:hover {
                    background-color: #eaeaea;
                    border: 1px solid #b3b3b3;
                }
                /* Visual layout state when actively latched down */
                QPushButton:checked {
                    background-color: #e1f5fe;
                    border: 1px solid #0288d1;
                    color: #0288d1;
                }
            """)
            
            # Track buttons by their full name string
            self.buttons[day] = btn
            layout.addWidget(btn)
            
            # Forward the click to our global selection state handler
            btn.clicked.connect(self._on_day_toggled)

    def _on_day_toggled(self):
        # Emit the updated collection of strings downstream
        self.selection_changed.emit(self.get_selected_days())

    def get_selected_days(self) -> list[str]:
        return [day for day, btn in self.buttons.items() if btn.isChecked()]

    def set_selected_days(self, days_list: list[str]):
        """Programmatically check buttons (useful when loading from your database)"""
        for day, btn in self.buttons.items():
            btn.setChecked(day in days_list)

class AppStateManager(QObject):
    token_stats_updated = pyqtSignal(dict)
    tokens_by_status_updated = pyqtSignal(dict)
    active_trainees_updated = pyqtSignal(list)
    settings_updated = pyqtSignal(dict)
    total_meal_count_updated = pyqtSignal(dict)
    scanned_meal_count_updated = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

        self.token_stats = {}
        self.tokens_by_status = {}
        self.active_trainees = []
        self.settings = {}
        self.total_meal_count = {}

        self.dirty_bits = {
            "token_stats": True,
            "tokens_by_status": True,
            "active_trainees": True,
            "settings": True,
            "total_meal_count": True,
        }

        self.workers = []

        self.scanned_meal_count = {}
        self.scan_poll_timer = QTimer(self)
        self.scan_poll_timer.setInterval(5000)
        self.scan_poll_timer.timeout.connect(self.__fetch_scanned_meal_count)

    def invalidate_cache(self, key: str):
        """Called when API POST success occurs"""
        if key in self.dirty_bits:
            self.dirty_bits[key] = True
    
    def ensure_fresh_data(self, key: str):
        """Called by Panel Views. If clean simple switch, if dirty spawn GET request thread"""
        if key == "scanned_meal_count":
            self.__fetch_scanned_meal_count()

        if self.dirty_bits.get(key, False):
            if key == "token_stats":
                self.__fetch_token_stats()
            elif key == "tokens_by_status":
                self.__fetch_tokens_by_status()
            elif key == "active_trainees":
                self.__fetch_active_trainees()
            elif key == "settings":
                self.__fetch_settings()
            elif key == "total_meal_count":
                self.__fetch_total_meal_count()
        else:
            if key == "token_stats":
                self.token_stats_updated.emit(self.token_stats)
            elif key == "tokens_by_status":
                self.tokens_by_status_updated.emit(self.tokens_by_status)
            elif key == "active_trainees":
                self.active_trainees_updated.emit(self.active_trainees)
            elif key == "settings":
                self.settings_updated.emit(self.settings)
            elif key == "total_meal_count":
                self.total_meal_count_updated.emit(self.total_meal_count)
        
    def __fetch_token_stats(self):
        from core.client_network import ClientNetworkThread
        worker = ClientNetworkThread(self, API_ENDPOINTS["fetch-physical-token-stats"], GET)
        self.workers.append(worker)

        def on_success(action, data):
            print(f"Fetched by State Manager: {action}")
            self.token_stats = data
            self.dirty_bits["token_stats"] = False
            if worker in self.workers: self.workers.remove(worker)
            self.token_stats_updated.emit(self.token_stats)
        
        def on_failure(action, error):
            print(f"Error on {action}: {error}")
            if worker in self.workers: self.workers.remove(worker)

        worker.bind_and_start(on_success, on_failure)

    def __fetch_tokens_by_status(self):
        from core.client_network import ClientNetworkThread
        worker = ClientNetworkThread(self, API_ENDPOINTS["fetch-status-wise-token-list"], GET)
        self.workers.append(worker)

        def on_success(action, data):
            print(f"Fetched by State Manager: {action}")
            self.tokens_by_status = data
            self.tokens_by_status["tokens_available"] = sorted(data.get("tokens_available"))
            self.dirty_bits["tokens_by_status"] = False
            if worker in self.workers: self.workers.remove(worker)
            self.tokens_by_status_updated.emit(self.tokens_by_status)

        def on_failure(action, error):
            print(f"Error on {action}: {error}")
            if worker in self.workers: self.workers.remove(worker)

        worker.bind_and_start(on_success, on_failure)

    def __fetch_active_trainees(self):
        from core.client_network import ClientNetworkThread
        worker = ClientNetworkThread(self, API_ENDPOINTS["fetch-active-trainee-list"], GET)
        self.workers.append(worker)

        def on_success(action, data):
            print(f"Fetched by State Manager: {action}")
            self.active_trainees = sorted(data.get("trainees"), key=lambda item: item[0])
            self.dirty_bits["active_trainees"] = False
            if worker in self.workers: self.workers.remove(worker)
            self.active_trainees_updated.emit(self.active_trainees)

        def on_failure(action, error):
            print(f"Error on {action}: {error}")
            if worker in self.workers: self.workers.remove(worker)

        worker.bind_and_start(on_success, on_failure)

    def __fetch_settings(self):
        from core.client_network import ClientNetworkThread
        worker = ClientNetworkThread(self, API_ENDPOINTS["fetch-current-settings"], GET)
        self.workers.append(worker)

        def on_success(action, data):
            print(f"Fetched by State Manager: {action}")
            self.settings = data
            self.dirty_bits["settings"] = False
            if worker in self.workers: self.workers.remove(worker)
            self.settings_updated.emit(self.settings)

        def on_failure(action, error):
            print(f"Error on {action}: {error}")
            if worker in self.workers: self.workers.remove(worker)

        worker.bind_and_start(on_success, on_failure)

    def __fetch_total_meal_count(self):
        from core.client_network import ClientNetworkThread
        current_date = UtilityFunctions.get_current_ist_datetime().strftime("%Y-%m-%d")
        worker = ClientNetworkThread(self, API_ENDPOINTS["fetch-total-meal-preferences-count"], GET, target_date=current_date)
        self.workers.append(worker)

        def on_success(action, data):
            print(f"Fetched by State Manager: {action}")
            self.total_meal_count = data
            self.dirty_bits["total_meal_count"] = False
            if worker in self.workers: self.workers.remove(worker)
            self.total_meal_count_updated.emit(self.total_meal_count)

        def on_failure(action, error):
            print(f"Error on {action}: {error}")
            if worker in self.workers: self.workers.remove(worker)

        worker.bind_and_start(on_success, on_failure)
    
    def __fetch_scanned_meal_count(self):
        from core.client_network import ClientNetworkThread
        current_date = UtilityFunctions.get_current_ist_datetime().strftime("%Y-%m-%d")
        worker = ClientNetworkThread(self, API_ENDPOINTS["fetch-scanned-meal-preferences-count"], GET, target_date=current_date)
        self.workers.append(worker)

        def on_success(action, data):
            print(f"Fetched by State Manager: {action}")
            self.scanned_meal_count = data
            if worker in self.workers: self.workers.remove(worker)
            self.scanned_meal_count_updated.emit(self.scanned_meal_count)

        def on_failure(action, error):
            print(f"Error on {action}: {error}")
            if worker in self.workers: self.workers.remove(worker)

        worker.bind_and_start(on_success, on_failure)