import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from time import perf_counter

from flask import g, request
from flask.logging import default_handler


def configure_logging(app):
    log_file = Path(app.config.get("LOG_FILE", Path(app.root_path).parent / "logs" / "iot.log"))
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = app.logger
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Flask współdzieli logger między instancjami aplikacji — nie dublujemy handlerów.
    for handler in logger.handlers[:]:
        if handler is default_handler or handler.name in {"iot_console", "iot_file"}:
            logger.removeHandler(handler)
            if handler is not default_handler:
                handler.close()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    console = logging.StreamHandler()
    console.set_name("iot_console")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.set_name("iot_file")
    for handler in (console, file_handler):
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    @app.before_request
    def start_request():
        g.request_started_at = perf_counter()
        g.username = None

    @app.after_request
    def log_request(response):
        duration_ms = (perf_counter() - g.request_started_at) * 1000
        if response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.WARNING
        else:
            level = logging.INFO
        logger.log(
            level,
            "%s %r status=%d duration_ms=%.2f user=%r",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            g.username,
        )
        return response
