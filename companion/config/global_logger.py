import logging
import os

from logging.handlers import RotatingFileHandler
from typing import Optional


class Logger:

    def __init__(self) -> None:
        self._logger: Optional[logging.Logger] = None

    def setup_logger(
        self, service_name: str = "default", log_level: str = "DEBUG"
    ) -> logging.Logger:
        """
        Setup logger with defined configurations.
        """
        if self._logger is not None:
            raise RuntimeError("Logger is already setup.")
        self._logger = logging.getLogger(service_name)

        if os.getenv("ENVIRONMENT") == "development":
            log_path = f"{os.getcwd()}/logs"
            if not os.path.exists(log_path):
                os.mkdir(log_path)

            file_handler = RotatingFileHandler(
                filename=log_path + f"/{service_name}.log",
                encoding="utf-8",
                mode="a",
                maxBytes=10 * 1024 * 1024,  # 10 MiB
                backupCount=5,
            )
            formatter = logging.Formatter(
                "[{asctime}] - {service_name} - {levelname} - {message}",
                style="{",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
        else:
            console_handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[{asctime}] - {service_name} - {levelname} - {message}",
                style="{",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            console_handler.setFormatter(formatter)
            self._logger.addHandler(console_handler)

        self._logger.setLevel(log_level)
        # add service name to log record
        extras = {"service_name": service_name}
        self._logger = logging.LoggerAdapter(self._logger, extras)

        return self._logger


logger = Logger().setup_logger("companion")
