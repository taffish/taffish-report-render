"""Component extension API for taffish-report-render.

This package keeps component-specific contracts and helpers outside the main
CLI. The CLI still owns report rendering orchestration, while each component
module can contribute registry metadata, docs, path discovery, validation, and
data preparation helpers.
"""

from __future__ import annotations

from typing import Any

from .bio import (
    BIO_COMPONENT_DOCS,
    BIO_COMPONENT_REGISTRY,
    genome_browser_component_paths,
    validate_bio_component,
)
from .interactive import (
    INTERACTIVE_PLOT_COMPONENT_DOCS,
    INTERACTIVE_PLOT_COMPONENT_REGISTRY,
    validate_interactive_plot_component,
)
from .structure import (
    STRUCTURE_COMPONENT_DOCS,
    STRUCTURE_COMPONENT_REGISTRY,
    normalize_structure_models,
    parse_pdb_atoms,
    structure_component_paths,
    validate_structure_component,
)


COMPONENT_REGISTRY_EXTENSIONS: dict[str, dict[str, Any]] = {
    **BIO_COMPONENT_REGISTRY,
    **INTERACTIVE_PLOT_COMPONENT_REGISTRY,
    **STRUCTURE_COMPONENT_REGISTRY,
}

COMPONENT_DOC_EXTENSIONS: dict[str, str] = {
    **BIO_COMPONENT_DOCS,
    **INTERACTIVE_PLOT_COMPONENT_DOCS,
    **STRUCTURE_COMPONENT_DOCS,
}


def extended_component_path_values(component: dict[str, Any]) -> list[tuple[str, str]]:
    """Return component-specific path fields not expressible as flat keys."""

    ctype = str(component.get("type", ""))
    if ctype == "structure_viewer":
        return structure_component_paths(component)
    if ctype == "genome_browser":
        return genome_browser_component_paths(component)
    return []


def validate_extended_component(component: dict[str, Any], location: str) -> None:
    """Run component-specific validation hooks."""

    ctype = str(component.get("type", ""))
    if ctype == "structure_viewer":
        validate_structure_component(component, location)
    elif ctype == "interactive_plot":
        validate_interactive_plot_component(component, location)
    elif ctype in {"tree_viewer", "sequence_alignment", "genome_browser"}:
        validate_bio_component(component, location)


__all__ = [
    "COMPONENT_DOC_EXTENSIONS",
    "COMPONENT_REGISTRY_EXTENSIONS",
    "extended_component_path_values",
    "normalize_structure_models",
    "parse_pdb_atoms",
    "validate_extended_component",
]
