import time
import threading
import logging

from board_detection import get_positions, get_fen_from_position
from executor.capture_screenshot_in_memory import capture_screenshot_in_memory
from executor.process_move import process_move
from executor.processing_sync import processing_event
from core.config import AppConfig

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

_consecutive_failures = 0
_max_failures = AppConfig.MAX_CONSECUTIVE_FAILURES


def _get_var_value(var):
    """
    Safely extract value from various variable types.
    
    Handles:
    - Callables (lambdas/functions) - call them
    - Objects with .get() method
    - Objects with .isChecked() method
    - Objects with .value attribute
    - Direct values
    """
    if callable(var):
        try:
            result = var()
            if callable(result) or hasattr(result, 'get') or hasattr(result, 'isChecked') or hasattr(result, 'value'):
                return _get_var_value(result)
            return result
        except Exception as e:
            logger.warning(f"Error calling variable function: {e}")
            return None
    
    if hasattr(var, 'isChecked'):
        try:
            return var.isChecked()
        except Exception as e:
            logger.warning(f"Error calling .isChecked(): {e}")
            return None
    
    if hasattr(var, 'get'):
        try:
            return var.get()
        except Exception as e:
            logger.warning(f"Error calling .get(): {e}")
            return None
    
    if hasattr(var, 'value'):
        try:
            return var.value
        except Exception as e:
            logger.warning(f"Error accessing .value: {e}")
            return None
    
    return var


def _set_var_value(var, value):
    """
    Safely set value for various variable types.
    
    Handles:
    - Objects with .set() method
    - Objects with .setChecked() method
    - Direct attribute assignment
    """
    if hasattr(var, 'set') and callable(var.set):
        try:
            var.set(value)
            return True
        except Exception as e:
            logger.warning(f"Error calling .set(): {e}")
    
    if hasattr(var, 'setChecked') and callable(var.setChecked):
        try:
            var.setChecked(value)
            return True
        except Exception as e:
            logger.warning(f"Error calling .setChecked(): {e}")
    
    if hasattr(var, 'value'):
        try:
            var.value = value
            return True
        except Exception as e:
            logger.warning(f"Error setting .value: {e}")
    
    logger.warning(f"Unable to set value on variable type: {type(var)}")
    return False


def process_move_thread(
    root,
    color_indicator,
    auto_mode_var,
    btn_play,
    move_mode,
    board_positions,
    update_status,
    kingside_var,
    queenside_var,
    update_last_fen_for_color,
    last_fen_by_color,
    screenshot_delay_var,
):
    """
    Starts a new daemon thread that will run process_move().
    """
    logger.info("Starting new thread to process move")
    threading.Thread(
        target=process_move,
        args=(
            root,
            color_indicator,
            auto_mode_var,
            btn_play,
            move_mode,
            board_positions,
            update_status,
            kingside_var,
            queenside_var,
            update_last_fen_for_color,
            last_fen_by_color,
            screenshot_delay_var,
        ),
        daemon=True,
    ).start()


def auto_move_loop(
    root,
    color_indicator,
    auto_mode_var,
    btn_play,
    move_mode,
    board_positions,
    last_fen_by_color,
    screenshot_delay_var,
    update_status_callback,
    kingside_var,
    queenside_var,
    update_last_fen_for_color
):
    """
    Main auto move loop - coordinates the overall flow.
    Complexity reduced by delegating to specialized functions.
    """
    global _consecutive_failures
    _consecutive_failures = 0
    
    logger.info("Auto move loop started")
    opp_color = 'b' if color_indicator == 'w' else 'w'
    logger.info(f"Player color: {color_indicator}, Opponent color: {opp_color}")

    # Initialize with seed position
    _perform_initial_seeding(root, auto_mode_var, color_indicator, last_fen_by_color)
    
    # Main processing loop
    _run_move_detection_loop(
        root, color_indicator, opp_color, auto_mode_var, btn_play, move_mode,
        board_positions, last_fen_by_color, screenshot_delay_var,
        update_status_callback, kingside_var, queenside_var, update_last_fen_for_color
    )
    
    logger.info("Exiting auto_move_loop")


def _perform_initial_seeding(root, auto_mode_var, color_indicator, last_fen_by_color):
    """
    Capture initial board position to seed the FEN tracking.
    """
    logger.debug("Seeding last_fen_by_color with initial board position")
    
    try:
        seed_img = capture_screenshot_in_memory(root, auto_mode_var)
        if not seed_img:
            logger.warning("Seed capture returned None; skipping initial seed")
            return
            
        boxes = get_positions(seed_img)
        if not boxes:
            logger.warning("No board detected in seed capture")
            return
            
        seed_fen = _extract_fen_from_boxes(color_indicator, boxes)
        if seed_fen:
            _update_seed_positions(seed_fen, last_fen_by_color)
            
    except Exception as ex:
        logger.error(f"Exception during initial seed: {ex}", exc_info=True)


