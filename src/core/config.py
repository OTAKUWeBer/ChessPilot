class AppConfig:
    BG_COLOR = "#2D2D2D"
    FRAME_COLOR = "#373737"
    ACCENT_COLOR = "#4CAF50"
    TEXT_COLOR = "#FFFFFF"
    HOVER_COLOR = "#45a049"

    DEFAULT_DEPTH = 15
    DEFAULT_SCREENSHOT_DELAY = 0.4
    DEFAULT_MOVE_MODE = "drag"
    
    # Delay before capturing board after detecting opponent's turn (seconds)
    OPPONENT_MOVE_SETTLE_DELAY = 0.5
    
    # Delay between polling attempts in auto mode (seconds)
    AUTO_MODE_POLL_INTERVAL = 0.1
    
    # Maximum retries for FEN extraction when it fails
    MAX_FEN_EXTRACTION_RETRIES = 3
    
    # Delay between FEN extraction retries (seconds)
    FEN_RETRY_DELAY = 0.5
    
    # Minimum time between move executions (prevents too-fast moves)
    MIN_MOVE_INTERVAL = 0.3
    
    # Maximum consecutive failures before auto mode stops
    MAX_CONSECUTIVE_FAILURES = 3
    
    # Skip verification if it fails (continue with move execution)
    SKIP_VERIFICATION_ON_FAILURE = True
    
    BOARD_DETECTION_CONFIDENCE = 0.5

    WINDOW_TITLE = "ChessPilot"
    WINDOW_WIDTH = 380
    WINDOW_HEIGHT = 480
