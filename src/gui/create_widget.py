from PyQt6.QtWidgets import (QWidget, QLabel, QSlider, QDoubleSpinBox,
                             QRadioButton, QButtonGroup, QVBoxLayout, QHBoxLayout, QCheckBox)
from PyQt6.QtCore import Qt
import logging
from gui.update_depth_label import update_depth_label
from gui.shortcuts_dialog import show_shortcuts_dialog

logger = logging.getLogger(__name__)

def create_widgets(app):
    central_widget = QWidget()
    app.setCentralWidget(central_widget)
    main_layout = QVBoxLayout(central_widget)
    main_layout.setContentsMargins(0, 0, 0, 0)

    app.color_frame = QWidget()
    app.color_frame.setStyleSheet(f"background-color: {app.bg_color};")
    color_layout = QVBoxLayout(app.color_frame)
    color_layout.setContentsMargins(15, 15, 15, 15)

    header_container = QWidget()
    header_layout = QHBoxLayout(header_container)
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_layout.setSpacing(10)
    
    header = QLabel("ChessPilot")
    header.setStyleSheet(f"""
        color: {app.accent_color};
        font-family: 'Segoe UI';
        font-size: 20pt;
        font-weight: bold;
    """)
    header.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    # Add shortcuts button
    app.shortcuts_btn = app.create_shortcuts_button(header_container, lambda: show_shortcuts_dialog(app))
    
    header_layout.addStretch()
    header_layout.addWidget(header)
    header_layout.addStretch()
    header_layout.addWidget(app.shortcuts_btn)
    
    color_layout.addWidget(header_container)
    color_layout.addSpacing(15)

    color_panel = QWidget()
    color_panel.setStyleSheet(f"background-color: {app.frame_color}; border-radius: 8px;")
    color_panel_layout = QVBoxLayout(color_panel)
    color_panel_layout.setContentsMargins(20, 20, 20, 20)

    color_label = QLabel("Select Your Color:")
    color_label.setStyleSheet(f"""
        color: {app.text_color};
        font-family: 'Segoe UI';
        font-size: 12pt;
        font-weight: 500;
    """)
    color_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    color_panel_layout.addWidget(color_label)
    color_panel_layout.addSpacing(10)

    btn_frame = QWidget()
    btn_layout = QHBoxLayout(btn_frame)
    btn_layout.setContentsMargins(0, 0, 0, 0)
    btn_layout.setSpacing(10)
    app.btn_white = app.create_color_button(btn_frame, "White", "w")
    app.btn_black = app.create_color_button(btn_frame, "Black", "b")
    btn_layout.addWidget(app.btn_white)
    btn_layout.addWidget(app.btn_black)
    color_panel_layout.addWidget(btn_frame)
    color_panel_layout.addSpacing(15)

    depth_panel = QWidget()
    depth_panel.setStyleSheet(f"background-color: {app.frame_color};")
    depth_layout = QVBoxLayout(depth_panel)
    depth_layout.setContentsMargins(0, 0, 0, 0)

    depth_title = QLabel("Stockfish Depth:")
    depth_title.setStyleSheet(f"""
        color: {app.text_color};
        font-family: 'Segoe UI';
        font-size: 11pt;
        font-weight: 500;
    """)
    depth_layout.addWidget(depth_title)
    depth_layout.addSpacing(5)

    app.depth_slider = QSlider(Qt.Orientation.Horizontal)
    app.depth_slider.setMinimum(10)
    app.depth_slider.setMaximum(30)
    app.depth_slider.setValue(app.depth_var)
    app.depth_slider.setStyleSheet(f"""
        QSlider::groove:horizontal {{
            background: #4a4a4a;
            height: 6px;
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {app.accent_color};
            width: 20px;
            height: 20px;
            margin: -7px 0;
            border-radius: 10px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {app.hover_color};
        }}
    """)
    depth_layout.addWidget(app.depth_slider)
    depth_layout.addSpacing(8)

    app.depth_label = QLabel(f"Depth: {app.depth_var}")
    app.depth_label.setStyleSheet(f"""
        color: {app.text_color};
        font-family: 'Segoe UI';
        font-size: 10pt;
    """)
    app.depth_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    depth_layout.addWidget(app.depth_label)
    depth_layout.addSpacing(15)

    delay_label = QLabel("Screenshot Delay (seconds):")
    delay_label.setStyleSheet(f"""
        color: {app.text_color};
        font-family: 'Segoe UI';
        font-size: 11pt;
        font-weight: 500;
    """)
    depth_layout.addWidget(delay_label)
    depth_layout.addSpacing(5)

    app.delay_spinbox = QDoubleSpinBox()
    app.delay_spinbox.setMinimum(0.0)
    app.delay_spinbox.setMaximum(1)
    app.delay_spinbox.setSingleStep(0.1)
    app.delay_spinbox.setValue(app.screenshot_delay_var)
    app.delay_spinbox.setDecimals(1)
    app.delay_spinbox.setAlignment(Qt.AlignmentFlag.AlignCenter)
    app.delay_spinbox.setFixedWidth(100)
    app.delay_spinbox.setFixedHeight(32)
    app.delay_spinbox.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.UpDownArrows)
    app.delay_spinbox.setStyleSheet(f"""
        QDoubleSpinBox {{
            background-color: #4a4a4a;
            color: {app.text_color};
            border: 1px solid #5a5a5a;
            border-radius: 4px;
            padding: 5px 20px 5px 5px;
            font-family: 'Segoe UI';
            font-size: 10pt;
        }}
        QDoubleSpinBox::up-button {{
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 18px;
            height: 15px;
            background-color: {app.accent_color};
            border-top-right-radius: 3px;
            border-left: 1px solid #5a5a5a;
        }}
        QDoubleSpinBox::down-button {{
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            width: 18px;
            height: 15px;
            background-color: {app.accent_color};
            border-bottom-right-radius: 3px;
            border-left: 1px solid #5a5a5a;
        }}
        QDoubleSpinBox::up-button:hover {{
            background-color: {app.hover_color};
        }}
        QDoubleSpinBox::down-button:hover {{
            background-color: {app.hover_color};
        }}
        QDoubleSpinBox::up-arrow {{
            image: none;
            width: 0px;
            height: 0px;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid {app.text_color};
            margin: 0px 5px;
        }}
        QDoubleSpinBox::down-arrow {{
            image: none;
            width: 0px;
            height: 0px;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {app.text_color};
            margin: 0px 5px;
        }}
    """)
    app.delay_spinbox.valueChanged.connect(lambda val: setattr(app, 'screenshot_delay_var', val))
    depth_layout.addWidget(app.delay_spinbox)
    depth_layout.addSpacing(15)

    mode_frame = QWidget()
    mode_frame.setStyleSheet(f"background-color: {app.frame_color};")
    mode_layout = QVBoxLayout(mode_frame)
    mode_layout.setContentsMargins(0, 0, 0, 0)

    mode_title = QLabel("Move Mode:")
    mode_title.setStyleSheet(f"""
        color: {app.text_color};
        font-family: 'Segoe UI';
        font-size: 11pt;
        font-weight: 500;
    """)
    mode_layout.addWidget(mode_title)
    mode_layout.addSpacing(5)

    radio_frame = QWidget()
    radio_layout = QHBoxLayout(radio_frame)
    radio_layout.setContentsMargins(0, 0, 0, 0)
    radio_layout.setSpacing(15)

    app.move_mode_group = QButtonGroup()

    drag_radio = QRadioButton("Drag Mode")
    drag_radio.setChecked(True)
    drag_radio.setStyleSheet(f"""
        QRadioButton {{
            background-color: #4a4a4a;
            color: {app.text_color};
            font-family: 'Segoe UI';
            font-size: 10pt;
            padding: 8px 12px;
            border-radius: 4px;
        }}
        QRadioButton:hover {{
            background-color: #525252;
        }}
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
        }}
    """)
    drag_radio.toggled.connect(lambda checked: app.set_move_mode("drag") if checked else None)
    app.move_mode_group.addButton(drag_radio)
    radio_layout.addWidget(drag_radio)

    click_radio = QRadioButton("Click Mode")
    click_radio.setStyleSheet(f"""
        QRadioButton {{
            background-color: #4a4a4a;
            color: {app.text_color};
            font-family: 'Segoe UI';
            font-size: 10pt;
            padding: 8px 12px;
            border-radius: 4px;
        }}
        QRadioButton:hover {{
            background-color: #525252;
        }}
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
        }}
    """)
    click_radio.toggled.connect(lambda checked: app.set_move_mode("click") if checked else None)
    app.move_mode_group.addButton(click_radio)
    radio_layout.addWidget(click_radio)

    mode_layout.addWidget(radio_frame)
    depth_layout.addWidget(mode_frame)

    color_panel_layout.addWidget(depth_panel)

    color_layout.addWidget(color_panel)
    color_layout.addStretch()

    app.main_frame = QWidget()
    app.main_frame.setStyleSheet(f"background-color: {app.bg_color};")
    main_frame_layout = QVBoxLayout(app.main_frame)
    main_frame_layout.setContentsMargins(15, 15, 15, 15)

    control_panel = QWidget()
    control_panel.setStyleSheet(f"background-color: {app.frame_color}; border-radius: 8px;")
    control_layout = QVBoxLayout(control_panel)
    control_layout.setContentsMargins(20, 20, 20, 20)

    app.btn_play = app.create_action_button(control_panel, "Play Next Move", app.process_move_thread)
    control_layout.addWidget(app.btn_play)
    control_layout.addSpacing(10)


    app.castling_frame = QWidget()
    app.castling_frame.setStyleSheet(f"background-color: {app.frame_color};")
    castling_layout = QVBoxLayout(app.castling_frame)
    castling_layout.setContentsMargins(0, 0, 0, 0)
    castling_layout.setSpacing(8)
    
    castling_title = QLabel("Castling Rights:")
    castling_title.setStyleSheet(f"""
        color: {app.text_color};
        font-family: 'Segoe UI';
        font-size: 11pt;
        font-weight: 500;
    """)
    castling_layout.addWidget(castling_title)
    
    app.create_castling_checkboxes()
    castling_layout.addWidget(app.kingside_check)
    castling_layout.addWidget(app.queenside_check)
    control_layout.addWidget(app.castling_frame)
    control_layout.addSpacing(10)

    app.auto_mode_check = QCheckBox("Auto Next Moves")
    app.auto_mode_check.setStyleSheet(f"""
        QCheckBox {{
            background-color: #4a4a4a;
            color: {app.text_color};
            font-family: 'Segoe UI';
            font-size: 11pt;
            font-weight: 500;
            padding: 10px;
            border-radius: 4px;
        }}
        QCheckBox:hover {{
            background-color: #525252;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
        }}
    """)
    app.auto_mode_check.stateChanged.connect(lambda state: (setattr(app, 'auto_mode_var', state == Qt.CheckState.Checked.value), app.toggle_auto_mode()))
    control_layout.addWidget(app.auto_mode_check, alignment=Qt.AlignmentFlag.AlignCenter)
    control_layout.addSpacing(10)

    app.status_label = QLabel("")
    app.status_label.setStyleSheet(f"""
        color: {app.text_color};
        font-family: 'Segoe UI';
        font-size: 10pt;
        background-color: #4a4a4a;
        padding: 10px;
        border-radius: 4px;
    """)
    app.status_label.setWordWrap(True)
    app.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    control_layout.addWidget(app.status_label)

    main_frame_layout.addWidget(control_panel)
    main_frame_layout.addStretch()

    main_layout.addWidget(app.color_frame)
    main_layout.addWidget(app.main_frame)

    app.color_frame.show()
    app.main_frame.hide()
    
    control_layout.addSpacing(10)
    
    # Add depth slider to main frame
    depth_panel_main = QWidget()
    depth_panel_main.setStyleSheet(f"background-color: {app.frame_color};")
    depth_layout_main = QVBoxLayout(depth_panel_main)
    depth_layout_main.setContentsMargins(0, 0, 0, 0)

    depth_title_main = QLabel("Stockfish Depth:")
    depth_title_main.setStyleSheet(f"""
        color: {app.text_color};
        font-family: 'Segoe UI';
        font-size: 11pt;
        font-weight: 500;
    """)
    depth_layout_main.addWidget(depth_title_main)
    depth_layout_main.addSpacing(5)

    app.depth_slider_main = QSlider(Qt.Orientation.Horizontal)
    app.depth_slider_main.setMinimum(10)
    app.depth_slider_main.setMaximum(30)
    app.depth_slider_main.setValue(app.depth_var)
    app.depth_slider_main.setStyleSheet(f"""
        QSlider::groove:horizontal {{
            background: #4a4a4a;
            height: 6px;
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {app.accent_color};
            width: 20px;
            height: 20px;
            margin: -7px 0;
            border-radius: 10px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {app.hover_color};
        }}
    """)
    depth_layout_main.addWidget(app.depth_slider_main)
    depth_layout_main.addSpacing(8)

    app.depth_label_main = QLabel(f"Depth: {app.depth_var}")
    app.depth_label_main.setStyleSheet(f"""
        color: {app.text_color};
        font-family: 'Segoe UI';
        font-size: 10pt;
    """)
    app.depth_label_main.setAlignment(Qt.AlignmentFlag.AlignCenter)
    depth_layout_main.addWidget(app.depth_label_main)

    control_layout.addWidget(depth_panel_main)
    control_layout.addSpacing(10)

    # Synchronize both depth sliders
    def sync_depth_sliders(value):
        # Update both sliders and labels
        app.depth_slider.blockSignals(True)
        app.depth_slider_main.blockSignals(True)
        app.depth_slider.setValue(value)
        app.depth_slider_main.setValue(value)
        app.depth_slider.blockSignals(False)
        app.depth_slider_main.blockSignals(False)
        # Update labels and depth_var
        update_depth_label(app, value)
        app.depth_label_main.setText(f"Depth: {value}")
    
    app.depth_slider.valueChanged.connect(sync_depth_sliders)
    app.depth_slider_main.valueChanged.connect(sync_depth_sliders)
    app.btn_play.setEnabled(False)
    logger.debug("Widgets created successfully")