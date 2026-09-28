# 0.4 table of contents contract

Applies to the `0.4.0-r1` candidate, not a publication announcement. Pin the full
renderer identity and check its actual version: 0.3.3 does not understand this DSL.

The body remains a flat ordered `sections` array. TOC configuration never moves,
duplicates, removes, or renumbers body content, components, anchors, or assets.
With no `toc` table, legacy navigation and accordion behavior remain unchanged.
Any explicit section/component `toc` table (even `{}`) enables independent tree navigation.

| Location | Field | Default / meaning |
| --- | --- | --- |
| section `toc` | `parent` | Absent: root; otherwise an existing canonical section ID |
| section `toc` | `collapsed` | `false`: initially open; leaf nodes have no toggle |
| section `toc` | `title` | Body title; override with nonempty plain text in every declared language |
| component `toc` | `visible` | `true`; false excludes only the TOC entry |
| component `toc` | `title` | Original component title or built-in label; same language rules |

Section hiding is not supported: `sections.toc.visible` is rejected. Components
cannot declare `parent` or `collapsed`. Unknown TOC keys, invalid types and string
booleans fail validation. Collections copy their TOC policy to every expanded
component; row-level overrides are not part of this release.

See [the runnable minimal example](../examples/toc-minimal/report.toml) and the
[Chinese manual](toc.zh.md) for the equivalent nested-table and dotted-key syntax.
`migrate` writes dotted keys, preserving the nested localized title object.

Parents must be sections, not components or automatic renderer sections. Missing
parents, self-links, cycles and global anchor collisions fail. Collection expansion
is validated again. Existing ID normalization is retained; parent references must
use canonical IDs (prefer stable `[A-Za-z0-9_.-]` identifiers).
Reserved IDs are `top`, `report-guide`, `deliverables`, `provenance`,
`embedded-subreports-data`, `report-toc-data`, `image-modal-title`, and the `toc-branch-` prefix.
All declared section/component IDs also share a namespace with actual internal
IDs: code_file `ID-code`, tree_viewer `ID-newick`, sequence_alignment `ID-alignment`,
interactive_plot `ID-point-size-output`/`ID-opacity-output`, and structure_viewer
`ID-static` when static_image is set. validate-spec/lint reject collisions before
rendering, including after collection expansion. Unused suffixes are not reserved.
The maximum section depth is 64, with one further component level. Deep indentation
is capped to keep the sidebar usable.

Siblings follow body order. A parent may appear later in the body and branches may
be interleaved; tree traversal and total body order can therefore differ. Nothing
reorders the body. Prefer contiguous child sections when authoring a report.
Grouping sections with child sections but no components pass strict lint. A truly
empty leaf retains the legacy lint warning.

Text links navigate; separate buttons toggle descendants with Tab/Enter/Space.
Expand/collapse all only changes navigation. Deep links and browser history expand
all ancestors. Scroll highlighting observes body anchors, mapping an excluded
component to its visible owning section without restoring a hidden entry. Scrolling
does not close unrelated branches. Language and content-size changes refresh
positioning. The existing `#taffish-subreport=` route remains reserved for native
subreports. No CDN, service, search or persisted collapse state is introduced.
TOC state cannot hide print body content; full PDF pagination/font acceptance is
still a separate gate.

`explain --json` and `inspect-html --json` expose `toc`: mode, visible_count,
hidden_count and nodes with id, kind, parent, section_id, anchor, body_order,
visible, hidden_reason, title, title_source, collapsed, ancestors, depth, active_id.
Counts include automatic sections and hidden components and are not scientific
section/component counts. A component without an explicit title may have an empty
index title; its UI still uses the built-in component label.

The same index is embedded in HTML and written to `report_toc.json`; standalone
inspection needs no sidecar. `inspect-html --validate` checks unique actual anchors,
parent chains, depths, counts and tree-mode visible links. Flow-owned independent
expectations, asset hashes and real browser QA are still required.

For the synthetic 19-target / 190-window long report, from a source checkout:

```sh
PYTHONPATH=python python3 tests/toc_fixture.py --outdir NEW_FIXTURE_DIR
PYTHONPATH=python bin/report-render render --spec NEW_FIXTURE_DIR/report.toml \
  --root NEW_FIXTURE_DIR --out NEW_FIXTURE_DIR/output/report.html --validate
```

This fixture contains no customer data. Tests cover strict lint, semantic JSON/TOML
round-trip, legacy navigation, negative cases, unchanged body/assets, deep links,
bilingual desktop/narrow layouts, keyboard, history and print body preservation.
