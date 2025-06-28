import tkinter as tk
import logging

# Logger setup
logger = logging.getLogger(__name__)

def handle_esc_key(app, event=None):
    """Return to color‐selection screen if ESC is pressed."""
    logger.info("ESC key pressed; returning to color selection")
    if app.main_frame.winfo_ismapped():
        app.main_frame.pack_forget()
        app.color_frame.pack(expand=True, fill=tk.BOTH)
        app.color_indicator = None
        app.btn_play.config(state=tk.DISABLED)
        app.update_status("")
        app.auto_mode_var.set(False)
        app.btn_play.config(state=tk.NORMAL)
        
def bind_shortcuts(app):
    """Bind keyboard shortcuts to various actions."""
    # Color selection shortcuts (always allowed)
    app.root.bind('<Key-w>', lambda e: app.set_color('w'))
    app.root.bind('<Key-b>', lambda e: app.set_color('b'))
    # Main control shortcuts (only if color_indicator is set)
    app.root.bind(
        '<Key-p>',
        lambda e: app.process_move_thread() if app.color_indicator else None
    )
    app.root.bind(
        '<Key-a>',
        lambda e: app.auto_mode_check.invoke() if app.color_indicator else None
    )
    app.root.bind(
        '<Key-k>',
        lambda e: app.kingside_var.set(not app.kingside_var.get()) if app.color_indicator else None)
    app.root.bind(
        '<Key-q>',
        lambda e: app.queenside_var.set(not app.queenside_var.get()) if app.color_indicator else None)

    # Screenshot delay adjustment with Up/Down arrows
    app.root.bind(
        '<Up>',
        lambda e: (
            app.screenshot_delay_var.set(
                round(min(1.0, app.screenshot_delay_var.get() + 0.1), 1)
            ),
        ) if app.color_indicator is None else None
    )
    
    app.root.bind(
        '<Down>',
        lambda e: (
            app.screenshot_delay_var.set(
                round(max(0.0, app.screenshot_delay_var.get() - 0.1), 1)
            ),
        ) if app.color_indicator is None else None
    )

    # Depth adjustment with Right/Left arrows
    app.root.bind(
        '<Right>',
        lambda e: (
            app.depth_var.set(min(30, app.depth_var.get() + 1)),
            app.update_status(f"Depth: {app.depth_var.get()}")
        ) if app.color_indicator is None else None
    )
    app.root.bind(
        '<Left>',
        lambda e: (
            app.depth_var.set(max(10, app.depth_var.get() - 1)),
            app.update_status(f"Depth: {app.depth_var.get()}")
        ) if app.color_indicator is None else None
    )
