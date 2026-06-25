"""Structure/PDB report component helpers."""

from __future__ import annotations

from typing import Any


STRUCTURE_COMPONENT_REGISTRY: dict[str, dict[str, Any]] = {
    "structure_viewer": {
        "kind": "render",
        "summary": "Embed PDB/mmCIF-style structure evidence with an optional static image and an interactive structure viewer runtime.",
        "required": [],
        "path_fields": ["pdb", "static_image", "site_table"],
        "fields": [
            "id",
            "type",
            "title",
            "note",
            "pdb",
            "static_image",
            "runtime",
            "representation",
            "color_scheme",
            "show_surface",
            "spin",
            "controls_open",
            "fallback",
            "background",
            "atom_filter",
            "max_atoms",
            "height",
            "models",
            "site_groups",
            "site_table",
            "site_structure_id",
            "site_structure_column",
            "site_model",
            "site_chain",
            "site_chain_column",
            "site_residue_column",
            "site_group_column",
            "site_label_column",
            "site_max_sites",
            "copy",
        ],
    },
}


STRUCTURE_COMPONENT_DOCS: dict[str, str] = {
    "structure_viewer": (
        "structure_viewer embeds one or more PDB files as a report component. "
        "Use runtime='builtin' for the lightweight trace viewer or runtime='ngl' "
        "for the optional NGL WebGL runtime pack. Runtime packs are embedded only "
        "when a component explicitly requests them."
    ),
}


SUPPORTED_RUNTIME = {"builtin", "ngl"}
SUPPORTED_ATOM_FILTERS = {"ca", "backbone", "all"}
SUPPORTED_REPRESENTATIONS = {"cartoon", "backbone", "licorice", "ball+stick", "spacefill", "surface"}


def structure_component_paths(component: dict[str, Any]) -> list[tuple[str, str]]:
    values: list[tuple[str, str]] = []
    if component.get("site_table"):
        values.append(("site_table", str(component["site_table"])))
    for idx, model in enumerate(component.get("models", []) or []):
        if isinstance(model, dict) and model.get("pdb"):
            values.append((f"models[{idx}].pdb", str(model["pdb"])))
    return values


def normalize_structure_models(component: dict[str, Any]) -> list[dict[str, Any]]:
    models = component.get("models")
    if isinstance(models, list) and models:
        normalized = []
        for idx, model in enumerate(models, start=1):
            if not isinstance(model, dict):
                continue
            item = dict(model)
            item.setdefault("id", f"model-{idx}")
            item.setdefault("label", item.get("title", item["id"]))
            item.setdefault("color", default_model_color(idx - 1))
            normalized.append(item)
        return normalized
    if component.get("pdb"):
        return [
            {
                "id": "model-1",
                "label": component.get("title", "model-1"),
                "pdb": component["pdb"],
                "color": component.get("color", default_model_color(0)),
            }
        ]
    return []


def validate_structure_component(component: dict[str, Any], location: str) -> None:
    models = normalize_structure_models(component)
    if not models:
        raise ValueError(f"{location} requires either pdb or [[sections.components.models]]")
    runtime = str(component.get("runtime", "builtin")).strip().lower()
    if runtime not in SUPPORTED_RUNTIME:
        raise ValueError(f"{location}.runtime must be one of: {', '.join(sorted(SUPPORTED_RUNTIME))}")
    atom_filter = str(component.get("atom_filter", "ca")).strip().lower()
    if atom_filter not in SUPPORTED_ATOM_FILTERS:
        raise ValueError(f"{location}.atom_filter must be one of: {', '.join(sorted(SUPPORTED_ATOM_FILTERS))}")
    representation = str(component.get("representation", "cartoon")).strip().lower()
    if representation not in SUPPORTED_REPRESENTATIONS:
        raise ValueError(f"{location}.representation must be one of: {', '.join(sorted(SUPPORTED_REPRESENTATIONS))}")
    for idx, model in enumerate(models, start=1):
        if not model.get("pdb"):
            raise ValueError(f"{location}.models[{idx}].pdb is required")


def default_model_color(index: int) -> str:
    colors = ["#087f74", "#1d5fd7", "#b7791f", "#be123c", "#5b21b6", "#0f766e"]
    return colors[index % len(colors)]


def parse_pdb_atoms(text: str, atom_filter: str = "ca", max_atoms: int = 2500) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parse a PDB text block into a compact atom payload for the report viewer."""

    atom_filter = atom_filter if atom_filter in SUPPORTED_ATOM_FILTERS else "ca"
    raw_atoms: list[dict[str, Any]] = []
    ca_atoms: list[dict[str, Any]] = []
    backbone_atoms: list[dict[str, Any]] = []
    chains: set[str] = set()
    residues: set[tuple[str, str, str]] = set()
    atom_rows = 0
    hetatm_rows = 0
    for line in text.splitlines():
        record = line[:6].strip()
        if record not in {"ATOM", "HETATM"}:
            continue
        if record == "ATOM":
            atom_rows += 1
        else:
            hetatm_rows += 1
        name = line[12:16].strip() if len(line) >= 16 else ""
        residue = line[17:20].strip() if len(line) >= 20 else ""
        chain = (line[21].strip() if len(line) >= 22 else "") or "_"
        resseq = line[22:26].strip() if len(line) >= 26 else ""
        try:
            x = float(line[30:38])
            y = float(line[38:46])
            z = float(line[46:54])
        except ValueError:
            continue
        element = (line[76:78].strip() if len(line) >= 78 else "") or infer_element(name)
        atom = {
            "serial": line[6:11].strip() if len(line) >= 11 else "",
            "name": name,
            "residue": residue,
            "chain": chain,
            "resseq": resseq,
            "element": element,
            "x": round(x, 3),
            "y": round(y, 3),
            "z": round(z, 3),
        }
        raw_atoms.append(atom)
        chains.add(chain)
        residues.add((chain, resseq, residue))
        if record == "ATOM" and name == "CA":
            ca_atoms.append(atom)
        if record == "ATOM" and name in {"N", "CA", "C", "O"}:
            backbone_atoms.append(atom)
    selected = raw_atoms
    selected_filter = "all"
    if atom_filter == "ca" and ca_atoms:
        selected = ca_atoms
        selected_filter = "ca"
    elif atom_filter == "backbone" and backbone_atoms:
        selected = backbone_atoms
        selected_filter = "backbone"
    elif atom_filter == "ca":
        selected_filter = "all"
    elif atom_filter == "backbone":
        selected_filter = "all"
    truncated = len(selected) > max_atoms
    selected = selected[:max_atoms]
    summary = {
        "atom_rows": atom_rows,
        "hetatm_rows": hetatm_rows,
        "chains": len(chains),
        "residues": len(residues),
        "viewer_atoms": len(selected),
        "atom_filter": selected_filter,
        "truncated": truncated,
    }
    return selected, summary


def infer_element(atom_name: str) -> str:
    stripped = "".join(ch for ch in atom_name.strip() if ch.isalpha())
    if not stripped:
        return ""
    if len(stripped) >= 2 and stripped[:2].title() in {"Cl", "Br", "Fe", "Mg", "Zn", "Ca", "Na", "Mn"}:
        return stripped[:2].title()
    return stripped[0].upper()
