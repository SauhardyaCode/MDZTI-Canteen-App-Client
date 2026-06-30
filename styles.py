ROOT_STYLESHEET = """
    QWidget {
        background-color: white;
        color: black;
    }
"""

PANEL_BORDER_STYLESHEET = """
    .QFrame {
        border: 1px solid #4A8F67;
        padding: 0px;
    }
"""

TITLE_STYLESHEET = """
    QLabel {
        font-family: 'Consolas', 'Courier New', monospace;
        font-size: 30px;
        font-weight: 700;
        background-color: transparent;
        color: white;
    }
    .QFrame {
        background-color: #FF2C67;
    }
"""

SIDE_PANEL_STYLESHEET = """
    .QFrame {
        background-color: white;
    }
    QPushButton {
        padding: 10px;
        font-size: 16px;
        font-weight: 600;
        text-align: left;
        border-radius: 0;
        border: 1px solid gray;
        background-color: rgba(239, 104, 32, 0.4);
    }
    QPushButton:hover {
        background-color: rgba(239, 104, 32, 0.6);
    }
    QPushButton:pressed {
        background-color: rgba(239, 104, 32, 0.7);
    }
"""

GENERATE_PANEL_STYLESHEET = """
    QStackedWidget, QFrame {
        background-color: rgb(254, 246, 238);
    }
    QLabel {
        background-color: transparent;
    }
    QLabel#heading {
        color: #4D0000;
        font-size: 30px;
        font-weight: 700;
        text-decoration: underline;
    }
"""

GENERATE_PANEL_SUBFRAME_STYLESHEET = """
    .QLabel {
        font-size: 20px;
        font-weight: 500;
    }
    .QLineEdit {
        font-size: 20px;
        background-color: rgb(255, 248, 236);
    }
"""

ASSIGNMENT_PANEL_SUBFRAME_STYLESHEET = """
    .QLabel {
        font-size: 20px;
        font-weight: 500;
    }
    .SingleLineEdit, .QDateEdit, .QComboBox {
        font-size: 16px;
        background-color: rgb(255, 248, 236);
        padding: 5px 10px;
    }
"""

GENERATE_PANEL_INPUT_STYLESHEET = """
    .QFrame {
        background-color: rgb(230, 214, 182);
        padding: 10px 30px;
    }
    .Qlabel, .QLineEdit {
        margin: 0px 30px;
    }
"""

SPECIAL_PANEL_INPUT_STYLESHEET = """
    .QFrame {
        background-color: rgb(230, 214, 182);
        padding: 10px 30px;
    }
    .Qlabel, .QTimeEdit {
        padding: 5px 10px;
        font-size: 16px;
    }
    .QCheckBox {
        padding: 0px;
    }
"""

SELECTED_WINDOW_BUTTON_STYLESHEET = """
    QPushButton, QPushButton:hover, QPushButton:pressed {
        background-color: rgba(239, 104, 32, 0.9);
    }
"""

SUBMIT_BUTTON_STYLESHEET = """
    QPushButton {
        margin: 20px 0px;
        padding: 8px;
        border: 4px solid rgb(204, 64, 64);
        border-radius: 20px;
        background-color: rgb(204, 64, 64);
        color: white;
        font-family: "Source Sans", sans-serif;
        font-size: 18px;
    }
    QPushButton:hover {
        background-color: rgb(224, 84, 84);
        border: 4px solid rgb(224, 84, 84);
    }
    QPushButton:pressed {
        background-color: rgb(204, 64, 64);
        border: 4px solid rgb(204, 64, 64);
    }
"""

RESET_BUTTON_STYLESHEET = """
    QPushButton {
        margin: 20px 0px;
        padding: 8px;
        border: 4px solid rgb(171, 172, 152);
        border-radius: 20px;
        background-color: rgb(171, 172, 152);
        color: white;
        font-family: "Source Sans", sans-serif;
        font-size: 18px;
    }
    QPushButton:hover {
        background-color: rgb(191, 192, 172);
        border: 4px solid rgb(191, 192, 172);
    }
    QPushButton:pressed {
        background-color: rgb(171, 172, 152);
        border: 4px solid rgb(171, 172, 152);
    }
"""

