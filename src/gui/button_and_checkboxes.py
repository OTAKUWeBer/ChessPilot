from PyQt6.QtWidgets import QPushButton, QCheckBox
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

def color_button(app, parent, text, color):
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
    btn.clicked.connect(lambda: app.set_color(color))
    return btn

def action_button(app, parent, text, command):
    btn = QPushButton(text, parent)
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {app.accent_color};
            color: {app.text_color};
            border: none;
            border-radius: 3px;
            font-family: 'Segoe UI';
            font-size: 11pt;
            font-weight: bold;
            padding: 10px;
        }}
        QPushButton:hover {{
            background-color: {app.hover_color};
        }}
        QPushButton:pressed {{
            background-color: {app.hover_color};
        }}
    """)
    btn.clicked.connect(command)
    return btn

def castling_checkboxes(app):
    logger.debug("Creating castling checkboxes")

    kingside_check = QCheckBox("Kingside Castle", app.castling_frame)
    kingside_check.setStyleSheet(f"""
        QCheckBox {{
            background-color: #373737;
            color: white;
            font-family: 'Segoe UI';
            font-size: 10pt;
            padding: 5px;
        }}
        QCheckBox:hover {{
            background-color: #333131;
        }}
    """)
    kingside_check.stateChanged.connect(lambda state: setattr(app, 'kingside_var', state == Qt.CheckState.Checked.value))
    app.kingside_check = kingside_check
    app.kingside_var = False

    queenside_check = QCheckBox("Queenside Castle", app.castling_frame)
    queenside_check.setStyleSheet(f"""
        QCheckBox {{
            background-color: #373737;
            color: white;
            font-family: 'Segoe UI';
            font-size: 10pt;
            padding: 5px;
        }}
        QCheckBox:hover {{
            background-color: #333131;
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
