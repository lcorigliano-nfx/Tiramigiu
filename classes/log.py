from logging.handlers import RotatingFileHandler
import logging
import os
from colorlog import ColoredFormatter

class Log:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Log, cls).__new__(cls)
            cls._instance._initialize_logger()
        return cls._instance

    def _initialize_logger(self):
        self.logger = logging.getLogger("TiramigiuLogger")
        self.logger.setLevel(logging.DEBUG)

        # Ensure the logs directory exists
        os.makedirs('./logs', exist_ok=True)

        # Console handler with color
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_formatter = ColoredFormatter(
            '%(log_color)s%(asctime)s - %(class_name)s - %(levelname)s - %(message)s',
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(console_formatter)

        # File handler for general logs
        file_handler = RotatingFileHandler('./logs/general.log', maxBytes=5*1024*1024, backupCount=5)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(class_name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        # File handler for error logs
        error_handler = RotatingFileHandler('./logs/error.log', maxBytes=5*1024*1024, backupCount=5)
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter('%(asctime)s - %(class_name)s - %(levelname)s - %(message)s')
        error_handler.setFormatter(error_formatter)

        # Add handlers to the logger
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)

    def get_logger(self, class_name):
        return logging.LoggerAdapter(self.logger, {'class_name': class_name})