"""
Logging utilities with colorized output
"""

import sys
import logging
from datetime import datetime

class Colors:
    """ANSI color codes"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Regular colors
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'
    
    # Background colors
    BG_RED = '\033[101m'
    BG_GREEN = '\033[102m'
    BG_YELLOW = '\033[103m'

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors"""
    
    def __init__(self, no_color=False):
        super().__init__()
        self.no_color = no_color
        
        self.formats = {
            logging.DEBUG: Colors.GRAY,
            logging.INFO: Colors.BLUE,
            logging.WARNING: Colors.YELLOW,
            logging.ERROR: Colors.RED,
            logging.CRITICAL: Colors.BG_RED + Colors.WHITE
        }
    
    def format(self, record):
        if self.no_color:
            return f"[{record.levelname}] {record.getMessage()}"
        
        color = self.formats.get(record.levelno, Colors.RESET)
        levelname = f"{color}{record.levelname}{Colors.RESET}"
        message = record.getMessage()
        
        return f"[{levelname}] {message}"

class FuzzAILogger:
    """Custom logger for FuzzAI"""
    
    def __init__(self, verbose=False, no_color=False):
        self.verbose = verbose
        self.no_color = no_color
        self.logger = logging.getLogger('FuzzAI')
        
        level = logging.DEBUG if verbose else logging.INFO
        self.logger.setLevel(level)
        
        # Console handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColoredFormatter(no_color=no_color))
        self.logger.addHandler(handler)
    
    def _colorize(self, text, color):
        """Apply color to text"""
        if self.no_color:
            return text
        return f"{color}{text}{Colors.RESET}"
    
    def debug(self, msg):
        """Debug message"""
        self.logger.debug(msg)
    
    def info(self, msg):
        """Info message"""
        self.logger.info(msg)
    
    def success(self, msg):
        """Success message (green)"""
        colored_msg = self._colorize(msg, Colors.GREEN)
        self.logger.info(colored_msg)
    
    def warning(self, msg):
        """Warning message"""
        self.logger.warning(msg)
    
    def error(self, msg):
        """Error message"""
        self.logger.error(msg)
    
    def critical(self, msg):
        """Critical error message"""
        self.logger.critical(msg)
    
    def result(self, status_code, url, size, words, lines):
        """Format and log fuzzing result"""
        # Color based on status code
        if 200 <= status_code < 300:
            color = Colors.GREEN
        elif 300 <= status_code < 400:
            color = Colors.CYAN
        elif 400 <= status_code < 500:
            color = Colors.YELLOW
        else:
            color = Colors.RED
        
        status_colored = self._colorize(f"{status_code}", color)
        
        print(f"{status_colored:15} {url:60} [Size: {size:>8}, Words: {words:>6}, Lines: {lines:>4}]")
    
    def stats(self, total, found, filtered, elapsed):
        """Print statistics"""
        print(f"\n{self._colorize('═' * 80, Colors.CYAN)}")
        print(f"{self._colorize('Statistics:', Colors.BOLD)}")
        print(f"  Total requests:    {total}")
        print(f"  Results found:     {self._colorize(str(found), Colors.GREEN)}")
        print(f"  Filtered out:      {filtered}")
        print(f"  Elapsed time:      {elapsed:.2f}s")
        print(f"{self._colorize('═' * 80, Colors.CYAN)}\n")

# Global logger instance
_logger = None

def setup_logger(verbose=False, no_color=False):
    """Setup global logger"""
    global _logger
    _logger = FuzzAILogger(verbose=verbose, no_color=no_color)
    return _logger

def get_logger():
    """Get global logger instance"""
    global _logger
    if _logger is None:
        _logger = FuzzAILogger()
    return _logger

def log_banner():
    """Print FuzzAI banner"""
    logger = get_logger()
    if not logger.no_color:
        banner = f"""
{Colors.CYAN}{Colors.BOLD}
  ███████╗██╗   ██╗███████╗███████╗     █████╗ ██╗
  ██╔════╝██║   ██║╚══███╔╝╚══███╔╝    ██╔══██╗██║
  █████╗  ██║   ██║  ███╔╝   ███╔╝     ███████║██║
  ██╔══╝  ██║   ██║ ███╔╝   ███╔╝      ██╔══██║██║
  ██║     ╚██████╔╝███████╗███████╗    ██║  ██║██║
  ╚═╝      ╚═════╝ ╚══════╝╚══════╝    ╚═╝  ╚═╝╚═╝
                       _____
{Colors.RESET}
  {Colors.MAGENTA}AI-Powered Directory Fuzzing Tool{Colors.RESET}
  {Colors.GRAY}v1.0.0 | by Sammed101 & Bhaveshs08{Colors.RESET}
{Colors.CYAN}{'─' * 50}{Colors.RESET}
"""
    else:
        banner = """
  FUZZ_AI - AI-Powered Directory Fuzzing Tool
  v1.0.0 | by Sammed101 & Bhaveshs08
  --------------------------------------------------
"""
    print(banner)

# Convenience functions
def log_error(msg):
    """Log error message"""
    get_logger().error(msg)

def log_success(msg):
    """Log success message"""
    get_logger().success(msg)

def log_info(msg):
    """Log info message"""
    get_logger().info(msg)

def log_warning(msg):
    """Log warning message"""
    get_logger().warning(msg)