ADD_BUTTON_STYLESHEET = """
    QPushButton {
        margin: 0px 20px;
        padding: 5px;
        border: 1px solid rgb(246, 36, 64);
        background-color: rgb(255, 242, 219);
        font-family: "Source Sans", sans-serif;
        font-size: 12px;
    }
    QPushButton:hover {
        background-color: rgb(255, 229, 191);
    }
    QPushButton:pressed {
        background-color: rgb(255, 209, 171);
    }
"""

INFO_FRAME_STYLESHEET = """
    .QLabel {
        font-size: 16px;
    }
    #heading {
        font-size: 23px;
        font-weight: 500;
        text-decoration: none;
    }
"""

SUB_HEADING_STYLESHEET = """
    QLabel {
        margin: 50px 0px;
        color: #BA5A5A;
        font-size: 25px;
        font-weight: 500;
        text-decoration: underline;
    }
"""

DAY_FRAME_STYLESHEET = """
    .QFrame{
        margin: 0px;
        padding: 0px;
    }
    .QLabel, .QPushButton {
        font-size: 12px;
    }
"""

DAY_SUB_FRAME_STYLESHEET = """
    .QFrame {
        margin: 0px;
        padding: 0px;
        background-color: #ffffff;
    }
"""

LOGS_FRAME_STYLESHEET = """
    .QFrame, .QLabel {
        background-color: #E6F2DD;
    }
"""

STATUS_FRAME_STYLESHEET = """
    .QFrame, .QLabel {
        background-color: rgb(235, 244, 221);
    }
"""

LOGS_SUB_FRAME_STYLESHEET = """
    .QLabel {
        font-size: 12px;
        font-style: italic;
    }
"""

STATUS_SUB_FRAME_STYLESHEET = """
    .QFrame {
        margin: 0px 20px;
    }

    .QLabel {
        font-size: 16px;
    }
"""

SMALL_HEADING_STYLESHEET = """
    QLabel {
        margin: 0px;
        color: #7F2020;
        font-size: 12px;;
        font-weight: 600;
    }
"""

SUCCESS_LABEL_STYLESHEET = """
    .QLabel {
        font-family: monospace;
        font-size: 60px;
        font-weight: bold;
        letter-spacing: 5px;
        color: #033971;
        text-decoration: underline;
    }
"""

FAILURE_LABEL_STYLESHEET = """
    .QLabel {
        font-family: monospace;
        font-size: 60px;
        font-weight: bold;
        letter-spacing: 5px;
        color: #FF0000;
        text-decoration: underline;
    }
"""

SUCCESS_STYLESHEET = """
    QLabel {
        font-size: 35px;
    }
"""

SUCCESS_VEG_STYLESHEET = """
    QFrame {
        background-color: #BCD9A2;
    }
"""

SUCCESS_NON_VEG_STYLESHEET = """
    QFrame {
        background-color: #FAAA8C;
    }
"""

FAILURE_STYLESHEET = """
    QFrame {
        background-color: #ECCFD1;
    }
"""

FAILURE_STATUS_LABEL_STYLESHEET = """
    .QLabel {
        font-family: comicsans;
        font-size: 40px;
        font-weight: bold;
        color: #033971;
    }
"""

MANUAL_ENTRY_STYLESHEET = """
    QFrame {
        background-color: rgb(254, 246, 238);
    }

    QLabel {
        background-color: transparent;
    }
    
    QLabel#heading {
        color: #4D0000;
        font-size: 30px;
        font-weight: 700;
        text-decoration: underline;
    }
"""

SCAN_ENTRY_STYLESHEET = """
    QFrame {
        background-color: rgb(254, 246, 238);
    }

    QLabel {
        background-color: transparent;
    }
    
    QLabel#heading {
        color: #4D0000;
        font-size: 30px;
        font-weight: 600;
    }
"""

