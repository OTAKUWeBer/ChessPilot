import numpy as np
import onnxruntime as ort
from PIL import Image
from utils.resource_path import resource_path
import sys
import os
import logging
from board_detection.fen_extractor import get_fen_from_position
from board_detection.model_classes import CHESSBOARD_CLASS_ID

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

_session = None
_input_name = None
_output_name = None
conf = 0.5  # Lowered from 0.7 to detect boards more reliably

def get_session():
    """Lazily load the ONNX model."""
    global _session, _input_name, _output_name
    if _session is None:
        model_path = resource_path("chess_detection.onnx")
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Missing chess_detection.onnx at {model_path}. "
                "See README for instructions: https://github.com/OTAKUWeBer/ChessPilot/blob/main/README.md"
            )
        _session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        _input_name = _session.get_inputs()[0].name
        _output_name = _session.get_outputs()[0].name
    return _session, _input_name, _output_name

def letterbox_resize(image, target_size):
    """
    Resizes the image to fit within the target_size, maintaining the aspect ratio.
    Adds padding only to one dimension (either top/bottom or left/right) to make the image square.
    """
    orig_w, orig_h = image.size
    scale = min(target_size / orig_w, target_size / orig_h)

    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)

    resized = image.resize((new_w, new_h), Image.LANCZOS)

    x_offset = (target_size - new_w) // 2
    y_offset = (target_size - new_h) // 2

    padded = Image.new("RGB", (target_size, target_size), (0, 0, 0))
    padded.paste(resized, (x_offset, y_offset))

    return padded, x_offset, y_offset, scale

def preprocess_image(image):
    """
    Prepares the image for model inference by resizing, normalizing, and formatting.
    """
    image, x_offset, y_offset, scale = letterbox_resize(image, 640)
    image = np.array(image).astype(np.float32) / 255.0  # Normalize
    image = image.transpose(2, 0, 1)  # HWC to CHW
    image = np.expand_dims(image, axis=0)  # Add batch dimension
    return image, x_offset, y_offset, scale

def scale_bbox(detection, x_offset, y_offset, scale):
    """
    Scales bounding box coordinates from padded/resized image to original image dimensions.
    """
    x, y, w, h = detection[:4]
    new_x = int((x - x_offset) / scale)
    new_y = int((y - y_offset) / scale)
    new_w = int((w - x) / scale)  # Width in original dimensions
    new_h = int((h - y) / scale)  # Height in original dimensions
    
    scaled = detection.copy()
    scaled[:4] = [new_x, new_y, new_w, new_h]
    return scaled

def predict(image):
    """
    Runs model inference and returns processed detections.
    """
    try:
        session, input_name, output_name = get_session()
    except Exception as e:
        logger.error(f"Cannot run prediction - ONNX model error: {e}")
        return []

    img_array, x_offset, y_offset, scale = preprocess_image(image)
    output = session.run([output_name], {input_name: img_array})[0]
    output = np.squeeze(output)
    
    detections = []
    for r in output:
        if r[4] > conf:
            scaled = scale_bbox(r, x_offset, y_offset, scale)
            detections.append(scaled.tolist())
    
    logger.debug(f"Detected {len(detections)} objects with confidence > {conf}")
    
    return detections

def _predict_region(image, region):
    boxes = predict(image.crop(region))
    for box in boxes:
        box[0] += region[0]
        box[1] += region[1]
    return boxes


def _refine_board(image, boxes):
    for board in boxes:
        if board[5] != CHESSBOARD_CLASS_ID:
            continue
        x, y, width, height = board[:4]
        padding = max(width, height) * 0.05
        region = (
            max(0, int(x - padding)), max(0, int(y - padding)),
            min(image.width, int(x + width + padding)),
            min(image.height, int(y + height + padding)),
        )
        if region[2] <= region[0] or region[3] <= region[1]:
            continue
        refined = _predict_region(image, region)
        if refined and get_fen_from_position('w', refined) is not None:
            return refined
    return None


def get_positions(image_input, refined_search=True):
    """
    Detect normally, then refine board crops and overlapping tiles if needed.
    """
    try:
        if isinstance(image_input, str):
            image = Image.open(image_input)
        else:
            image = image_input
    except Exception as e:
        logger.warning(f"Error loading image: {e}")
        return []

    predictions = predict(image)
    if not refined_search or (predictions and get_fen_from_position('w', predictions) is not None):
        return predictions or None

    logger.info("Normal board detection failed; trying refined search")
    refined = _refine_board(image, predictions)
    if refined:
        return refined

    # Square tiles keep small boards from disappearing during full-screen resizing.
    size = max(1, min(min(image.size), max(image.size) // 2))
    x_offsets = sorted({0, (image.width - size) // 2, image.width - size})
    y_offsets = sorted({0, (image.height - size) // 2, image.height - size})
    for top in y_offsets:
        for left in x_offsets:
            boxes = _predict_region(image, (left, top, left + size, top + size))
            refined = _refine_board(image, boxes)
            if refined:
                return refined
            if boxes and get_fen_from_position('w', boxes) is not None:
                return boxes

    logger.warning("Board detection failed after normal and refined search")
    return None

if __name__ == "__main__":
    image_path = "screenshot.png"
    print(get_positions(image_path))
