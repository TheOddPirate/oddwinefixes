import logging
import sys
from pathlib import Path
from oddwinefixes.const import NAME

FILE_FORMAT = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"

CONSOLE_FORMAT = "%(message)s"


def _get_log_path() -> Path:
    """Checks how we are running and makes sure to adjust the log paths"""
    package_dir = Path(__file__).resolve().parent

    is_installed = "site-packages" in package_dir.parts or "/usr/" in str(package_dir)

    if not is_installed:
        project_root = package_dir.parent.parent.parent
        return project_root / f"{NAME.lower()}.log"

    state_dir = Path.home() / ".local" / "state" / NAME.lower()
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / f"{NAME.lower()}.log"

def setup_logging(verbose: bool = False, log_to_file: bool = True) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT))
    root_logger.addHandler(console_handler)
    
    if log_to_file:
        file_handler = logging.FileHandler(_get_log_path(), encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
        file_handler.setLevel(logging.DEBUG) 
        root_logger.addHandler(file_handler)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{NAME}.{name}")