def _extract_fen_from_boxes(color_indicator, boxes):
    """
    Extract FEN from detected board positions.
    """
    result = get_fen_from_position(color_indicator, boxes)
    if result is None:
        return None
        
    _, _, _, seed_fen = result
    parts = seed_fen.split()
    
    if len(parts) < 2:
        logger.warning("Seed FEN malformed; skipping initial seed")
        return None
        
    return parts[0]  # Return just the placement part


def _update_seed_positions(placement, last_fen_by_color):
    """
    Update both colors with the initial board placement.
    """
    last_fen_by_color['w'] = placement
    last_fen_by_color['b'] = placement
    logger.info(f"Seeded placement = {placement}")


def _run_move_detection_loop(
    root, color_indicator, opp_color, auto_mode_var, btn_play, move_mode,
    board_positions, last_fen_by_color, screenshot_delay_var,
    update_status_callback, kingside_var, queenside_var, update_last_fen_for_color
):
    """
    Main loop that continuously checks for moves and processes them.
    """
    global _consecutive_failures
    
    while _get_var_value(auto_mode_var):
        logger.debug("Loop tick")
        
        if _consecutive_failures >= _max_failures:
            logger.error(f"Exceeded maximum consecutive failures ({_max_failures}). Stopping auto mode.")
            _stop_auto_mode(root, auto_mode_var, btn_play, update_status_callback, 
                          f"Auto mode stopped: {_consecutive_failures} consecutive failures")
            break
        
        if not _should_continue_processing(board_positions):
            continue
            
        try:
            current_position = _capture_current_position(root, auto_mode_var, color_indicator)
            if not current_position:
                _consecutive_failures += 1
                logger.warning(f"Board capture failed (failure {_consecutive_failures}/{_max_failures})")
                
                if _consecutive_failures >= _max_failures:
                    logger.error("Max failures reached during board capture")
                    _stop_auto_mode(root, auto_mode_var, btn_play, update_status_callback,
                                  "Auto mode stopped: Board detection failed repeatedly")
                    break
                continue
                
            _consecutive_failures = 0
            
            placement, active = current_position
            
            if active == opp_color:
                _handle_opponent_turn(opp_color, placement, last_fen_by_color)
                continue
                
            if active == color_indicator:
                move_detected = _handle_player_turn(
                    opp_color, placement, last_fen_by_color
                )
                
                if move_detected:
                    _process_detected_move(
                        root, color_indicator, auto_mode_var, btn_play, move_mode, board_positions,
                        screenshot_delay_var, update_status_callback, kingside_var,
                        queenside_var, update_last_fen_for_color, last_fen_by_color
                    )
                    
        except Exception as e:
            _consecutive_failures += 1
            logger.error(f"Exception in auto_move_loop (failure {_consecutive_failures}/{_max_failures}): {e}", exc_info=True)
            
            if _consecutive_failures >= _max_failures:
                _stop_auto_mode(root, auto_mode_var, btn_play, update_status_callback,
                              f"Auto mode stopped: Error - {str(e)}")
                break
            else:
                # Continue loop but log the error
                logger.warning(f"Continuing after error ({_consecutive_failures}/{_max_failures} failures)")
                time.sleep(1.0)  # Wait a bit before retrying


def _stop_auto_mode(root, auto_mode_var, btn_play, update_status_callback, message):
    """
    Stop auto mode and update UI with error message.
    """
    logger.info(f"Stopping auto mode: {message}")
    
    try:
        # Disable auto mode variable
        if hasattr(root, "auto_mode_var"):
            root.auto_mode_var = False
        _set_var_value(auto_mode_var, False)
        
        # Uncheck the checkbox
        if hasattr(root, "auto_mode_check"):
            root.auto_mode_check.setChecked(False)
            logger.info("Unchecked auto_mode_check")
        
        # Re-enable the play button
        if hasattr(root, "btn_play"):
            root.btn_play.setEnabled(True)
            logger.info("Re-enabled play button")
        
        # Update status with error message
        if update_status_callback:
            root.after(0, lambda: update_status_callback(f"\n{message}"))
            
    except Exception as e:
        logger.error(f"Error stopping auto mode: {e}", exc_info=True)


def _should_continue_processing(board_positions):
    """
    Check if we should continue with the current loop iteration.
    """
    if processing_event.is_set():
        logger.debug("Currently processing a move; sleeping…")
        time.sleep(AppConfig.AUTO_MODE_POLL_INTERVAL)
        return False
        
    if not board_positions:
        logger.warning("Board positions not yet initialized; sleeping…")
        time.sleep(0.5)
        return False
        
    return True


