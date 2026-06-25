"""Interactive plot component helpers."""

from __future__ import annotations

from typing import Any


INTERACTIVE_PLOT_COMPONENT_REGISTRY: dict[str, dict[str, Any]] = {
    "interactive_plot": {
        "kind": "render",
        "summary": "Embed a compact tabular payload and render a browser-side ECharts view with report-local controls.",
        "required": ["source", "kind"],
        "path_fields": ["source"],
        "fields": [
            "id",
            "type",
            "source",
            "kind",
            "title",
            "note",
            "x",
            "y",
            "label",
            "size",
            "color",
            "pvalue",
            "padj",
            "log2fc",
            "base_mean",
            "gene",
            "description",
            "count",
            "gene_ratio",
            "sample",
            "group",
            "pc1",
            "pc2",
            "x_label",
            "y_label",
            "default_padj",
            "default_log2fc",
            "top_n",
            "max_points",
            "height",
            "controls_open",
            "point_size",
            "opacity",
            "color_up",
            "color_down",
            "color_ns",
            "color_low",
            "color_high",
            "label_max_chars",
            "fixed_range",
            "show_threshold_lines",
        ],
    },
}


INTERACTIVE_PLOT_COMPONENT_DOCS: dict[str, str] = {
    "interactive_plot": (
        "interactive_plot embeds a TSV/CSV-derived JSON payload and renders a "
        "browser-side ECharts view such as volcano, MA, PCA, or ORA dot plot. Controls only "
        "filter or restyle already-computed result rows; they do not recompute "
        "statistical models, differential expression, or enrichment."
    ),
}


SUPPORTED_INTERACTIVE_PLOT_KINDS = {"volcano", "ma", "ora_dotplot", "pca"}


def validate_interactive_plot_component(component: dict[str, Any], location: str) -> None:
    kind = str(component.get("kind", "")).strip().lower()
    if kind not in SUPPORTED_INTERACTIVE_PLOT_KINDS:
        raise ValueError(
            f"{location}.kind must be one of: {', '.join(sorted(SUPPORTED_INTERACTIVE_PLOT_KINDS))}"
        )
