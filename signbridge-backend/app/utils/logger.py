"""Logging helpers used across the backend services."""

from __future__ import annotations

import logging
from logging.config import dictConfig


def configure_logging(level: str = "INFO") -> logging.Logger:
	"""Configure structured logging and return the project logger."""

	dictConfig(
		{
			"version": 1,
			"disable_existing_loggers": False,
			"formatters": {
				"default": {
					"format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
				}
			},
			"handlers": {
				"console": {
					"class": "logging.StreamHandler",
					"formatter": "default",
				}
			},
			"root": {
				"handlers": ["console"],
				"level": level.upper(),
			},
		}
	)

	logger = logging.getLogger("signbridge")
	logger.setLevel(level.upper())
	return logger
