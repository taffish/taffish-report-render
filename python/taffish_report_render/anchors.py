"""正文与校验共享的 renderer DOM ID 规则；不改写既有稳定锚点。"""

FIXED_IDS = frozenset({
    "top", "report-guide", "deliverables", "provenance", "image-modal-title",
    "embedded-subreports-data", "report-toc-data",
})


def child_anchor(ident: str, suffix: str) -> str:
    return f"{ident}-{suffix}"


def component_child_anchors(ident: str, component: dict) -> list[str]:
    suffixes = {
        "code_file": ("code",),
        "tree_viewer": ("newick",),
        "sequence_alignment": ("alignment",),
        "interactive_plot": ("point-size-output", "opacity-output"),
    }.get(component.get("type"), ())
    if component.get("type") == "structure_viewer" and component.get("static_image"):
        suffixes = ("static",)
    return [child_anchor(ident, suffix) for suffix in suffixes]
