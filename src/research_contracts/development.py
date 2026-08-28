"""Noncanonical boundary for direct legacy/development research entry points."""

from __future__ import annotations

import inspect
import warnings
from pathlib import Path

from .governance import UNGOVERNED_CLASS, label_ungoverned_output


DEVELOPMENT_WARNING = (
    "DEVELOPMENT ONLY: this entry point produces UNGOVERNED_NONCANONICAL_OUTPUT; "
    "it cannot update canonical evidence or lifecycle state."
)


def mark_development_output(output_root: str | Path, *, entrypoint: str) -> Path:
    warnings.warn(f"{DEVELOPMENT_WARNING} entrypoint={entrypoint}", RuntimeWarning, stacklevel=2)
    return label_ungoverned_output(
        output_root, reason=f"direct development entry point: {entrypoint}"
    )


def mark_data_test_script_if_present(artifacts_root: str | Path) -> Path | None:
    """Mark a direct Data-test script regardless of shell or wrapper invocation."""
    for frame in inspect.stack():
        path = Path(frame.filename).resolve()
        if path.parent.name == "scripts" and path.parent.parent.name == "Data test":
            destination = Path(artifacts_root) / "noncanonical_entrypoints" / path.stem
            return mark_development_output(destination, entrypoint=str(path))
    return None


__all__ = ["DEVELOPMENT_WARNING", "UNGOVERNED_CLASS", "mark_development_output",
           "mark_data_test_script_if_present"]
