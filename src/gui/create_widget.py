import tkinter as tk
from tkinter import ttk
import logging
from gui.update_depth_label import update_depth_label

# Logger setup
logger = logging.getLogger(__name__)

def create_widgets(app):
    # Color selection screen
    logger.debug("Creating color selection widgets")
    app.color_frame = tk.Frame(app.root, bg=app.bg_color)
    header = tk.Label(
        app.color_frame,
        text="ChessPilot",
        font=('Segoe UI', 18, 'bold'),
        bg=app.bg_color,
        fg=app.accent_color
    )
    header.pack(pady=(20, 10))

    color_panel = tk.Frame(app.color_frame, bg=app.frame_color, padx=20, pady=15)
    tk.Label(
        color_panel,
        text="Select Your Color:",
        font=('Segoe UI', 11),
        bg=app.frame_color,
        fg=app.text_color
    ).pack(pady=5)

    btn_frame = tk.Frame(color_panel, bg=app.frame_color)
    app.btn_white = app.create_color_button(btn_frame, "White", "w")
    app.btn_black = app.create_color_button(btn_frame, "Black", "b")
    btn_frame.pack(pady=5)

    # Depth and delay settings
    depth_panel = tk.Frame(color_panel, bg=app.frame_color)
    tk.Label(
        depth_panel,
        text="LC0 Nodes:",
        font=('Segoe UI', 10),
        bg=app.frame_color,
        fg=app.text_color
    ).pack(anchor='w')

    # Create, pack slider, then label
    app.depth_slider = ttk.Scale(
        depth_panel,
        from_=500,
        to=2000,
        variable=app.depth_var,
        style="TScale",
        command=lambda val: update_depth_label(app, val)
    )
    app.depth_slider.pack(fill='x', pady=5)

    app.depth_label = tk.Label(
        depth_panel,
        text=f"Depth: {app.depth_var.get()}",
        font=('Segoe UI', 9),
        bg=app.frame_color,
        fg=app.text_color
    )
    app.depth_label.pack(pady=(0, 10))

    tk.Label(
        depth_panel,
        text="Auto Move Screenshot Delay (sec):",
        font=('Segoe UI', 10),
        bg=app.frame_color,
        fg=app.text_color
    ).pack(anchor='w')

    app.delay_spinbox = ttk.Spinbox(
        depth_panel,
        from_=0.0,
        to=1.0,
        increment=0.1,
        textvariable=app.screenshot_delay_var,
        format="%.1f",
        width=5,
        state="readonly",
        justify="center"
    )
    app.style.configure(
        "TSpinbox",
        fieldbackground="#F3F1F1",
        background=app.frame_color,
        foreground="#000000"
    )
    app.delay_spinbox.pack(anchor='w')

    depth_panel.pack(fill='x', pady=10)
    color_panel.pack(padx=30, pady=10, fill='x')
    app.color_frame.pack(expand=True, fill=tk.BOTH)

    # Main control screen (after color is chosen)
    logger.debug("Creating main control widgets")
    app.main_frame = tk.Frame(app.root, bg=app.bg_color)
    control_panel = tk.Frame(app.main_frame, bg=app.frame_color, padx=20, pady=15)

    app.btn_play = app.create_action_button(
        control_panel,
        "Play Next Move",
        app.process_move_thread
    )
    app.btn_play.pack(fill='x', pady=5)

    app.castling_frame = tk.Frame(control_panel, bg=app.frame_color)
    app.kingside_var = tk.BooleanVar()
    app.queenside_var = tk.BooleanVar()
    app.create_castling_checkboxes()
    app.castling_frame.pack(pady=10)

    app.auto_mode_check = ttk.Checkbutton(
        control_panel,
        text="Auto Next Moves",
        variable=app.auto_mode_var,
        command=app.toggle_auto_mode,
        style="Castling.TCheckbutton"
    )
    app.auto_mode_check.pack(pady=5, anchor="center")

    app.status_label = tk.Label(
        control_panel,
        text="",
        font=('Segoe UI', 10),
        bg=app.frame_color,
        fg=app.text_color,
        wraplength=300
    )
    app.status_label.pack(fill='x', pady=10)

    control_panel.pack(padx=30, pady=20, fill='both', expand=True)
    app.main_frame.pack(expand=True, fill=tk.BOTH)

    # Disable "Play Next Move" until a color is chosen
    app.btn_play.config(state=tk.DISABLED)
    logger.debug("Widgets created successfully")
