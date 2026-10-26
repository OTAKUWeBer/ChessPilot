"""
PyQt6 modal progress window for downloading Stockfish.
Provides thread-safe progress reporting and retry controls.
"""

import threading
import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal

from core.config import AppConfig

logger = logging.getLogger(__name__)

SILENT_MODE = False


class ProgressSignals(QObject):
    """Signals for thread-safe UI updates from worker threads."""
    progress_update = pyqtSignal(int)  # percentage
    label_update = pyqtSignal(str)
    sub_label_update = pyqtSignal(str)
    show_retry = pyqtSignal()
    close_window = pyqtSignal(int)  # delay in ms


class StockfishDownloaderApp(QWidget):
    """Modal progress window for downloading and installing Stockfish."""
    def __init__(self, workflow_factory=None):
        super().__init__()
        self.workflow_factory = workflow_factory
        self.setWindowTitle("Stockfish Downloader")
        self.setFixedSize(420, 180)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        
        if SILENT_MODE:
            self.hide()

        self.signals = ProgressSignals()
        self.signals.progress_update.connect(self._update_progress)
        self.signals.label_update.connect(self._update_label)
        self.signals.sub_label_update.connect(self._update_sub_label)
        self.signals.show_retry.connect(self._show_retry_button)
        self.signals.close_window.connect(self._close_after)

        self._setup_styles()
        self._create_widgets()

        threading.Thread(target=self._start_download_flow, daemon=True).start()

    def _setup_styles(self):
        bg = AppConfig.BG_COLOR
        frame = AppConfig.FRAME_COLOR
        accent = AppConfig.ACCENT_COLOR
        text = AppConfig.TEXT_COLOR
        hover = AppConfig.HOVER_COLOR

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
            }}
            QLabel {{
                color: {text};
                background-color: {bg};
            }}
            QProgressBar {{
                border: 1px solid {frame};
                background-color: {frame};
                text-align: center;
                color: {text};
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {accent};
                border-radius: 2px;
            }}
            QPushButton {{
                background-color: {accent};
                color: {text};
                border: none;
                border-radius: 3px;
                font-family: 'Segoe UI';
                font-size: 10pt;
                font-weight: bold;
                padding: 8px 15px;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
        """)

    def _create_widgets(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        self.label = QLabel("Preparing download...")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.pb = QProgressBar()
        self.pb.setMinimum(0)
        self.pb.setMaximum(100)
        self.pb.setValue(0)
        self.pb.setFixedHeight(25)
        layout.addWidget(self.pb)

        self.sub_label = QLabel("")
        self.sub_label.setWordWrap(True)
        layout.addWidget(self.sub_label)

        self.retry_button = QPushButton("Retry Download")
        self.retry_button.clicked.connect(self._retry_download)
        self.retry_button.hide()
        layout.addWidget(self.retry_button)

        self.setLayout(layout)

    def _update_label(self, text):
        self.label.setText(text)

    def _update_sub_label(self, text):
        self.sub_label.setText(text)

    def _update_progress(self, pct):
        self.pb.setValue(pct)

    def _show_retry_button(self):
        self.retry_button.show()

    def _close_after(self, ms):
        logger.debug("Window will close in %d ms", ms)
        if SILENT_MODE:
            QTimer.singleShot(100, self.close)
        else:
            QTimer.singleShot(ms, self.close)

    def _retry_download(self):
        self.retry_button.hide()
        self.pb.setValue(0)
        threading.Thread(target=self._start_download_flow, daemon=True).start()

    def _start_download_flow(self):
        if self.workflow_factory:
            workflow = self.workflow_factory(self.signals)
        else:
            from utils.downloader import DownloadWorkflow
            workflow = DownloadWorkflow(self.signals)
        workflow.execute()
