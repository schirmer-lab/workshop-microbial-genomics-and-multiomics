import functools
import logging
import sys
import time
import warnings
from functools import wraps
from typing import Any, Callable, Optional


class Pipeline:
    """
    A simple data processing pipeline.
    """

    def __init__(self):
        self.steps: list[tuple[str, callable]] = []

    def add(self, name: str, func: callable) -> None:
        """
        Add a function as a step in the pipeline with parameters.
        """
        self.steps.append((name, func))

    def run(self, data: any, verbose: bool = False) -> any:
        """
        Execute the pipeline on the given data.
        """
        for name, func in self.steps:
            if verbose:
                logging.info(f"Running step: {name}")
            data = func(data)
        return data

    def show_steps(self) -> None:
        """
        Show the steps in the pipeline.
        """
        for name, _ in self.steps:
            logging.info(name)


def setup_logging(verbosity: bool = True):
    """
    Set up logging configuration.

    Parameters
    ----------
    verbosity : bool
        If True, logging messages will be displayed.
    """
    logger = logging.getLogger()
    if logger.handlers:
        return

    handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.setLevel(logging.INFO if verbosity else logging.CRITICAL)

    handler.flush = sys.stderr.flush


def deprecated(
    message: Optional[str] = None, alternative: Optional[str] = None
) -> Callable:
    """
    Decorator to mark functions as deprecated.

    Parameters:
    -----------
    message: Optional message explaining why the function is deprecated
    alternative: Name of the function that should be used instead

    Example:
    --------
    @deprecated(message="Will be removed in v2.0", alternative="new_method")
    def old_method():
        pass
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            warning = f"DEPRECATED: {func.__name__} is deprecated"
            if message:
                warning += f" - {message}"
            if alternative:
                warning += f". Use {alternative} instead"

            warnings.warn(warning, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        return wrapper

    if callable(message):
        func = message
        message = None
        return decorator(func)

    return decorator


def timer(description="Execution time"):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            end = time.perf_counter()
            logging.info(
                f"{description} for {func.__name__}: {end - start:.4f} seconds"
            )
            return result

        return wrapper

    return decorator
