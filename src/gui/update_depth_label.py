import logging

logger = logging.getLogger(__name__)

def update_depth_label(app, value):
    logger.debug(f"Depth slider changed to {value}")
    app.depth_var = int(value)
    app.depth_label.setText(f"Depth: {int(value)}")
