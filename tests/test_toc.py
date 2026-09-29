"""目录 DSL、正文隔离、迁移、collection 与负向合同。"""
import json
import tempfile
import tomllib
import unittest
from copy import deepcopy
from pathlib import Path

from taffish_report_render.cli import (RenderError, validate_spec, normalize_spec, dump_toml_spec,
    report_json_schema, render_report, lint_spec, explain_manifest, validate_html_file)
from taffish_report_render.toc import build_toc_index, inspect_toc_html
from toc_fixture import make_spec, write_fixture, text


class TocTests(unittest.TestCase):
    def test_report_interaction_is_explicit_and_independent(self):
        for config, expected in ((None, "follow"), ({}, "follow"), ({"interaction": "follow"}, "follow"), ({"interaction": "manual"}, "manual")):
            spec = make_spec(1, 1)
            if config is not None: spec["toc"] = config
            validate_spec(spec)
            self.assertEqual(build_toc_index(normalize_spec(spec))["interaction"], expected)
            self.assertEqual(normalize_spec(tomllib.loads(dump_toml_spec(spec))), normalize_spec(spec))
            for section in spec["sections"]:
                section.pop("toc", None)
                for component in section["components"]: component.pop("toc", None)
            index = build_toc_index(normalize_spec(spec))
            self.assertEqual(index["interaction"], expected)
            self.assertEqual(index["mode"], "tree" if expected == "manual" else "legacy")
        schema = report_json_schema()
        self.assertFalse(schema["$defs"]["reportToc"]["additionalProperties"])
        self.assertEqual(schema["$defs"]["reportToc"]["properties"]["interaction"]["enum"], ["follow", "manual"])
        for config in (None, False, [], "manual", {"interaction": None}, {"interaction": []},
                       {"interaction": "tree"}, {"interaction": True}, {"interation": "follow"}, {"visible": False}):
            spec = make_spec(1, 1)
            spec["toc"] = config
            with self.subTest(config=config), self.assertRaises(RenderError): validate_spec(spec)

    def test_modes_have_identical_body_and_distinct_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            spec = write_fixture(root, 2, 2)
            follow, follow_ctx, _ = render_report(spec, root)
            self.assertNotIn('class="toc-toggle"', follow)
            self.assertNotIn('class="toc-controls"', follow)
            self.assertIn('data-toc-branch="positions"', follow)
            spec["toc"] = {"interaction": "manual"}
            manual, manual_ctx, _ = render_report(spec, root)
            self.assertIn('class="toc-toggle"', manual)
            self.assertIn('class="toc-controls"', manual)
            start, end = '<section class="section" id="overview"', '<section class="section" id="deliverables"'
            self.assertEqual(follow.split(start)[1].split(end)[0], manual.split(start)[1].split(end)[0])
            self.assertEqual([vars(a) for a in follow_ctx.assets], [vars(a) for a in manual_ctx.assets])
            for html, interaction in ((follow, "follow"), (manual, "manual")):
                self.assertEqual(inspect_toc_html(html, validate=True)["interaction"], interaction)
                with self.assertRaisesRegex(ValueError, "interaction"):
                    inspect_toc_html(html.replace(f'data-toc-interaction="{interaction}"', 'data-toc-interaction="bad"'), validate=True)
            # 0.4.0 的旧 v1 诊断索引仍可 inspect，不补写新的交互配置。
            import re
            old_index = inspect_toc_html(manual)
            old_index["version"] = 1
            del old_index["interaction"]
            old_html = re.sub(r'(<script[^>]+id="report-toc-data"[^>]*>)(.*?)(</script>)',
                              lambda m: m[1] + json.dumps(old_index) + m[3], manual, flags=re.S)
            old_html = old_html.replace(' data-toc-interaction="manual"', '')
            self.assertEqual(inspect_toc_html(old_html, validate=True), old_index)

    def test_roundtrip_and_schema(self):
        spec = make_spec(2, 2)
        validate_spec(spec)
        self.assertEqual(normalize_spec(tomllib.loads(dump_toml_spec(spec))), normalize_spec(spec))
        normalized = normalize_spec(spec)
        self.assertEqual(normalize_spec(tomllib.loads(dump_toml_spec(normalized))), normalized)
        schema = report_json_schema()
        self.assertFalse(schema["$defs"]["sectionToc"]["additionalProperties"])
        self.assertEqual(schema["$defs"]["sectionToc"]["properties"]["title"]["$ref"], "#/$defs/tocI18nText")
        self.assertNotIn("required", schema["$defs"]["tocI18nText"])
        for name in ("plot_card", "table_preview", "sequence_alignment", "code_file_collection"):
            self.assertIn("toc", schema["$defs"][name]["properties"])
        spec["languages"], spec["language_default"] = ["en"], "en"
        for section in spec["sections"]:
            if "title" in section.get("toc", {}): section["toc"]["title"].pop("zh")
            for c in section["components"]:
                if "title" in c.get("toc", {}): c["toc"]["title"].pop("zh")
        validate_spec(spec)
        self.assertEqual(normalize_spec(tomllib.loads(dump_toml_spec(spec))), normalize_spec(spec))

    def test_invalid_contracts(self):
        for toc in ({"parent": "missing"}, {"parent": "positions"}, {"visible": False}, {"collpased": True},
                    {"collapsed": "true"}, {"title": {"zh": "缺英文"}}, {"title": {"zh": [], "en": "x"}}, None):
            with self.subTest(toc=toc):
                spec = make_spec(1, 1)
                spec["sections"][1]["toc"] = toc
                with self.assertRaises(RenderError): validate_spec(spec)
        spec = make_spec(1, 1)
        spec["sections"][1]["toc"]["parent"] = "focused_targets"
        with self.assertRaisesRegex(RenderError, "cycle"): validate_spec(spec)
        for toc in ({"visible": "false"}, {"parent": "positions"}, {"collapsed": False}, {"visble": False}):
            spec = make_spec(1, 1)
            spec["sections"][0]["components"][0]["toc"] = toc
            with self.assertRaises(RenderError): validate_spec(spec)

    def test_global_anchor_collisions(self):
        for ident in ("overview", "top", "report-guide", "report-toc-data", "image-modal-title", "toc-branch-foo"):
            spec = make_spec(1, 1)
            spec["sections"][0]["components"][0]["id"] = ident
            with self.assertRaises(RenderError): validate_spec(spec)
        spec = make_spec(1, 1)
        spec["sections"][-1]["id"] = "overview"
        with self.assertRaises(RenderError): validate_spec(spec)

    def test_derived_anchor_collisions_before_render(self):
        from taffish_report_render.anchors import component_child_anchors
        from taffish_report_render.cli import slug
        from taffish_report_render.toc import validate_toc
        for ctype, extra in (("code_file", {}), ("tree_viewer", {}), ("sequence_alignment", {}),
                             ("interactive_plot", {}), ("structure_viewer", {"static_image": "score.svg"})):
            component = {"id": "methods", "type": ctype, **extra}
            for child in component_child_anchors("methods", component):
                for reverse in (False, True):
                    for as_section in (False, True):
                        spec = make_spec(1, 1)
                        spec["sections"][0]["components"] = [component]
                        other = {"id": child, "title": text("碰撞", "Collision"), "components": []}
                        if not as_section:
                            other = {"id": "safe-section", "title": text("章", "Section"), "components": [{"id": child, "type": "code_file"}]}
                        spec["sections"] = [spec["sections"][0], other]
                        if reverse: spec["sections"].reverse()
                        with self.subTest(ctype=ctype, child=child, reverse=reverse, as_section=as_section):
                            with self.assertRaisesRegex(ValueError, "duplicate or reserved anchor"):
                                validate_toc(spec, slug, ["en", "zh"])
        # Public validation/lint/render all fail before reading any asset, with or without TOC.
        for toc in (True, False):
            for ident in ("methods-code", "image-modal-title", "methods code"):
                spec = make_spec(1, 1)
                spec["sections"][0]["components"][0]["id"] = "methods"
                spec["sections"][2]["components"][0]["id"] = ident
                if not toc:
                    for s in spec["sections"]:
                        s.pop("toc", None)
                        for c in s["components"]: c.pop("toc", None)
                with self.assertRaisesRegex(RenderError, "duplicate or reserved anchor"): validate_spec(spec)
                issues, _ = lint_spec(spec, strict=True)
                self.assertTrue(any(i.severity == "error" and "anchor" in i.message for i in issues))
                with self.assertRaisesRegex(RenderError, "duplicate or reserved anchor"):
                    render_report(spec, Path("/nonexistent-fixture"))

    def test_internal_ids_remain_stable_and_unique(self):
        from taffish_report_render.toc import TocHTMLParser
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            spec = write_fixture(root, 1, 1)
            html, _, _ = render_report(spec, root)
            parser = TocHTMLParser()
            parser.feed(html)
            self.assertTrue(all(n == 1 for n in parser.ids.values()))
            for ident in ("intro-text-code", "candidate_01_window_01-alignment", "image-modal-title"):
                self.assertEqual(parser.ids[ident], 1)
            # Duplicate an internal ID, not a section/component index entry.
            with self.assertRaisesRegex(ValueError, "duplicate HTML anchor"):
                inspect_toc_html(html.replace("</body>", '<span id="intro-text-code"></span></body>'), validate=True)

    def test_content_unchanged_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            spec = write_fixture(root, 2, 2)
            original = deepcopy(spec)
            html, ctx, manifest = render_report(spec, root)
            index = inspect_toc_html(html, validate=True)
            self.assertEqual(spec, original)
            node = next(n for n in index["nodes"] if n["id"] == "candidate_01_window_01")
            self.assertFalse(node["visible"])
            self.assertEqual(node["active_id"], "candidate_01")
            self.assertEqual(node["ancestors"], ["positions", "focused_targets", "candidate_01"])
            self.assertEqual(index, explain_manifest(manifest)["toc"])
            self.assertIn('id="candidate_01_window_01"', html)
            self.assertNotIn('href="#candidate_01_window_01"', html)
            self.assertNotIn('<details class="nav-group">', html)
            legacy = deepcopy(spec)
            for section in legacy["sections"]:
                section.pop("toc", None)
                for c in section["components"]: c.pop("toc", None)
            old_html, old_ctx, _ = render_report(legacy, root)
            self.assertIn('<details class="nav-group">', old_html)
            # 只对业务正文比较，排除版本/诊断/目录；组件资源字节与顺序完全相同。
            start = '<section class="section" id="overview"'
            end = '<section class="section" id="deliverables"'
            self.assertEqual(html.split(start)[1].split(end)[0], old_html.split(start)[1].split(end)[0])
            self.assertEqual([vars(a) for a in ctx.assets], [vars(a) for a in old_ctx.assets])
            issues, _ = lint_spec(spec, root=root, strict=True)
            self.assertEqual(issues, [])

    def test_empty_leaf_long_title_and_escaping(self):
        spec = make_spec(1, 1)
        spec["sections"].append({"id": "empty", "title": text("空章", "Empty"), "toc": {"parent": "positions", "collapsed": True}})
        spec["sections"][1]["toc"]["title"] = text('</script><img onerror="bad()">', "<script>bad()</script>")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            write_fixture(root, 1, 1)
            html, _, _ = render_report(spec, root)
            self.assertIn("&lt;script&gt;bad()&lt;/script&gt;", html)
            self.assertNotIn('<script>bad()</script>', html)
            self.assertNotIn('data-toc-toggle="empty"', html)
            inspect_toc_html(html, validate=True)

    def test_collection_policy_and_collision_after_expansion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            spec = write_fixture(root, 1, 1)
            (root / "files.tsv").write_text("id\tsource\nfirst\tmethods.txt\n")
            spec["sections"][0]["components"] = [{"id": "files", "type": "code_file_collection", "source": "files.tsv", "toc": {"visible": False}}]
            norm = normalize_spec(spec, root)
            validate_spec(norm, allow_collections=False)
            self.assertEqual(norm["sections"][0]["components"][0]["toc"], {"visible": False})
            spec["sections"][1]["id"] = "files-first"
            spec["sections"][2]["toc"]["parent"] = "files-first"
            spec["sections"][3]["toc"]["parent"] = "files-first"
            spec["sections"][-1]["toc"]["parent"] = "files-first"
            with self.assertRaisesRegex(RenderError, "duplicate"):
                validate_spec(normalize_spec(spec, root), allow_collections=False)
            spec["sections"][1]["id"] = "files-first-code"
            for s in spec["sections"]:
                if s.get("toc", {}).get("parent") == "files-first": s["toc"]["parent"] = "files-first-code"
            with self.assertRaisesRegex(RenderError, "duplicate"):
                validate_spec(normalize_spec(spec, root), allow_collections=False)

    def test_empty_collection_keeps_tree_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "files.tsv").write_text("id\tsource\n")
            spec = {"project": {"title": text("空", "Empty")}, "sections": [{"id": "s", "title": text("章", "Chapter"),
                "components": [{"id": "files", "type": "code_file_collection", "source": "files.tsv", "toc": {}}]}]}
            normalized = normalize_spec(spec, root)
            self.assertEqual(build_toc_index(normalized)["mode"], "tree")
            self.assertEqual(normalized["sections"][0]["components"], [])

    def test_html_fault_injection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "input"
            spec = write_fixture(root, 1, 1)
            html, _, _ = render_report(spec, root)
            for broken in (html.replace('id="candidate_01_window_01"', 'id="removed"', 1),
                           html.replace('href="#candidate_01"', 'href="#wrong"', 1),
                           html.replace('id="report-toc-data"', 'id="missing-index"', 1)):
                with self.assertRaises(ValueError): inspect_toc_html(broken, validate=True)
            import re
            pattern = r'(<script[^>]+id="report-toc-data"[^>]*>)(.*?)(</script>)'
            for field, value in (("active_id", "positions"), ("visible", "false"), ("body_order", -1), ("kind", "bogus")):
                index = inspect_toc_html(html)
                next(n for n in index["nodes"] if n["id"] == "candidate_01_window_01")[field] = value
                broken = re.sub(pattern, lambda m: m[1] + json.dumps(index) + m[3], html, flags=re.S)
                with self.assertRaises(ValueError): inspect_toc_html(broken, validate=True)
            from taffish_report_render.cli import html_summary
            path = root / "bad.html"
            path.write_text(re.sub(pattern, lambda m: m[1] + "{bad" + m[3], html, flags=re.S))
            with self.assertRaises(RenderError): html_summary(path)

    def test_source_order_and_depth_limit(self):
        spec = make_spec(1, 1)
        spec["sections"].reverse()
        validate_spec(spec)
        index = build_toc_index(normalize_spec(spec))
        self.assertEqual([n["id"] for n in index["nodes"] if n["kind"] == "section"], [s["id"] for s in spec["sections"]])
        spec["sections"] = [{"id": f"s{i}", "title": text("章", "Chapter"), "toc": {"parent": f"s{i-1}"} if i else {}} for i in range(65)]
        with self.assertRaisesRegex(RenderError, "depth"): validate_spec(spec)


if __name__ == "__main__": unittest.main()
