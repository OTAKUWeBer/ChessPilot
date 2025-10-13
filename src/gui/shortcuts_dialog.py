from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

class ShortcutsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Get colors from parent app
        if parent:
            bg_color = parent.bg_color
            frame_color = parent.frame_color
            text_color = parent.text_color
            accent_color = parent.accent_color
            hover_color = parent.hover_color
        else:
            bg_color = "#2b2b2b"
            frame_color = "#3a3a3a"
            text_color = "#e0e0e0"
            accent_color = "#4caf50"
            hover_color = "#66bb6a"
        
        self.setStyleSheet(f"background-color: {bg_color};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("Keyboard Shortcuts")
        title.setStyleSheet(f"""
            color: {accent_color};
            font-family: 'Segoe UI';
            font-size: 16pt;
            font-weight: bold;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Shortcuts are mode-sensitive:")
        desc.setStyleSheet(f"""
            color: {text_color};
            font-family: 'Segoe UI';
            font-size: 10pt;
        """)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        # Selection Mode Section
        selection_label = QLabel("Selection Mode (Before choosing color):")
        selection_label.setStyleSheet(f"""
            color: {accent_color};
            font-family: 'Segoe UI';
            font-size: 11pt;
            font-weight: bold;
            margin-top: 10px;
        """)
        layout.addWidget(selection_label)
        
        selection_shortcuts = [
            ("W / B", "Choose White or Black"),
            ("← / →", "Decrease / Increase Stockfish depth"),
            ("↓ / ↑", "Decrease / Increase screenshot delay"),
            ("Esc", "Return to color selection screen"),
        ]
        
        selection_table = self._create_shortcuts_table(selection_shortcuts, frame_color, text_color)
        layout.addWidget(selection_table)
        
        # Play Mode Section
        play_label = QLabel("Play Mode (After choosing color):")
        play_label.setStyleSheet(f"""
            color: {accent_color};
            font-family: 'Segoe UI';
            font-size: 11pt;
            font-weight: bold;
            margin-top: 10px;
        """)
        layout.addWidget(play_label)
        
        play_shortcuts = [
            ("W / B", "Change Color White or Black"),
            ("P", "Execute the next move"),
            ("A", "Toggle Auto-Play mode"),
            ("K / Q", "Toggle Kingside / Queenside castling"),
            ("Esc", "Return to color selection screen"),
        ]
        
        play_table = self._create_shortcuts_table(play_shortcuts, frame_color, text_color)
        layout.addWidget(play_table)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(40)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent_color};
                color: {text_color};
                border: none;
                border-radius: 5px;
                font-family: 'Segoe UI';
                font-size: 11pt;
                font-weight: bold;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
    
    def _create_shortcuts_table(self, shortcuts, frame_color, text_color):
        table = QTableWidget()
        table.setRowCount(len(shortcuts))
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Shortcut", "Description"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setShowGrid(False)
        
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {frame_color};
                color: {text_color};
                border: none;
                border-radius: 5px;
                font-family: 'Segoe UI';
                font-size: 10pt;
            }}
            QHeaderView::section {{
                background-color: {frame_color};
                color: {text_color};
                font-weight: bold;
                border: none;
                padding: 8px;
                font-family: 'Segoe UI';
                font-size: 10pt;
            }}
            QTableWidget::item {{
                padding: 8px;
                border-bottom: 1px solid #4a4a4a;
            }}
        """)
        
        for row, (shortcut, description) in enumerate(shortcuts):
            shortcut_item = QTableWidgetItem(shortcut)
            shortcut_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 0, shortcut_item)
            
            desc_item = QTableWidgetItem(description)
            table.setItem(row, 1, desc_item)
        
        table.resizeColumnsToContents()
        table.setColumnWidth(0, 120)
        
        return table

def show_shortcuts_dialog(app):
    """Show the shortcuts dialog"""
    dialog = ShortcutsDialog(app)
    dialog.exec()
