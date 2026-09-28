"""确定性的目录模型；不修改正文、资产或源 spec。"""

from __future__ import annotations

import json
from collections import Counter
from html.parser import HTMLParser
from typing import Any, Callable
from .anchors import FIXED_IDS, component_child_anchors

MAX_DEPTH = 64
RESERVED_IDS = FIXED_IDS
AUTOMATIC_TITLES = {
    "report-guide": {"en": "How to Read", "zh": "如何阅读"},
    "deliverables": {"en": "Deliverables", "zh": "交付文件"},
    "provenance": {"en": "Provenance", "zh": "溯源信息"},
}


def validate_toc(spec: dict, slug: Callable[[str], str], languages: list[str]) -> None:
    sections = spec["sections"]
    section_ids = [slug(str(s.get("id") or f"section-{i}")) for i, s in enumerate(sections, 1)]
    ids: set[str] = set()
    parents = {}
    for sid, section in zip(section_ids, sections):
        owners = [(sid, section, True)] + [
            (slug(str(c.get("id") or f"{sid}-{c.get('type')}-{i}")), c, False)
            for i, c in enumerate(section.get("components", []), 1)
        ]
        for ident, owner, is_section in owners:
            owned_ids = [ident] + ([] if is_section else component_child_anchors(ident, owner))
            for anchor in owned_ids:
                if anchor in ids or anchor in RESERVED_IDS or anchor.startswith("toc-branch-"):
                    raise ValueError(f"duplicate or reserved anchor id: {anchor} (owner: {ident})")
                ids.add(anchor)
            if "toc" not in owner:
                continue
            toc = owner["toc"]
            if not isinstance(toc, dict):
                raise ValueError(f"{ident}.toc must be a table")
            allowed = {"parent", "collapsed", "title"} if is_section else {"visible", "title"}
            unknown = sorted(set(toc) - allowed)
            if unknown:
                raise ValueError(f"{ident}.toc has unknown or unsupported fields: {', '.join(unknown)}")
            for key in ("collapsed", "visible"):
                if key in toc and not isinstance(toc[key], bool):
                    raise ValueError(f"{ident}.toc.{key} must be a boolean")
            if "title" in toc:
                title = toc["title"]
                if not isinstance(title, dict) or any(not isinstance(v, str) or not v.strip() for v in title.values()):
                    raise ValueError(f"{ident}.toc.title must contain non-empty language strings")
                if any(lang not in title for lang in languages):
                    raise ValueError(f"{ident}.toc.title must contain every declared language")
            if "parent" in toc:
                parent = toc["parent"]
                if not isinstance(parent, str) or not parent or parent != slug(parent) or parent not in section_ids:
                    raise ValueError(f"{ident}.toc.parent must reference an existing canonical section id")
                parents[ident] = parent
    for sid in section_ids:
        visited = {sid}
        node = sid
        while node in parents:
            node = parents[node]
            if node in visited:
                raise ValueError(f"toc parent cycle or self-reference involving {sid}")
            visited.add(node)
            if len(visited) > MAX_DEPTH:
                raise ValueError(f"toc section depth exceeds {MAX_DEPTH}")


def build_toc_index(manifest: dict) -> dict[str, Any]:
    sections = manifest["sections"]
    mode = "tree" if any("toc" in s or any("toc" in c for c in s.get("components", [])) for s in sections) else "legacy"
    nodes: list[dict] = []

    def add(ident: str, kind: str, parent: str | None, owner: dict, section_id: str | None) -> None:
        toc = owner.get("toc", {})
        nodes.append({
            "id": ident, "kind": kind, "parent": parent, "section_id": section_id,
            "anchor": "#" + ident, "body_order": len(nodes),
            "visible": toc.get("visible", True),
            "hidden_reason": "explicit_visible_false" if toc.get("visible") is False else None,
            "title": toc.get("title", owner.get("title", {})),
            "title_source": "toc.title" if "title" in toc else "title",
            "collapsed": toc.get("collapsed", False),
        })

    add("report-guide", "automatic", None, {"title": AUTOMATIC_TITLES["report-guide"]}, None)
    for s in sections:
        sid = s["id"]
        add(sid, "section", s.get("toc", {}).get("parent"), s, sid)
        for c in s.get("components", []):
            add(c["id"], "component", sid, c, sid)
    for ident in ("deliverables", "provenance"):
        add(ident, "automatic", None, {"title": AUTOMATIC_TITLES[ident]}, None)
    by_id = {n["id"]: n for n in nodes}
    for node in nodes:
        ancestors = []
        parent = node["parent"]
        while parent:
            ancestors.append(parent)
            parent = by_id[parent]["parent"]
        node["ancestors"] = list(reversed(ancestors))
        node["depth"] = len(ancestors) + 1
        node["active_id"] = node["id"] if node["visible"] else node["section_id"]
    return {"version": 1, "mode": mode, "nodes": nodes,
            "visible_count": sum(n["visible"] for n in nodes),
            "hidden_count": sum(not n["visible"] for n in nodes)}


