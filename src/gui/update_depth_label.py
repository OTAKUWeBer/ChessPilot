import logging

# Logger setup
logger = logging.getLogger(__name__)

def update_depth_label(app, value):
    logger.debug(f"Depth slider changed to {value}")
    app.depth_label.config(text=f"Depth: {int(float(value))}")
    app.root.update_idletasks()