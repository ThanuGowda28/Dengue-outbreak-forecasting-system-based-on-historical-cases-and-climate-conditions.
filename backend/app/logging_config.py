from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging(app) -> None:
    configured_log_dir = app.config.get("LOG_DIR")
    log_dir = (
        Path(configured_log_dir)
        if configured_log_dir
        else Path(app.root_path).parent / "logs"
    )
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        app.logger.exception("Could not create application log directory: %s", log_dir)
        return

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s", "%Y-%m-%dT%H:%M:%S%z"
    )
    for name, filename in (
        ("dengue.api", "api.log"),
        ("dengue.prediction", "prediction.log"),
        ("dengue.training", "training.log"),
        ("dengue.system", "system.log"),
        ("dengue.errors", "error.log"),
    ):
        logger = logging.getLogger(name)
        if any(getattr(handler, "baseFilename", "") == str((log_dir / filename).resolve()) for handler in logger.handlers):
            continue
        handler = RotatingFileHandler(log_dir / filename, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
        handler.setFormatter(formatter)
        handler.setLevel(logging.INFO if name != "dengue.errors" else logging.ERROR)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO if name != "dengue.errors" else logging.ERROR)
        logger.propagate = True

    app.logger.info("Rotating application logs configured at %s", log_dir)
