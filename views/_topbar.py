"""Compatibility entry point for pages using the former section tab bar.

The shared app shell now provides persistent grouped sidebar navigation.
"""


def render_section_tabs(active_section: str | None = None) -> None:
    """Avoid duplicate navigation while preserving existing page callers."""
    return None
