import logging

COLOR_RESET = "\x1b[0m"
COLOR_RED = "\x1b[31m"
COLOR_YELLOW = "\x1b[33m"
COLOR_GREEN = "\x1b[32m"
COLOR_CYAN = "\x1b[36m"

class ColorFormatter(logging.Formatter):
    LEVEL_COLORS = {
        logging.DEBUG: COLOR_CYAN,
        logging.INFO: COLOR_GREEN,
        logging.WARNING: COLOR_YELLOW,
        logging.ERROR: COLOR_RED,
        logging.CRITICAL: COLOR_RED,
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, COLOR_RESET)
        record.levelname = f"{color}{record.levelname}{COLOR_RESET}"
        record.msg = f"{color}{record.msg}{COLOR_RESET}"
        return super().format(record)

def setup_console_logging(level=logging.DEBUG):
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    fmt = "[%(asctime)s] [%(levelname)s] %(message)s"
    console_handler.setFormatter(ColorFormatter(fmt, datefmt="%H:%M:%S"))

    root_logger.addHandler(console_handler)