HEADING_STYLESHEET = """
    QLabel {
        color: #4D0000;
        font-size: 30px;
        font-weight: 700;
        text-decoration: underline;
    }
"""

SCANNER_CARD_STYLESHEET = """
    QFrame {
        background-color: #ffffff;
        border-radius: 16px;
        border: 1px solid #e0e0e0;
    }
    QLabel {
        border: none; 
    }
"""

LOGIN_SCREEN_OVERLAY_STYLESHEET = """
    QFrame#DarkOverlay {
        background-color: rgba(0, 0, 0, 180); /* Translucent shield */
    }
    QLabel {
        background-color: transparent;
        color: white;
    }
"""

ROLE_TITLE_STYLESHEET = """
    .QLabel {
        font-family: monospace;
        font-size: 30px;
        font-weight: 500;
        letter-spacing: 3px;
        color: #ffffff;
        text-decoration: underline;
    }
"""

ROLE_BUTTON_STYLESHEET = """
    QPushButton {
        padding: 12px 8px;
        border: 4px solid rgb(204, 64, 64);
        border-radius: 24px;
        background-color: rgb(204, 64, 64);
        color: white;
        font-family: "Source Sans", sans-serif;
        font-size: 18px;
    }
    QPushButton:hover {
        background-color: rgb(224, 84, 84);
        border: 4px solid rgb(224, 84, 84);
    }
    QPushButton:pressed {
        background-color: rgb(204, 64, 64);
        border: 4px solid rgb(204, 64, 64);
    }
"""

LOGIN_CARD_STYLESHEET = """
    .QFrame {
        background-color: rgba(255, 255, 255, 0.8);
        border-radius: 25px;
        padding: 25px;
    }
    QLabel {
        color: #222222; /* Dark typography texts */
        font-family: 'Segoe UI', Arial;
        background-color: transparent;
    }
    QLabel#heading {
        color: rgb(184, 34, 34);
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 50px;
    }
    QLineEdit {
        background-color: #f0f2f5;
        color: #111111;
        border: 1px solid #cccccc;
        border-radius: 6px;
        padding: 10px;
        font-size: 14px;
        margin-top: 10px;
        margin-bottom: 30px;
    }
    QLineEdit:focus {
        border: 1px solid #ff5722;
        background-color: #ffffff;
    }
"""

LOGIN_BUTTON_STYLESHEET = """
    QPushButton {
        padding: 8px;
        border: 4px solid rgb(204, 64, 64);
        border-radius: 20px;
        background-color: rgb(204, 64, 64);
        color: white;
        font-family: "Source Sans", sans-serif;
        font-size: 16px;
    }
    QPushButton:hover {
        background-color: rgb(224, 84, 84);
        border: 4px solid rgb(224, 84, 84);
    }
    QPushButton:pressed {
        background-color: rgb(204, 64, 64);
        border: 4px solid rgb(204, 64, 64);
    }
"""

SMALL_BUTTON_STYLESHEET = """
    QPushButton {
        background-color: transparent;
        font-size: 12px;
        color: rgb(41, 54, 129);
        text-decoration: underline;
        letter-spacing: 1px;
    }
    QPushButton:hover {
        font-weight: bold;
    }
    QPushButton:pressed {
        color: rgb(66, 116, 217)
    }
"""

SIGNUP_CARD_STYLESHEET = """
    .QFrame {
        background-color: rgba(255, 255, 255, 0.8);
        border-radius: 25px;
        padding: 25px;
    }
    QLabel {
        color: #222222; /* Dark typography texts */
        font-family: 'Segoe UI', Arial;
        background-color: transparent;
    }
    QLabel#heading {
        color: rgb(184, 34, 34);
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    QLineEdit {
        background-color: #f0f2f5;
        color: #111111;
        border: 1px solid #cccccc;
        border-radius: 6px;
        padding: 10px;
        font-size: 14px;
        margin-top: 10px;
        margin-bottom: 30px;
    }
    QLineEdit:focus {
        border: 1px solid #ff5722;
        background-color: #ffffff;
    }
"""