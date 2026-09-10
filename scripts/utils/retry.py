"""
UnoSnake — Retry avec backoff exponentiel.

Utilisé pour les appels API externes (Serper, Airtable, Pinterest).
"""

import time
import logging

logger = logging.getLogger("unosnake")


def retry_with_backoff(
    func,
    max_retries: int = 3,
    backoff_base: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
    on_retry: callable = None,
):
    """
    Exécute une fonction avec retry et backoff exponentiel.

    Args:
        func: Callable sans arguments à exécuter.
        max_retries: Nombre max de tentatives.
        backoff_base: Base du backoff exponentiel (secondes).
        retryable_exceptions: Tuple d'exceptions à retrier.
        on_retry: Callback optionnel appelé avant chaque retry(attempt, exception).

    Returns:
        Résultat de func().

    Raises:
        Dernière exception si tous les retries échouent.
    """
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except retryable_exceptions as e:
            last_exception = e
            if attempt == max_retries:
                logger.error(f"All {max_retries} attempts failed: {e}")
                raise

            wait_time = backoff_base ** attempt
            logger.warning(
                f"Attempt {attempt}/{max_retries} failed: {e}. "
                f"Retrying in {wait_time:.1f}s..."
            )

            if on_retry:
                on_retry(attempt, e)

            time.sleep(wait_time)

    raise last_exception  # Should not reach here
