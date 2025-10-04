from PyQt6.QtWidgets import (QWidget, QLabel, QSlider, QDoubleSpinBox,
                             QRadioButton, QButtonGroup, QVBoxLayout, QHBoxLayout, QCheckBox)
from PyQt6.QtCore import Qt
import logging
from gui.update_depth_label import update_depth_label

logger = logging.getLogger(__name__)

def create_widgets(app):
    central_widget = QWidget()
    app.setCentralWidget(central_widget)
    main_layout = QVBoxLayout(central_widget)
    main_layout.setContentsMargins(0, 0, 0, 0)

    app.color_frame = QWidget()
    app.color_frame.setStyleSheet(f"background-color: {app.bg_color};")
    color_layout = QVBoxLayout(app.color_frame)

    header = QLabel("ChessPilot")
    header.setStyleSheet(f"""
        color: {app.accent_color};
        font-family: 'Segoe UI';
        font-size: 18pt;
        font-weight: bold;
    """)
    header.setAlignment(Qt.AlignmentFlag.AlignCenter)
    color_layout.addWidget(header)
    color_layout.addSpacing(10)

    color_panel = QWidget()
    color_panel.setStyleSheet(f"background-color: {app.frame_color}; border-radius: 5px;")
    color_panel_layout = QVBoxLayout(color_panel)
    color_panel_layout.setContentsMargins(20, 15, 20, 15)

    color_label = QLabel("Select Your Color:")
    color_label.setStyleSheet(f"""
        color: {app.text_color};
        font-family: 'Segoe UI';
        font-size: 11pt;
    """)
    color_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    color_panel_layout.addWidget(color_label)
    color_panel_layout.addSpacing(5)

    btn_frame = QWidget()
    btn_layout = QHBoxLayout(btn_frame)
    btn_layout.setContentsMargins(0, 0, 0, 0)
    app.btn_white = app.create_color_button(btn_frame, "White", "w")
    app.btn_black = app.create_color_button(btn_frame, "Black", "b")
    btn_layout.addWidget(app.btn_white)
    btn_layout.addSpacing(5)
    btn_layout.addWidget(app.btn_black)
    btn_layout.addStretch()
    color_panel_layout.addWidget(btn_frame)
    color_panel_layout.addSpacing(5)

    depth_panel = QWidget()
    depth_panel.setStyleSheet(f"background-color: {app.frame_color};")
    depth_layout = QVBoxLayout(depth_panel)
    depth_layout.setContentsMargins(0, 0, 0, 0)

    depth_title = QLabel("Stockfish Depth:")
    depth_title.setStyleSheet(f"""
        color: {app.text_color};
        font-family: 'Segoe UI';
        font-size: 10pt;
    """)
    depth_layout.addWidget(depth_title)

    app.depth_slider = QSlider(Qt.Orientation.Horizontal)
    app.depth_slider.setMinimum(10)
    app.depth_slider.setMaximum(30)
    app.depth_slider.setValue(app.depth_var)
    app.depth_slider.setStyleSheet(f"""
        QSlider::groove:horizontal {{
            background: {app.frame_color};
            height: 8px;
            border-radius: 4px;
        }}
        QSlider::handle:horizontal {{
            background: {app.accent_color};
            width: 18px;
            margin: -5px 0;
            border-radius: 9px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {app.hover_color};
        }}
    """)
    app.depth_slider.valueChanged.connect(lambda val: update_depth_label(app, val))
    depth_layout.addWidget(app.depth_slider)
    depth_layout.addSpacing(5)

    app.depth_label = QLabel(f"Depth: {app.depth_var}")
    app.depth_label.setStyleSheet(f"""
        color: {app.text_color};
        font-family: 'Segoe UI';
        font-size: 9pt;
    """)
    depth_layout.addWidget(app.depth_label)
    depth_layout.addSpacing(10)

    delay_label = QLabel("Auto Move Screenshot Delay (sec):")
    delay_label.setStyleSheet(f"""
        color: {app.text_color};
        font-family: 'Segoe UI';
        font-size: 10pt;
    """)
    depth_layout.addWidget(delay_label)

    app.delay_spinbox = QDoubleSpinBox()
    app.delay_spinbox.setMinimum(0.0)
    app.delay_spinbox.setMaximum(1.0)
    app.delay_spinbox.setSingleStep(0.1)
    app.delay_spinbox.setValue(app.screenshot_delay_var)
    app.delay_spinbox.setDecimals(1)
    app.delay_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app.delay_spinbox.setStyleSheet(f"""
        QDoubleSpinBox {{
            background-color: #F3F1F1;
            color: #000000;
            border: 1px solid #cccccc;
            border-radius: 3px;
            padding: 3px;
            font-family: 'Segoe UI';
        }}
    """)
    app.delay_spinbox.valueChanged.connect(lambda val: setattr(app, 'screenshot_delay_var', val))
    depth_layout.addWidget(app.delay_spinbox)

    mode_frame = QWidget()
    mode_frame.setStyleSheet(f"background-color: {app.frame_color};")
    mode_layout = QVBoxLayout(mode_frame)
    mode_layout.setContentsMargins(0, 5, 0, 0)

    radio_frame = QWidget()
    radio_layout = QHBoxLayout(radio_frame)
    radio_layout.setContentsMargins(0, 0, 0, 0)

    app.move_mode_group = QButtonGroup()

    drag_radio = QRadioButton("Drag Mode")
    drag_radio.setChecked(True)
    drag_radio.setStyleSheet(f"""
        QRadioButton {{
            background-color: #373737;
            color: white;
            font-family: 'Segoe UI';
            font-size: 10pt;
            padding: 5px;
        }}
        QRadioButton:hover {{
            background-color: #333131;
        }}
    """)
    drag_radio.toggled.connect(lambda checked: app.set_move_mode("drag") if checked else None)
    app.move_mode_group.addButton(drag_radio)
    radio_layout.addWidget(drag_radio)
    radio_layout.addSpacing(10)

    click_radio = QRadioButton("Click Mode")
    click_radio.setStyleSheet(f"""
        QRadioButton {{
            background-color: #373737;
            color: white;
            font-family: 'Segoe UI';
            font-size: 10pt;
            padding: 5px;
        }}
        QRadioButton:hover {{
            background-color: #333131;
        }}
    """)
    click_radio.toggled.connect(lambda checked: app.set_move_mode("click") if checked else None)
    app.move_mode_group.addButton(click_radio)
    radio_layout.addWidget(click_radio)
    radio_layout.addStretch()

    mode_layout.addWidget(radio_frame)
    depth_layout.addWidget(mode_frame)

    color_panel_layout.addWidget(depth_panel)
    color_panel_layout.addSpacing(10)

    color_layout.addWidget(color_panel)
    color_layout.addSpacing(30)
    color_layout.addStretch()

    app.main_frame = QWidget()
    app.main_frame.setStyleSheet(f"background-color: {app.bg_color};")
    main_frame_layout = QVBoxLayout(app.main_frame)

    control_panel = QWidget()
    control_panel.setStyleSheet(f"background-color: {app.frame_color}; border-radius: 5px;")
    control_layout = QVBoxLayout(control_panel)
    control_layout.setContentsMargins(20, 15, 20, 15)

    app.btn_play = app.create_action_button(control_panel, "Play Next Move", app.process_move_thread)
    control_layout.addWidget(app.btn_play)
    control_layout.addSpacing(5)

    app.castling_frame = QWidget()
    app.castling_frame.setStyleSheet(f"background-color: {app.frame_color};")
    castling_layout = QVBoxLayout(app.castling_frame)
    castling_layout.setContentsMargins(0, 0, 0, 0)
    app.create_castling_checkboxes()
    castling_layout.addWidget(app.kingside_check)
    castling_layout.addWidget(app.queenside_check)
    control_layout.addWidget(app.castling_frame)
    control_layout.addSpacing(10)

    app.auto_mode_check = QCheckBox("Auto Next Moves")
    app.auto_mode_check.setStyleSheet(f"""
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
    app.auto_mode_check.stateChanged.connect(lambda state: (setattr(app, 'auto_mode_var', state == Qt.CheckState.Checked.value), app.toggle_auto_mode()))
    control_layout.addWidget(app.auto_mode_check, alignment=Qt.AlignmentFlag.AlignCenter)
    control_layout.addSpacing(5)

    app.status_label = QLabel("")
    app.status_label.setStyleSheet(f"""
        color: {app.text_color};
        font-family: 'Segoe UI';
        font-size: 10pt;
    """)
    app.status_label.setWordWrap(True)
    app.status_label.setMaximumWidth(300)
    control_layout.addWidget(app.status_label)
    control_layout.addSpacing(10)

    main_frame_layout.addWidget(control_panel)
    main_frame_layout.addSpacing(20)
    main_frame_layout.addStretch()

    main_layout.addWidget(app.color_frame)
    main_layout.addWidget(app.main_frame)

    app.color_frame.show()
    app.main_frame.hide()

    app.btn_play.setEnabled(False)
    logger.debug("Widgets created successfully")
