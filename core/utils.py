from typing import List
from datetime import datetime, timedelta, timezone
from PyQt6.QtCore import QRectF, QSize, Qt, pyqtProperty, QPropertyAnimation, QDate, pyqtSignal
from PyQt6.QtGui import QColor, QKeyEvent, QMovie, QPainter, QTextCharFormat
from PyQt6.QtWidgets import (
    QAbstractButton,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
    QCalendarWidget,
    QPushButton,
    QHBoxLayout
)

__all__ = ["POST", "GET", "WEEKDAYS", "WEEKDAYS_ABBR", "API_ENDPOINTS", "UtilityFunctions", "ToggleSwitch", "SingleLineEdit", "LoadingOverlay", "ClickableColorCalendar", "DaySelectionMapping", "ALLOWED_CONFIG_KEYS"]

POST = "POST"
GET = "GET"
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
WEEKDAYS_ABBR = (day[:3] for day in WEEKDAYS)

API_ENDPOINTS = {
    "fetch-physical-token-stats": "get-existing-token-stats",
    "fetch-available-token-list": "get-available-tokens",
    "fetch-active-trainee-list": "get-trainee-list",
    "fetch-current-settings": "get-settings",
    "fetch-total-meal-preferences-count": "get-total-meal-data",
    "fetch-scanned-meal-preferences-count": "get-scanned-meal-data",
    "configure-settings-key-value-pairs": "configure-settings",
    "generate-new-physical-qr-token": "generate-new-token",
    "assign-existing-token-to-trainee": "assign-token",
    "verify-qr-token-scanned-by-trainee": "verify-token",
    "change-course-interval-of-trainees": "change-course-interval",
    "configure-special-settings-for-trainees": "apply-special-config"
}

ALLOWED_CONFIG_KEYS = ("breakfast_time_slot", "lunch_time_slot", "dinner_time_slot", "only_veg_days")

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
    
    def generate_date_intervals(self, dates_arr: List[str]) -> List[str]:
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
        self.movie = QMovie("assets/loader3.gif")
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
        self.selected_dates: set[QDate] = set()
        layout = QVBoxLayout(self)
        
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self.handle_date_click)
        
        layout.addWidget(self.calendar)

    def handle_date_click(self, date: QDate):
        if date < QDate.currentDate():
            return

        # Create a blank text format container
        fmt = QTextCharFormat()
        
        if date in self.selected_dates:
            self.selected_dates.remove(date)
            # Setting background to transparent restores the default calendar style
            fmt.setBackground(QColor(Qt.GlobalColor.transparent))
            fmt.setForeground(QColor(Qt.GlobalColor.black)) # Reset text to black
        else:
            self.selected_dates.add(date)
            # Apply your custom highlight color theme
            fmt.setBackground(QColor("#6388a4")) # Modern blue accent
            fmt.setForeground(QColor(Qt.GlobalColor.white)) # Crisp white text digits
            
        # Apply the format to the specific grid cell row layout
        self.calendar.setDateTextFormat(date, fmt)
    
    def clear(self):
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