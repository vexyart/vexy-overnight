"""Legacy data summarisation helpers kept for backward compatibility."""
# this_file: src/vexy_overnight/vexy_overnight.py

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import copy, deepcopy
from dataclasses import dataclass
from typing import Any, TypedDict

from loguru import logger


class Summary(TypedDict):
    """Structured representation of ``process_data`` results."""

    count: int
    unique_count: int
    types: list[str]
    config_name: str | None
    first_item: str
    options: dict[str, Any]


@dataclass(slots=True)
class Config:
    """Configuration settings for ``process_data`` summarisation."""

    name: str
    value: str | int | float
    options: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        """Validate ``options`` to ensure they are mapping-like with string keys."""
        if self.options is None:
            return

        if not isinstance(self.options, Mapping):
            raise TypeError("Config options must be a mapping")

        if any(not isinstance(key, str) for key in self.options):
            raise TypeError("Config option keys must be strings")


def process_data(
    data: Sequence[Any],
    config: Config | None = None,
    *,
    debug: bool = False,
) -> Summary:
    """Summarise ``data`` into a deterministic :class:`Summary` mapping.

    Args:
        data: Sequence of items to inspect; must not be empty.
        config: Optional configuration whose metadata is surfaced in the
            summary.
        debug: When ``True`` emit debug-level logging while computing the
            summary.

    Returns:
        Summary: Dictionary describing collection size, unique counts, type
        distribution, and derived configuration metadata.

    Raises:
        TypeError: If ``data`` is not a sequence or ``config`` is not a
            :class:`Config` instance.
        ValueError: If ``data`` is empty.
    """
    if isinstance(data, str | bytes) or not isinstance(data, Sequence):
        raise TypeError("Input data must be a sequence of records")

    if not data:
        raise ValueError("Input data cannot be empty")

    if config is not None and not isinstance(config, Config):
        raise TypeError("config must be a Config instance")

    if debug:
        logger.debug("Debug mode enabled")

    if config and config.options is not None:
        options_copy: dict[str, Any] = {}
        for key, value in config.options.items():
            try:
                options_copy[key] = deepcopy(value)
                continue
            except Exception:
                pass

            try:
                options_copy[key] = copy(value)
                continue
            except Exception:
                options_copy[key] = repr(value)
    else:
        options_copy = {}

    summary: Summary = {
        "count": len(data),
        "unique_count": len({repr(item) for item in data}),
        "types": sorted({type(item).__name__ for item in data}),
        "config_name": config.name if config else None,
        "first_item": repr(data[0]),
        "options": options_copy,
    }

    if debug:
        logger.debug("Summary generated: {}", summary)

    return summary


def main() -> None:
    """Demonstrate :func:`process_data` by logging a simple summary."""
    sample = [1, 2, 3]
    config = Config(name="default", value="demo", options={"label": "sample"})
    summary = process_data(sample, config=config, debug=False)
    logger.info("Processing completed: {}", summary)


if __name__ == "__main__":
    main()
