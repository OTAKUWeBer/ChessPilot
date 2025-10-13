from PyQt6.QtWidgets import QPushButton, QCheckBox
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

def color_button(app, parent, text, color):
    btn = QPushButton(text, parent)
    btn.setFixedWidth(120)
    btn.setFixedHeight(40)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {app.accent_color};
            color: {app.text_color};
            border: none;
            border-radius: 5px;
            font-family: 'Segoe UI';
            font-size: 11pt;
            font-weight: bold;
            padding: 10px 20px;
        }}
        QPushButton:hover {{
            background-color: {app.hover_color};
        }}
        QPushButton:pressed {{
            background-color: #3d8b40;
        }}
    """)
    btn.clicked.connect(lambda: app.set_color(color))
    return btn

def action_button(app, parent, text, command):
    btn = QPushButton(text, parent)
    btn.setFixedHeight(45)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {app.accent_color};
            color: {app.text_color};
            border: none;
            border-radius: 5px;
            font-family: 'Segoe UI';
            font-size: 12pt;
            font-weight: bold;
            padding: 12px;
        }}
        QPushButton:hover {{
            background-color: {app.hover_color};
        }}
        QPushButton:pressed {{
            background-color: #3d8b40;
        }}
        QPushButton:disabled {{
            background-color: #5a5a5a;
            color: #888888;
        }}
    """)
    btn.clicked.connect(command)
    return btn

def shortcuts_button(app, parent, command):
    """Create a small button to show keyboard shortcuts"""
    btn = QPushButton("❗ Keys", parent)
    btn.setFixedWidth(70)
    btn.setFixedHeight(30)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: #4a4a4a;
            color: {app.text_color};
            border: 1px solid #5a5a5a;
            border-radius: 4px;
            font-family: 'Segoe UI';
            font-size: 9pt;
            font-weight: normal;
            padding: 5px 10px;
        }}
        QPushButton:hover {{
            background-color: #525252;
            border-color: {app.accent_color};
        }}
        QPushButton:pressed {{
            background-color: #3a3a3a;
        }}
    """)
    btn.clicked.connect(command)
    return btn

def castling_checkboxes(app):
    logger.debug("Creating castling checkboxes")

    kingside_check = QCheckBox("Kingside Castle", app.castling_frame)
    kingside_check.setStyleSheet(f"""
        QCheckBox {{
            background-color: #4a4a4a;
            color: {app.text_color};
            font-family: 'Segoe UI';
            font-size: 10pt;
            padding: 8px;
            border-radius: 4px;
        }}
        QCheckBox:hover {{
            background-color: #525252;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
        }}
    """)
    kingside_check.stateChanged.connect(lambda state: setattr(app, 'kingside_var', state == Qt.CheckState.Checked.value))
    app.kingside_check = kingside_check
    app.kingside_var = False

    queenside_check = QCheckBox("Queenside Castle", app.castling_frame)
    queenside_check.setStyleSheet(f"""
        QCheckBox {{
            background-color: #4a4a4a;
            color: {app.text_color};
            font-family: 'Segoe UI';
            font-size: 10pt;
            padding: 8px;
            border-radius: 4px;
        }}
        QCheckBox:hover {{
            background-color: #525252;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
        }}
    """)
    queenside_check.stateChanged.connect(lambda state: setattr(app, 'queenside_var', state == Qt.CheckState.Checked.value))
    app.queenside_check = queenside_check
    app.queenside_var = False

def move_mode(app, parent, text, method):
    btn = QPushButton(text, parent)
    btn.setFixedWidth(100)
    btn.setFixedHeight(35)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {app.accent_color};
            color: {app.text_color};
            border: none;
            border-radius: 3px;
            font-family: 'Segoe UI';
            font-size: 10pt;
            font-weight: bold;
            padding: 8px 15px;
        }}
        QPushButton:hover {{
            background-color: {app.hover_color};
        }}
        QPushButton:pressed {{
            background-color: {app.hover_color};
        }}
    """)
    btn.clicked.connect(lambda: app.set_move_mode(method))
    return btn
