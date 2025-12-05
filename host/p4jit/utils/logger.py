import logging
import sys

# Define INFO_VERBOSE level
INFO_VERBOSE = 15
logging.addLevelName(INFO_VERBOSE, "INFO_VERBOSE")

class Colors:
    RESET = '\033[0m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    GRAY = '\033[90m'
    BOLD = '\033[1m'

class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': Colors.GRAY,
        'INFO_VERBOSE': Colors.CYAN,  # Cyan for detailed info
        'INFO': Colors.BLUE,          # Blue for milestones
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED,
        'CRITICAL': Colors.RED + Colors.BOLD
    }
    
    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
             original_levelname = record.levelname
             record.levelname = f"{self.COLORS[levelname]}{levelname}{Colors.RESET}"
             result = super().format(record)
             record.levelname = original_levelname
             return result
        return super().format(record)

def setup_logger(name: str, level=logging.INFO):
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
        
    logger.setLevel(level)
    
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    
    formatter = ColoredFormatter(
        fmt='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    console.setFormatter(formatter)
    
    logger.addHandler(console)
    logger.propagate = False
    return logger

def set_global_level(level):
    """Set the logging level for the entire p4jit package."""
    # This sets the level for the 'p4jit' parent logger
    # All child loggers (e.g. p4jit.toolchain) will inherit this effective level
    # unless strictly set otherwise.
    logger = logging.getLogger('p4jit')
    logger.setLevel(level)
    
    # Also update handlers
    for handler in logger.handlers:
        handler.setLevel(level)

def enable_file_logging(filename='p4jit.log', level=logging.DEBUG):
    """Enable logging to a file in addition to console."""
    file_handler = logging.FileHandler(filename, mode='w')
    file_handler.setLevel(level)
    formatter = logging.Formatter(
        fmt='[%(asctime)s] [%(name)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    logging.getLogger('p4jit').addHandler(file_handler)
