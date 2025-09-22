# this_file: tests/test_vexy_overnight.py
"""Regression tests for legacy summarisation helpers exposed by the package."""

from __future__ import annotations

from typing import Any

import pytest
from loguru import logger


def test_import_exposes_public_api() -> None:
    """Importing the package should expose the documented public symbols."""
    import vexy_overnight as pkg

    assert {"__version__", "Config", "process_data"}.issubset(dir(pkg)), (
        "Package should expose expected symbols"
    )
    assert callable(pkg.process_data), "Package should expose process_data callable"


def test_process_data_when_valid_input_then_returns_summary() -> None:
    """Valid input sequences yield a populated summary mapping."""
    import vexy_overnight as pkg

    config = pkg.Config(name="numbers", value="unit-test")
    summary = pkg.process_data([1, 2, 2, 3], config=config)

    assert summary["count"] == 4, "Count should match input length"
    assert summary["unique_count"] == 3, "Unique count should deduplicate values"
    assert summary["types"] == ["int"], "Types should list unique type names"
    assert summary["config_name"] == "numbers", "Config name should propagate into summary"
    assert summary["first_item"] == "1", "First item should be stringified"
    assert summary["options"] == {}, "Options default to empty dict"


def test_process_data_when_empty_input_then_raises_value_error() -> None:
    """Empty sequences raise :class:`ValueError` to prevent undefined output."""
    import vexy_overnight as pkg

    with pytest.raises(ValueError, match="cannot be empty"):
        pkg.process_data([])


@pytest.mark.parametrize("bad_input", ["not a sequence of records", 42])  # type: ignore[misc]
def test_process_data_when_non_sequence_like_input_then_raises_type_error(
    bad_input: object,
) -> None:
    """Non-sequence inputs such as strings raise :class:`TypeError`."""
    import vexy_overnight as pkg

    with pytest.raises(TypeError, match="sequence"):
        pkg.process_data(bad_input)  # type: ignore[arg-type]


def test_process_data_when_config_options_then_copies_into_summary() -> None:
    """Options mappings are copied to keep summaries isolated from inputs."""
    import vexy_overnight as pkg

    options: dict[str, str] = {"label": "dataset"}
    config = pkg.Config(name="meta", value=1, options=options)
    summary = pkg.process_data([{"id": 1}, {"id": 1}], config=config)

    assert summary["unique_count"] == 1, "Unhashable items should be deduplicated via repr"
    assert summary["options"] == {"label": "dataset"}, "Options should be copied into summary"
    assert summary["options"] is not options, "Options must be copied to avoid mutation"


def test_process_data_when_options_mapping_proxy_then_copies_as_plain_dict() -> None:
    """Mapping proxies are materialised into mutable dictionaries in the summary."""
    from types import MappingProxyType

    import vexy_overnight as pkg

    options = MappingProxyType({"nested": {"value": 1}})
    config = pkg.Config(name="meta", value=1, options=options)
    summary = pkg.process_data([1], config=config)

    assert summary["options"] == {"nested": {"value": 1}}, "Summary should copy proxy content"
    assert isinstance(summary["options"], dict), "Summary options must be a plain dict"
    assert summary["options"] is not options, "Summary should not reuse proxy object"

    summary["options"]["nested"]["value"] = 2
    assert options["nested"]["value"] == 1, "Mutations in summary must not leak back to proxy"


def test_process_data_when_option_value_deepcopy_fails_then_falls_back() -> None:
    """Copy failures fallback to shallow copies or repr strings safely."""
    import vexy_overnight as pkg

    class FragileValue:
        def __init__(self, marker: str) -> None:
            self.marker = marker

        def __copy__(self) -> FragileValue:
            return FragileValue(self.marker)

        def __deepcopy__(self, memo: dict[int, Any]) -> FragileValue:
            raise RuntimeError("no deepcopy available")

    original = FragileValue("token")
    config = pkg.Config(name="meta", value=1, options={"fragile": original})
    summary = pkg.process_data([1], config=config)

    fragile_copy = summary["options"]["fragile"]
    assert isinstance(fragile_copy, FragileValue), "Fallback should keep object type"
    assert fragile_copy is not original, "Summary must not reuse original object"

    fragile_copy.marker = "updated"
    assert original.marker == "token", "Mutating summary copy must not leak to source"

    class StubbornValue(FragileValue):
        def __copy__(self) -> StubbornValue:
            raise RuntimeError("no shallow copy available")

        def __deepcopy__(self, memo: dict[int, Any]) -> StubbornValue:
            raise RuntimeError("no deep copy available")

        def __repr__(self) -> str:
            return f"StubbornValue({self.marker})"

    stubborn = StubbornValue("token")
    stubborn_summary = pkg.process_data(
        [1], config=pkg.Config(name="meta", value=2, options={"stubborn": stubborn})
    )

    stubborn_option = stubborn_summary["options"]["stubborn"]
    assert stubborn_option == "StubbornValue(token)", "repr fallback should preserve descriptor"


