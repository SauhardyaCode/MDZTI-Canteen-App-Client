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