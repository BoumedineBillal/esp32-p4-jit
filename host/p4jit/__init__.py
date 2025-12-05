
import logging
from .toolchain.builder import Builder
from .runtime.jit_session import JITSession
from .p4jit import P4JIT
from .runtime.memory_caps import MALLOC_CAP_SPIRAM, MALLOC_CAP_8BIT, MALLOC_CAP_INTERNAL, MALLOC_CAP_EXEC
from .utils.logger import setup_logger, set_global_level, INFO_VERBOSE

# Initialize Root Logger
# This ensures that all 'p4jit.*' loggers share this configuration
setup_logger('p4jit', level=logging.INFO)

def set_log_level(level: str):
    """
    Set logging level: 'DEBUG', 'INFO_VERBOSE', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    
    Example:
        import p4jit
        p4jit.set_log_level('DEBUG')
    """
    level_map = {
        'DEBUG': logging.DEBUG,
        'INFO_VERBOSE': INFO_VERBOSE,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    # Handle both string and int input if user passes raw constants
    if isinstance(level, int):
        val = level
    else:
        val = level_map.get(level.upper(), logging.INFO)
        
    set_global_level(val)
