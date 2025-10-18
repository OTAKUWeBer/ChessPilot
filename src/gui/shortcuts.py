from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

def handle_esc_key(app):
    logger.info("ESC key pressed; returning to color selection")
    if app.main_frame.isVisible():
        app.main_frame.hide()
        app.color_frame.show()
        app.color_indicator = None
        app.btn_play.setEnabled(False)
        app.update_status("")
        app.auto_mode_var = False
        app.auto_mode_check.setChecked(False)
        app.btn_play.setEnabled(True)

def bind_shortcuts(app):
    QShortcut(QKeySequence(Qt.Key.Key_Escape), app).activated.connect(lambda: handle_esc_key(app) if app.color_indicator else None)

    QShortcut(QKeySequence(Qt.Key.Key_W), app).activated.connect(lambda: app.set_color('w'))
    QShortcut(QKeySequence(Qt.Key.Key_B), app).activated.connect(lambda: app.set_color('b'))

    QShortcut(QKeySequence(Qt.Key.Key_P), app).activated.connect(
        lambda: app.process_move_thread() if app.color_indicator else None
    )

    QShortcut(QKeySequence(Qt.Key.Key_A), app).activated.connect(
        lambda: app.auto_mode_check.toggle() if app.color_indicator else None
    )

    QShortcut(QKeySequence(Qt.Key.Key_K), app).activated.connect(
        lambda: app.kingside_check.toggle() if app.color_indicator else None
    )

    QShortcut(QKeySequence(Qt.Key.Key_Q), app).activated.connect(
        lambda: app.queenside_check.toggle() if app.color_indicator else None
    )

    QShortcut(QKeySequence(Qt.Key.Key_Up), app).activated.connect(
        lambda: adjust_delay_up(app) if app.color_indicator is None else None
    )

    QShortcut(QKeySequence(Qt.Key.Key_Down), app).activated.connect(
        lambda: adjust_delay_down(app) if app.color_indicator is None else None
    )

    QShortcut(QKeySequence(Qt.Key.Key_Right), app).activated.connect(
        lambda: adjust_depth_up(app)
    )

    QShortcut(QKeySequence(Qt.Key.Key_Left), app).activated.connect(
        lambda: adjust_depth_down(app)
    )

def adjust_delay_up(app):
    current = app.screenshot_delay_var
    new_val = round(min(1.0, current + 0.1), 1)
    app.screenshot_delay_var = new_val
    app.delay_spinbox.setValue(new_val)

def adjust_delay_down(app):
    current = app.screenshot_delay_var
    new_val = round(max(0.0, current - 0.1), 1)
    app.screenshot_delay_var = new_val
    app.delay_spinbox.setValue(new_val)

def adjust_depth_up(app):
    current = app.depth_var
    new_val = min(30, current + 1)
    app.depth_var = new_val
    app.depth_slider.setValue(new_val)

def adjust_depth_down(app):
    current = app.depth_var
    new_val = max(10, current - 1)
    app.depth_var = new_val
    app.depth_slider.setValue(new_val)
