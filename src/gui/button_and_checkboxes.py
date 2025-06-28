import tkinter as tk
from tkinter import ttk
import logging

# Logger setup
logger = logging.getLogger(__name__)

def color_button(app, parent, text, color):
    btn = tk.Button(
        parent,
        text=text,
        font=('Segoe UI', 10, 'bold'),
        width=9,
        bd=0,
        padx=15,
        pady=8,
        bg=app.accent_color,
        fg=app.text_color,
        activebackground=app.hover_color,
        activeforeground=app.text_color,
        command=lambda: app.set_color(color)
    )
    btn.pack(side=tk.LEFT, padx=5)
    return btn

def action_button(app, parent, text, command):
    btn = tk.Button(
        parent,
        text=text,
        font=('Segoe UI', 11, 'bold'),
        bg=app.accent_color,
        fg=app.text_color,
        activebackground=app.hover_color,
        activeforeground=app.text_color,
        bd=0,
        pady=10,
        command=command
    )
    btn.pack()
    return btn

def castling_checkboxes(app):
    logger.debug("Creating castling checkboxes")
    style = ttk.Style()
    style.configure(
        "Castling.TCheckbutton",
        background="#373737",
        foreground="white",
        font=("Segoe UI", 10)
    )
    style.map(
        "Castling.TCheckbutton",
        background=[('active', '#333131'), ('pressed', '#333131')],
        foreground=[('active', 'white'), ('pressed', 'white')]
    )
    ttk.Checkbutton(
        app.castling_frame,
        text="Kingside Castle",
        variable=app.kingside_var,
        style="Castling.TCheckbutton"
    ).grid(row=0, column=0, padx=10, sticky='w')
    ttk.Checkbutton(
        app.castling_frame,
        text="Queenside Castle",
        variable=app.queenside_var,
        style="Castling.TCheckbutton"
    ).grid(row=1, column=0, padx=10, sticky='w')