"""
UnoSnake — Logging structuré.

Logs lisibles dans GitHub Actions.
Ne log JAMAIS de secrets (tokens, clés API, headers Authorization).
"""

import logging
import sys


def setup_logger(name: str = "unosnake", level: str = "INFO") -> logging.Logger:
    """
    Configure un logger UnoSnake avec format structuré.

    Returns:
        Logger configuré.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Déjà configuré

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logger.level)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def log_step(logger: logging.Logger, step: str, details: str = "") -> None:
    """Log une étape du pipeline avec séparateur visuel."""
    logger.info("=" * 50)
    logger.info(f"STEP: {step}")
    if details:
        logger.info(details)
    logger.info("=" * 50)


def log_summary(
    logger: logging.Logger,
    searched: int = 0,
    found: int = 0,
    eliminated: int = 0,
    kept: int = 0,
    created: int = 0,
    errors: int = 0,
) -> None:
    """Log un résumé de fin de pipeline."""
    logger.info("=" * 50)
    logger.info("PIPELINE SUMMARY")
    logger.info(f"  Searched:    {searched} queries")
    logger.info(f"  Found:       {found} candidates")
    logger.info(f"  Eliminated:  {eliminated} (duplicates/low score)")
    logger.info(f"  Kept:        {kept} candidates")
    logger.info(f"  Created:     {created} Airtable records")
    logger.info(f"  Errors:      {errors}")
    logger.info("=" * 50)