def test_process_data_when_tuple_and_deque_then_summary_remains_stable() -> None:
    """Non-list sequences such as tuples or deques produce deterministic output."""
    from collections import deque

    import vexy_overnight as pkg

    tuple_summary = pkg.process_data((1, 2, 2))
    assert tuple_summary["count"] == 3, "Tuple input should count all items"
    assert tuple_summary["unique_count"] == 2, "Tuple input should deduplicate"
    assert tuple_summary["first_item"] == "1", "Tuple first item repr should match"
    assert tuple_summary["types"] == ["int"], "Tuple types should detect ints"

    queue = deque(["a", "b"])
    deque_summary = pkg.process_data(queue)
    assert deque_summary["count"] == 2, "Deque input should be supported"
    assert deque_summary["first_item"] == "'a'", "Deque first item repr should be stable"
    assert deque_summary["types"] == ["str"], "Deque types should detect strings"


def test_process_data_when_config_not_config_instance_then_raises_type_error() -> None:
    """:class:`TypeError` should be raised when ``config`` is not a ``Config`` instance."""
    import vexy_overnight as pkg

    class FakeConfig:
        name = "fake"
        options: dict[str, Any] = {}

    with pytest.raises(TypeError, match="Config"):
        pkg.process_data([1], config=FakeConfig())  # type: ignore[arg-type]


def test_process_data_when_debug_true_then_emits_debug_log() -> None:
    """Debug flag should emit diagnostic logging to ``loguru`` sinks."""
    import vexy_overnight as pkg

    messages: list[str] = []
    sink_id = logger.add(messages.append, level="DEBUG")
    try:
        pkg.process_data([42], debug=True)
    finally:
        logger.remove(sink_id)

    assert any("Debug mode enabled" in message for message in messages), (
        "Debug flag should emit debug log"
    )


def test_main_when_called_then_logs_summary() -> None:
    """Top-level ``main`` helper should log a completion summary."""
    import vexy_overnight.vexy_overnight as module

    messages: list[str] = []
    sink_id = logger.add(messages.append, level="INFO")
    try:
        module.main()
    finally:
        logger.remove(sink_id)

    assert any("Processing completed" in message for message in messages), (
        "Main should log completion message"
    )
    assert any("'count': 3" in message for message in messages), "Main summary should include count"


@pytest.mark.parametrize(  # type: ignore[misc]
    ("options", "match"),
    [([("key", "value")], "mapping"), ({1: "value"}, "string")],
)
def test_config_when_options_invalid_then_raises_type_error(options: object, match: str) -> None:
    """Invalid option payloads for :class:`Config` constructor raise ``TypeError``."""
    import vexy_overnight as pkg

    with pytest.raises(TypeError, match=match):
        pkg.Config(name="invalid", value=1, options=options)  # type: ignore[arg-type]


def test_process_data_when_nested_options_then_summary_is_isolated() -> None:
    """Nested mutable objects should be deep-copied to prevent aliasing."""
    import vexy_overnight as pkg

    options = {"nested": {"tags": ["a"]}}
    config = pkg.Config(name="meta", value=1, options=options)
    summary = pkg.process_data([1], config=config)

    options["nested"]["tags"].append("b")
    summary["options"]["nested"]["tags"].append("c")

    assert options["nested"]["tags"] == ["a", "b"], "Config options should track its own mutations"
    assert summary["options"]["nested"]["tags"] == [
        "a",
        "c",
    ], "Summary options should not share nested structures"


def test_process_data_summary_has_expected_keys() -> None:
    """Summaries should expose the canonical set of keys for consumers."""
    import vexy_overnight as pkg

    summary: pkg.Summary = pkg.process_data([1, 2, 3])

    expected_keys = {"count", "unique_count", "types", "config_name", "first_item", "options"}
    assert set(summary) == expected_keys, "Summary should expose the canonical key set"