def render_toc(index: dict, titles: dict[str, str], label: Callable[[str, str], str]) -> str:
    """titles 已由调用方进行双语与 HTML 转义；ID 只使用已校验的 canonical slug。"""
    children: dict[str | None, list[dict]] = {}
    for node in index["nodes"]:
        if node["visible"]:
            children.setdefault(node["parent"], []).append(node)

    def render_children(parent: str | None) -> str:
        parts = []
        for node in children.get(parent, []):
            ident = node["id"]
            link = f'<a href="#{ident}" data-toc-link="{ident}">{titles[ident]}</a>'
            if children.get(ident):
                opened = not node["collapsed"]
                button = (f'<button type="button" class="toc-toggle" data-toc-toggle="{ident}" '
                          f'aria-expanded="{str(opened).lower()}" aria-controls="toc-branch-{ident}">'
                          f'<span aria-hidden="true">▸</span><span class="toc-sr-only">'
                          f'{label("Toggle subsections", "展开或收起子目录")}: {titles[ident]}</span></button>')
                body = f'<ul id="toc-branch-{ident}"{ "" if opened else " hidden"}>{render_children(ident)}</ul>'
            else:
                button, body = "", ""
            parts.append(f'<li data-toc-node="{ident}"><div class="toc-row">{link}{button}</div>{body}</li>')
        return "".join(parts)

    controls = ('<div class="toc-controls">'
                f'<button type="button" data-toc-all="expand">{label("Expand all", "全部展开")}</button>'
                f'<button type="button" data-toc-all="collapse">{label("Collapse all", "全部收起")}</button></div>')
    return controls + '<ul class="toc-tree">' + render_children(None) + '</ul>'


class TocHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: Counter[str] = Counter()
        self.links: dict[str, str] = {}
        self.payload: list[str] = []
        self.in_payload = False
        self.mode = None

    def handle_starttag(self, tag: str, attrs: list) -> None:
        data = dict(attrs)
        if data.get("id"):
            self.ids[data["id"]] += 1
        if "data-toc-mode" in data:
            self.mode = data["data-toc-mode"]
        if "data-toc-link" in data:
            if data["data-toc-link"] in self.links:
                raise ValueError("duplicate toc link")
            self.links[data["data-toc-link"]] = data.get("href", "")
        if tag == "script" and data.get("id") == "report-toc-data":
            self.in_payload = True

    def handle_data(self, data: str) -> None:
        if self.in_payload:
            self.payload.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.in_payload = False


def inspect_toc_html(html: str, validate: bool = False) -> dict | None:
    parser = TocHTMLParser()
    parser.feed(html)
    if not parser.payload:
        if validate and parser.mode is not None:
            raise ValueError("missing embedded toc index")
        return None  # 兼容旧版 standalone HTML。
    index = json.loads("".join(parser.payload))
    if not isinstance(index, dict) or not isinstance(index.get("nodes"), list):
        raise ValueError("toc index must be an object with a nodes array")
    if validate:
        duplicates = sorted(ident for ident, count in parser.ids.items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate HTML anchor ids: {', '.join(duplicates)}")
        nodes = index["nodes"]
        if index.get("version") != 1 or index.get("mode") not in {"tree", "legacy"}:
            raise ValueError("unsupported toc index version/mode")
        if any(not isinstance(n, dict) or not isinstance(n.get("id"), str) for n in nodes):
            raise ValueError("invalid toc node")
        by_id = {n["id"]: n for n in nodes}
        if len(by_id) != len(nodes) or index["mode"] != parser.mode:
            raise ValueError("toc index identity mismatch")
        for order, node in enumerate(nodes):
            ident = node["id"]
            kind = node.get("kind")
            if kind not in {"section", "component", "automatic"} or node.get("body_order") != order:
                raise ValueError(f"invalid toc kind/order: {ident}")
            if type(node.get("visible")) is not bool or type(node.get("collapsed")) is not bool:
                raise ValueError(f"invalid toc boolean: {ident}")
            if kind != "component" and not node["visible"]:
                raise ValueError(f"only components can be hidden: {ident}")
            expected_active = ident if node["visible"] else node["section_id"]
            expected_reason = None if node["visible"] else "explicit_visible_false"
            if node.get("active_id") != expected_active or node.get("hidden_reason") != expected_reason:
                raise ValueError(f"invalid toc visibility mapping: {ident}")
            if kind == "automatic" and (ident not in AUTOMATIC_TITLES or node["parent"] is not None or node["section_id"] is not None):
                raise ValueError(f"invalid automatic toc node: {ident}")
            if kind == "section" and node["section_id"] != ident:
                raise ValueError(f"invalid toc section owner: {ident}")
            if kind == "component" and (not node["parent"] or node["parent"] != node["section_id"] or node["collapsed"]):
                raise ValueError(f"invalid toc component owner: {ident}")
            if parser.ids[ident] != 1 or node["anchor"] != "#" + ident:
                raise ValueError(f"toc anchor missing or duplicated: {ident}")
            ancestors = []
            parent = node["parent"]
            while parent:
                if not isinstance(parent, str) or parent == ident or parent in ancestors or parent not in by_id:
                    raise ValueError(f"invalid toc parent chain: {ident}")
                if by_id[parent]["kind"] != "section":
                    raise ValueError(f"toc parent is not a section: {ident}")
                ancestors.append(parent)
                parent = by_id[parent]["parent"]
            if len(ancestors) + 1 > MAX_DEPTH + (kind == "component"):
                raise ValueError(f"toc depth exceeds limit: {ident}")
            if node["ancestors"] != list(reversed(ancestors)) or node["depth"] != len(ancestors) + 1:
                raise ValueError(f"toc depth/ancestors mismatch: {ident}")
        visible = {n["id"]: n["anchor"] for n in nodes if n["visible"]}
        if index["visible_count"] != len(visible) or index["hidden_count"] != len(nodes) - len(visible):
            raise ValueError("toc counts mismatch")
        if index["mode"] == "tree" and parser.links != visible:
            raise ValueError("toc DOM links disagree with visibility/anchors")
    return index
