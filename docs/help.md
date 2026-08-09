taffish-report-render 0.3.2-r1

Usage:
  taf-taffish-report-render COMMAND [OPTIONS]

Purpose:
  Build one standalone TAFFISH HTML report from:
    1. report.toml or report.manifest.json
    2. one local result root directory

Main idea:
  Write report structure in TOML.
  Put real result files under --root.
  Run render.

  No hand-written HTML, JavaScript, CSS, or extra report code is needed.

Fastest test:
  taf-taffish-report-render new --outdir report-example
  taf-taffish-report-render render --spec report-example/report.toml --root report-example --out report-example/04_reports/taffish_report.html --force --validate
  taf-taffish-report-render inspect-html report-example/04_reports/taffish_report.html --validate

Render your own results:
  Example result tree:
    my-run/
      03_results/...
      04_reports/report.toml

  Commands:
    taf-taffish-report-render lint --spec my-run/04_reports/report.toml --root my-run
    taf-taffish-report-render render --spec my-run/04_reports/report.toml --root my-run --out my-run/04_reports/taffish_report.html --force --validate
    taf-taffish-report-render inspect-html my-run/04_reports/taffish_report.html --validate

Commands:
  render          Compile a standalone HTML report.
  lint            Check spec paths, assets, i18n fields, and boundaries.
  explain         Preview sections, components, and referenced files.
  validate-spec   Check TOML/JSON structure.
  inspect-html    Check a rendered HTML report.
  validate-html   Check the standalone HTML contract.
  components      List fixed component types.
  component-doc   Show concise fields for one component.
  init            Print a minimal TOML starter.
  new             Create a runnable example workspace.
  schema          Print the JSON schema.
  migrate         Normalize TOML/JSON to canonical output.
  list-assets     List rendered report asset indexes.

Common components:
  dashboard_cards, table_preview, plot_card, interactive_plot,
  native_subreport, structure_viewer, genome_browser, tree_viewer,
  sequence_alignment, plot_collection, table_collection,
  code_file_collection, native_subreport_collection

Plot layouts:
  plot_card supports grid, wide, and responsive media layouts.
  media_note_layout auto keeps 0-3 note items stacked and compacts 4 or more.
  Compact media folds at component widths 900px and 620px.
  PNG, JPEG, WebP, and SVG use deterministic renderer-owned MIME mappings.
  See the component manual for validated media ratios and alignment fields.

Structured notes:
  Sections and every fixed component support note_items with validated kinds,
  bilingual labels, paragraphs, and plain-text lists. Markdown, HTML, CSS, and
  JavaScript are not parsed from report specs.

Path rule:
  All source/image/path values are relative to --root.
  Absolute paths and paths escaping --root are rejected.

Detailed manuals:
  https://github.com/taffish/taffish-report-render/blob/main/docs/report-spec.en.md
  https://github.com/taffish/taffish-report-render/blob/main/docs/components.en.md
  https://github.com/taffish/taffish-report-render/blob/main/docs/examples.en.md
  https://github.com/taffish/taffish-report-render/blob/main/docs/runtime-packs.en.md

Wrapper options:
  taf-taffish-report-render --help       Show this TAFFISH help.
  taf-taffish-report-render --version    Show TAFFISH wrapper version.
  taf-taffish-report-render --compile    Compile the TAFFISH wrapper.
  taf-taffish-report-render -- --version Pass an option-leading argument to report-render.

Notes:
  Non-option subcommands above go directly to the unified report-render CLI.
