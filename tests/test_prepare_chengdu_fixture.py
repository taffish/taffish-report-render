import base64
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
HELPER = APP_ROOT / "tools" / "prepare-chengdu-yuanda-report12-fixture.py"
PREFIX = "pufa_structure_comparison_all_domains"


class ChengduFixturePreparationTests(unittest.TestCase):
    def write_source(self, root: Path) -> None:
        results = root / "03_results"
        reports = root / "04_reports"
        overlay = results / "overlay_pdb" / "target_fixture_domain_1"
        display = results / "structure_figures_display"
        overlay.mkdir(parents=True)
        display.mkdir(parents=True)
        reports.mkdir(parents=True)

        generic = "metric\tvalue\nfixture\t1\n"
        tables = {
            f"{PREFIX}.domain_differentiation_data_rank.tsv": generic,
            f"{PREFIX}.domain_differentiation_mechanism_candidates.tsv": generic,
            f"{PREFIX}.domain_differentiation_summary.tsv": generic,
            f"{PREFIX}.figure_files.pre_pymol.tsv": "figure_type\tpath\nsummary\t/absolute/source/03_results/figures/summary.png\n",
            f"{PREFIX}.figure_files.tsv": "figure_type\tpath\nsummary\t/absolute/source/03_results/figures/summary.png\n",
            f"{PREFIX}.foldseek_structural_similarity.raw.tsv": "query\ttarget\talntmscore\tfident\trmsd\ntarget_fixture_domain_1\tEPA_fixture\t0.9\t0.4\t1.2\n",
            f"{PREFIX}.foldseek_structural_similarity.tsv": "query\ttarget\talntmscore\tfident\trmsd\ntarget_fixture_domain_1\tEPA_fixture\t0.9\t0.4\t1.2\n",
            f"{PREFIX}.local_motif_structural_similarity.tsv": "comparison_group\tmotif_window_rmsd\tmotif_site_rmsd\nfixture_group\t1.1\t1.3\n",
            f"{PREFIX}.motif_sites_on_target.tsv": "structure_id\tstructure_residue\ttarget_state\ttarget_residue_label\ntarget_fixture_domain_1\t12\ttarget_matches_DHA\tA12\n",
            f"{PREFIX}.overlay_priority_summary.tsv": generic,
            f"{PREFIX}.selected_structures.tsv": "structure_id\trole\ntarget_fixture_domain_1\ttarget\nEPA_fixture\tEPA\nDHA_fixture\tDHA\n",
            f"{PREFIX}.selection_summary.tsv": generic,
            f"{PREFIX}.structure_quality.tsv": "structure_id\trole\tmean_plddt\tpdb_path\ntarget_fixture_domain_1\ttarget\t91.5\t/absolute/source/03_results/pdb/target.pdb\nEPA_fixture\tEPA\t88.0\t/absolute/source/03_results/pdb/epa.pdb\nDHA_fixture\tDHA\t87.0\t/absolute/source/03_results/pdb/dha.pdb\n",
            f"{PREFIX}.target_local_motif_preference.tsv": "target_structure_id\tEPA_minus_DHA_site_rmsd\ntarget_fixture_domain_1\t1.4\n",
        }
        manifest_rows = [
            ("target", "target_fixture_domain_1", "target | fixture", "target.pdb", "#2b2f33"),
            ("EPA", "EPA_fixture", "EPA | fixture", "epa_EPA_fixture.aligned.pdb", "#0b84a5"),
            ("DHA", "DHA_fixture", "DHA | fixture", "dha_DHA_fixture.aligned.pdb", "#8b5cf6"),
        ]
        manifest = "overlay_id\tmodel_role\ttarget_structure_id\tstructure_id\tlabel\tpdb_path\tcolor\talignment_group\tpaired_ca_count\n"
        for role, structure, label, filename, color in manifest_rows:
            manifest += f"target_fixture_domain_1\t{role}\ttarget_fixture_domain_1\t{structure}\t{label}\t/absolute/source/03_results/overlay_pdb/target_fixture_domain_1/{filename}\t{color}\tfixture_group\t12\n"
            (overlay / filename).write_text("ATOM      1  CA  ALA A   1       0.000   0.000   0.000  1.00 90.00           C\nEND\n", encoding="utf-8")
        tables[f"{PREFIX}.overlay_pdb_manifest.tsv"] = manifest
        for name, content in tables.items():
            (results / name).write_text(content, encoding="utf-8")

        png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        (display / f"{PREFIX}.target_fixture_domain_1.target_epa_dha_overlay.display.png").write_bytes(png)
        (reports / "flow_summary.tsv").write_text("metric\tvalue\nstatus\tcomplete\n", encoding="utf-8")
        (reports / "versions.tsv").write_text("tool\tversion\nfixture\t1\n", encoding="utf-8")
        (reports / "methods.txt").write_text("Synthetic miniature input for the deterministic fixture-preparation unit test.\n", encoding="utf-8")

    def run_helper(self, source: Path, outdir: Path) -> None:
        subprocess.run(
            [
                sys.executable,
                str(HELPER),
                "--source-root",
                str(source),
                "--outdir",
                str(outdir),
                "--expected-overlay-groups",
                "1",
            ],
            check=True,
            text=True,
            capture_output=True,
        )

    def test_preparation_is_relative_and_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "raw"
            first = root / "first"
            second = root / "second"
            self.write_source(source)
            self.run_helper(source, first)
            self.run_helper(source, second)

            first_files = sorted(path.relative_to(first) for path in first.rglob("*") if path.is_file())
            second_files = sorted(path.relative_to(second) for path in second.rglob("*") if path.is_file())
            self.assertEqual(first_files, second_files)
            for relative in first_files:
                self.assertEqual((first / relative).read_bytes(), (second / relative).read_bytes(), relative)

            report_toml = (first / "report.toml").read_text(encoding="utf-8")
            self.assertIn("Chengdu Yuanda PUFA Structure Comparison Report 12", report_toml)
            self.assertIn('runtime = "ngl"', report_toml)
            self.assertNotIn(str(root), report_toml)
            sanitized = (first / "03_results" / "tables" / f"{PREFIX}.structure_quality.tsv").read_text(encoding="utf-8")
            self.assertNotIn("/absolute/source", sanitized)
            self.assertIn("03_results/pdb/target.pdb", sanitized)
            receipt = json.loads((first / "fixture-preparation.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt["expected_overlay_groups"], 1)
            self.assertGreater(len(receipt["input_files"]), 10)
            self.assertGreater(len(receipt["output_files"]), 10)


if __name__ == "__main__":
    unittest.main()
