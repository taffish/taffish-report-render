# 0.4.1 table of contents and reading compatibility

Applies to the `0.4.1-r1` candidate, not a publication announcement. Pin the full
renderer identity and check its actual version: 0.3.3 does not understand this DSL.

The body remains a flat ordered `sections` array. TOC configuration never moves,
duplicates, removes, or renumbers body content, components, anchors, or assets.
By default, ordinary scrolling opens the current reading path and closes unrelated
branches, retaining the 0.3 reading experience. With no node `toc` table, the legacy
two-level appearance is retained. Node fields (even an empty table) select structure,
not interaction: hierarchical navigation also follows reading by default, without
separate triangle buttons or an expand/collapse-all toolbar. Root entries remain present.

| Location | Field | Default / meaning |
| --- | --- | --- |
| report root `toc` | `interaction` | `"follow"` (default) or `"manual"` |
| section `toc` | `parent` | Absent: root; otherwise an existing canonical section ID |
| section `toc` | `collapsed` | `false`: initial HTML/manual state; the current reading path takes priority in follow mode |
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

In default follow mode, Tab/Enter navigate text links. Current entries have
`aria-current`; branch links have `aria-expanded`/`aria-controls`. Ordinary scrolling
opens the full current ancestor path and closes unrelated branches without navigating
the body, changing the hash or stealing focus. A branch containing keyboard focus is
temporarily kept open until focus leaves. The reading path overrides `collapsed`;
this is neither initially opening the entire tree nor click-only expansion.
The desktop sticky sidebar scrolls only itself when needed to reveal the active
entry; this does not scroll the narrow-screen body or interfere with TOC keyboard focus.
On narrow screens the TOC sits above the body. Position tracking uses body-relative
anchors and the body's live position, so folding cannot leave stale absolute coordinates.
If native scroll anchoring leaves a layout shift, one immediate document-offset
compensation preserves the visible body's position. There is no section jump,
smooth scrolling, correction loop, or reliance on size observers to detect translation.

Explicit manual mode retains 0.4.0 separate fold buttons (Tab/Enter/Space) and the
bulk toolbar, even without any node fields. Scrolling highlights without changing
manual state. In both modes deep links and history expand all ancestors. Hidden
components map to their visible owning section without restoring hidden entries.
Language and content-size changes refresh positioning.
The existing `#taffish-subreport=` route remains reserved for native
subreports. No CDN, service, search or persisted collapse state is introduced.
TOC state cannot hide print body content; full PDF pagination/font acceptance is
still a separate gate.

## Upgrading from 0.4.0

Existing node fields remain valid without rewriting the hierarchy. The new default
is intentionally reading-follow. To retain 0.4.0 manual behavior, add at the report
root (not inside a section):

```toml
[toc]
interaction = "manual"
```

Use `"follow"` to explicitly pin the default. Unknown keys, invalid types and
unsupported values fail validation; no automatic numbering is introduced.

## Diagnostics and verification

`explain --json` and `inspect-html --json` expose `toc`: version=2, mode, interaction, visible_count,
hidden_count and nodes with id, kind, parent, section_id, anchor, body_order,
visible, hidden_reason, title, title_source, collapsed, ancestors, depth, active_id.
Counts include automatic sections and hidden components and are not scientific
section/component counts. A component without an explicit title may have an empty
index title; its UI still uses the built-in component label.
`mode` remains the structural classification `legacy`/`tree`; `interaction` is
`follow`/`manual`. Inspection still accepts old v1 indexes and pre-0.4 HTML without
inventing new configuration. Version 2 also checks HTML/index interaction identity.

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
`tests/prepare-toc-browser.py` prepares separate follow/manual, legacy, hide-only,
short-title-only and empty-table cases. `tests/browser-follow.cjs` tests real wheel
reading; `tests/browser-toc.cjs` tests explicit manual mode independently.
