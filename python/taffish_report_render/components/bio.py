"""Bioinformatics viewer component contracts."""

from __future__ import annotations

from typing import Any


BIO_COMPONENT_REGISTRY: dict[str, dict[str, Any]] = {
    "tree_viewer": {
        "kind": "render",
        "summary": "Embed and render a small Newick phylogeny as an inline SVG tree with a copyable source.",
        "required": ["source"],
        "path_fields": ["source"],
        "fields": [
            "id",
            "type",
            "source",
            "title",
            "note",
            "layout",
            "width",
            "height",
            "show_labels",
            "show_branch_lengths",
            "branch_color",
            "branch_width",
            "label_color",
            "label_size",
            "scale_color",
            "background",
            "copy",
            "max_tips",
        ],
    },
    "sequence_alignment": {
        "kind": "render",
        "summary": "Embed a FASTA or CLUSTAL multiple sequence alignment as a compact colored alignment browser.",
        "required": ["source"],
        "path_fields": ["source"],
        "fields": [
            "id",
            "type",
            "source",
            "format",
            "title",
            "note",
            "alphabet",
            "color_scheme",
            "font_size",
            "label_width",
            "gap_color",
            "residue_a",
            "residue_c",
            "residue_g",
            "residue_t",
            "residue_u",
            "residue_n",
            "residue_hydrophobic",
            "residue_positive",
            "residue_negative",
            "residue_polar",
            "residue_special",
            "wrap",
            "show_consensus",
            "copy",
            "max_sequences",
            "max_columns",
        ],
    },
    "genome_browser": {
        "kind": "render",
        "summary": "Declare an IGV-style genome browser using embedded runtime code and external/local reference or track URLs.",
        "required": ["locus"],
        "path_fields": [],
        "fields": [
            "id",
            "type",
            "title",
            "note",
            "runtime",
            "viewer_mode",
            "data_mode",
            "genome",
            "locus",
            "reference_name",
            "reference_fasta",
            "reference_index",
            "embed_reference",
            "embed_tracks",
            "tracks",
            "height",
            "controls_open",
        ],
    },
}


BIO_COMPONENT_DOCS: dict[str, str] = {
    "tree_viewer": (
        "tree_viewer reads a Newick file, embeds the source text, and renders an inline SVG tree. "
        "It is intended for small and medium phylogeny reports where a standalone HTML should still "
        "show the tree even if external tree-viewing software is unavailable."
    ),
    "sequence_alignment": (
        "sequence_alignment reads FASTA or CLUSTAL alignments and renders a scrollable, colored, "
        "copyable alignment view. It is a report browser, not an aligner; upstream tools must compute "
        "the alignment before rendering."
    ),
    "genome_browser": (
        "genome_browser declares an IGV-style browser panel. Large BAM/CRAM/BigWig/VCF data should "
        "normally stay external or local-linked; small FASTA/FAI/BED/GFF/bedGraph fixtures can be "
        "embedded through embed_reference/embed_tracks while the report records every asset."
    ),
}


SUPPORTED_TREE_LAYOUTS = {"rectangular"}
SUPPORTED_ALIGNMENT_FORMATS = {"auto", "fasta", "clustal"}
SUPPORTED_ALIGNMENT_ALPHABETS = {"auto", "dna", "rna", "protein"}
SUPPORTED_ALIGNMENT_COLOR_SCHEMES = {"taffish", "classic", "mono"}
SUPPORTED_GENOME_RUNTIMES = {"igv"}
SUPPORTED_GENOME_DATA_MODES = {"external", "local", "linked", "embedded", "embedded-small-assets"}
SUPPORTED_GENOME_VIEWER_MODES = {"embedded", "linked"}


def _looks_external_resource(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    if stripped.startswith(("#", "data:", "mailto:", "tel:", "javascript:", "//")):
        return True
    if ":" in stripped.split("/", 1)[0]:
        return True
    return False


def genome_browser_component_paths(component: dict[str, Any]) -> list[tuple[str, str]]:
    paths: list[tuple[str, str]] = []
    for field in ("reference_fasta", "reference_index"):
        value = str(component.get(field, "") or "").strip()
        if value and not _looks_external_resource(value):
            paths.append((field, value))
    tracks = component.get("tracks", []) or []
    if isinstance(tracks, list):
        for idx, track in enumerate(tracks):
            if not isinstance(track, dict):
                continue
            for field in ("source", "url", "index_url"):
                value = str(track.get(field, "") or "").strip()
                if value and not _looks_external_resource(value):
                    paths.append((f"tracks[{idx}].{field}", value))
    return paths


def validate_bio_component(component: dict[str, Any], location: str) -> None:
    ctype = str(component.get("type", ""))
    if ctype == "tree_viewer":
        layout = str(component.get("layout", "rectangular")).strip().lower()
        if layout not in SUPPORTED_TREE_LAYOUTS:
            raise ValueError(f"{location}.layout must be one of: {', '.join(sorted(SUPPORTED_TREE_LAYOUTS))}")
        return
    if ctype == "sequence_alignment":
        fmt = str(component.get("format", "auto")).strip().lower()
        if fmt not in SUPPORTED_ALIGNMENT_FORMATS:
            raise ValueError(f"{location}.format must be one of: {', '.join(sorted(SUPPORTED_ALIGNMENT_FORMATS))}")
        alphabet = str(component.get("alphabet", "auto")).strip().lower()
        if alphabet not in SUPPORTED_ALIGNMENT_ALPHABETS:
            raise ValueError(f"{location}.alphabet must be one of: {', '.join(sorted(SUPPORTED_ALIGNMENT_ALPHABETS))}")
        color_scheme = str(component.get("color_scheme", "taffish")).strip().lower()
        if color_scheme not in SUPPORTED_ALIGNMENT_COLOR_SCHEMES:
            raise ValueError(
                f"{location}.color_scheme must be one of: {', '.join(sorted(SUPPORTED_ALIGNMENT_COLOR_SCHEMES))}"
            )
        return
    if ctype == "genome_browser":
        runtime = str(component.get("runtime", "igv")).strip().lower()
        if runtime not in SUPPORTED_GENOME_RUNTIMES:
            raise ValueError(f"{location}.runtime must be one of: {', '.join(sorted(SUPPORTED_GENOME_RUNTIMES))}")
        viewer_mode = str(component.get("viewer_mode", "embedded")).strip().lower()
        if viewer_mode not in SUPPORTED_GENOME_VIEWER_MODES:
            raise ValueError(f"{location}.viewer_mode must be one of: {', '.join(sorted(SUPPORTED_GENOME_VIEWER_MODES))}")
        data_mode = str(component.get("data_mode", "external")).strip().lower()
        if data_mode not in SUPPORTED_GENOME_DATA_MODES:
            raise ValueError(f"{location}.data_mode must be one of: {', '.join(sorted(SUPPORTED_GENOME_DATA_MODES))}")
        tracks = component.get("tracks", []) or []
        if tracks and not isinstance(tracks, list):
            raise ValueError(f"{location}.tracks must be a list of track tables")