def _capture_current_position(root, auto_mode_var, color_indicator):
    """
    Capture screenshot and extract current board position with retry logic.
    Returns tuple of (placement, active_color) or None if failed.
    """
    max_retries = AppConfig.MAX_FEN_EXTRACTION_RETRIES
    
    for attempt in range(max_retries):
        logger.debug(f"Capturing screenshot for auto-move (attempt {attempt + 1}/{max_retries})…")
        screenshot = capture_screenshot_in_memory(root, auto_mode_var)
        
        if not screenshot:
            logger.warning(f"Screenshot returned None on attempt {attempt + 1}; retrying…")
            time.sleep(AppConfig.FEN_RETRY_DELAY)
            continue
            
        boxes = get_positions(screenshot)
        if not boxes:
            logger.warning(f"Board detection failed on attempt {attempt + 1}; retrying…")
            time.sleep(AppConfig.FEN_RETRY_DELAY)
            continue
            
        result = _parse_fen_position(color_indicator, boxes)
        if result:
            return result
        
        # If parsing failed, retry
        if attempt < max_retries - 1:
            logger.warning(f"FEN parsing failed on attempt {attempt + 1}; retrying…")
            time.sleep(AppConfig.FEN_RETRY_DELAY)
    
    logger.error(f"Failed to capture position after {max_retries} attempts")
    return None

def _parse_fen_position(color_indicator, boxes):
    """
    Parse FEN from board positions and return placement and active color.
    """
    try:
        result = get_fen_from_position(color_indicator, boxes)
        if not result:
            logger.warning("get_fen_from_position returned None")
            return None
            
        _, _, _, current_fen = result
        logger.info(f"FEN extracted: {current_fen}")
        
        parts = current_fen.split()
        if len(parts) < 2:
            logger.warning("Malformed FEN (insufficient parts)")
            return None
            
        placement, active = parts[0], parts[1]
        logger.debug(f"Placement: {placement}, Active side: {active}")
        return placement, active
    except Exception as e:
        logger.error(f"Exception parsing FEN: {e}", exc_info=True)
        return None

def _handle_opponent_turn(opp_color, placement, last_fen_by_color):
    """
    Handle processing when it's the opponent's turn.
    """
    old = last_fen_by_color.get(opp_color)
    if old is None or placement != old:
        logger.info("Opponent moved; updating last_fen_by_color[opp_color].")
        last_fen_by_color[opp_color] = placement
    else:
        logger.debug("Opponent placement unchanged.")
    time.sleep(AppConfig.AUTO_MODE_POLL_INTERVAL)

def _handle_player_turn(opp_color, placement, last_fen_by_color):
    """
    Handle processing when it's the player's turn.
    Returns True if a genuine opponent move was detected.
    """
    if opp_color not in last_fen_by_color:
        logger.debug("Our turn detected but no previous opponent-FEN known; sleeping…")
        time.sleep(AppConfig.AUTO_MODE_POLL_INTERVAL)
        return False
        
    if placement == last_fen_by_color[opp_color]:
        logger.debug("It's our turn but opponent didn't move; sleeping…")
        time.sleep(AppConfig.AUTO_MODE_POLL_INTERVAL)
        return False
        
    # Genuine move detected
    last_fen_by_color[opp_color] = placement
    logger.info("Detected genuine opponent move; launching our move.")
    return True

def _process_detected_move(
    root, color_indicator, auto_mode_var, btn_play, move_mode, board_positions,
    screenshot_delay_var, update_status_callback, kingside_var,
    queenside_var, update_last_fen_for_color, last_fen_by_color
):
    """
    Process a detected opponent move by calculating and executing our response.
    """
    settle_delay = AppConfig.OPPONENT_MOVE_SETTLE_DELAY
    logger.info(f"Opponent move detected. Waiting {settle_delay}s for move to settle…")
    time.sleep(settle_delay)
    
    # Verify the position is stable by capturing again
    logger.debug("Verifying position stability after settle delay…")
    verification_position = _capture_current_position(root, auto_mode_var, color_indicator)
    
    if verification_position:
        placement, active = verification_position
        # Update with verified position
        if active == color_indicator:
            last_fen_by_color[color_indicator] = placement
            logger.info("Position verified and stable, proceeding with move calculation")
        else:
            logger.warning("Position changed during verification, opponent may still be moving")
            time.sleep(AppConfig.OPPONENT_MOVE_SETTLE_DELAY)
    
    delay = _get_var_value(screenshot_delay_var)
    logger.debug(f"Additional delay of {delay}s before calculating move…")
    time.sleep(delay)
    
    process_move_thread(
        root, color_indicator, auto_mode_var, btn_play, move_mode, board_positions,
        update_status_callback, kingside_var, queenside_var,
        update_last_fen_for_color, last_fen_by_color, screenshot_delay_var
    )
    
    logger.debug(f"Sleeping for {AppConfig.MIN_MOVE_INTERVAL}s after launching move…")
    time.sleep(AppConfig.MIN_MOVE_INTERVAL)
