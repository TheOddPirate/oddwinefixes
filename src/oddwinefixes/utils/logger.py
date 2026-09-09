import logging
import sys
from oddwinefixes.const import NAME

FILE_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"

CONSOLE_FORMAT = "%(message)s"

def setup_logging(verbose: bool = False, log_to_file: bool = True) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
    root_logger.addHandler(console_handler)
    
    if log_to_file:
        file_handler = logging.FileHandler(f"{NAME.lower()}.log", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
        file_handler.setLevel(logging.DEBUG) 
        root_logger.addHandler(file_handler)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{NAME}.{name}")