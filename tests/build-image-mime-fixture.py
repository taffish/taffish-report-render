#!/usr/bin/env python3
"""Build real-image smoke and fungal-equivalent MIME regression fixtures."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path


PNG = "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACAQMAAABIeJ9nAAAAA1BMVEULj4IUgrSzAAAADElEQVQI12NgYGAAAAAEAAEnNCcKAAAAAElFTkSuQmCC"
JPEG = "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAMCAgICAgMCAgIDAwMDBAYEBAQEBAgGBgUGCQgKCgkICQkKDA8MCgsOCwkJDRENDg8QEBEQCgwSExIQEw8QEBD/2wBDAQMDAwQDBAgEBAgQCwkLEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBD/wAARCAACAAIDAREAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAABv/EABQQAQAAAAAAAAAAAAAAAAAAAAD/xAAVAQEBAAAAAAAAAAAAAAAAAAAHCP/EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhEDEQA/AFaJz2//2Q=="
WEBP = "UklGRjYAAABXRUJQVlA4ICoAAACQAQCdASoCAAIAAgA0JaACdLoAA5gA/u+9V/4hzoc6HL/361MjHz7gAAA="

SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 120" role="img" aria-label="Scientific MIME fixture">
  <rect width="240" height="120" fill="#f6fbfa"/>
  <path d="M22 92 L72 58 L122 76 L172 31 L218 48" fill="none" stroke="#0f8a7a" stroke-width="7"/>
  <circle cx="72" cy="58" r="7" fill="#f2b84b"/><circle cx="172" cy="31" r="7" fill="#f2b84b"/>
</svg>
"""


def write_binary(path: Path, encoded: str) -> None:
    path.write_bytes(base64.b64decode(encoded))


def write_images(root: Path, profile: str) -> list[tuple[str, str, str]]:
    figures = root / "03_results" / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    if profile == "core":
        assets = [
            ("image-png.png", "PNG scientific panel", "PNG 科研图"),
            ("image-jpeg.jpg", "JPEG scientific panel", "JPEG 科研图"),
            ("image-webp.webp", "WebP literature panel", "WebP 文献图"),
            ("image-svg.svg", "SVG vector panel", "SVG 矢量图"),
        ]
    else:
        assets = [
            ("genome-overview.png", "Genome overview", "基因组概览"),
            ("compartment-summary.png", "Compartment summary", "区室汇总"),
            ("workflow.svg", "Workflow", "分析流程"),
            ("chromosome-map.svg", "Chromosome map", "染色体图谱"),
            ("gene-density.svg", "Gene density", "基因密度"),
            ("repeat-density.svg", "Repeat density", "重复序列密度"),
            ("sonah-2016-figure-1.webp", "SoNaH 2016 literature figure", "SoNaH 2016 文献图"),
        ]

    for index, (name, _title_en, _title_zh) in enumerate(assets):
        path = figures / name
        suffix = path.suffix.lower()
        if suffix == ".png":
            write_binary(path, PNG)
        elif suffix in {".jpg", ".jpeg"}:
            write_binary(path, JPEG)
        elif suffix == ".webp":
            write_binary(path, WEBP)
        elif suffix == ".svg":
            path.write_text(SVG.replace("Scientific MIME fixture", f"Scientific MIME fixture {index + 1}"), encoding="utf-8")
    return assets


def build_spec(root: Path, spec: Path, profile: str, assets: list[tuple[str, str, str]]) -> None:
    title_en = "Core image MIME regression" if profile == "core" else "Fungal report equivalent MIME regression"
    title_zh = "核心图片 MIME 回归" if profile == "core" else "真菌报告等价 MIME 回归"
    lines = [
        'schema_version = "0.1"',
        'template = "taffish-flow-report"',
        'language_default = "zh"',
        "",
        "[project]",
        'flow_name = "taffish-report-render"',
        'flow_version = "0.3.1-r1"',
        f'analysis_mode = "image-mime-{profile}"',
        f'title.en = "{title_en}"',
        f'title.zh = "{title_zh}"',
        'subtitle.en = "Real PNG, JPEG, WebP and SVG bytes are embedded into one offline report."',
        'subtitle.zh = "将真实 PNG、JPEG、WebP 与 SVG 字节内嵌到同一份离线报告中。"',
        "",
        "[[sections]]",
        'id = "image-contract"',
        'kind = "results"',
        'title.en = "1. Image MIME contract"',
        'title.zh = "1. 图片 MIME 契约"',
        'note.en = "Every declared scientific image must retain its exact image MIME in the standalone HTML."',
        'note.zh = "每张声明的科研图片在 standalone HTML 中都必须保留精确的图片 MIME。"',
    ]
    for index, (name, component_en, component_zh) in enumerate(assets, start=1):
        lines.extend(
            [
                "",
                "[[sections.components]]",
                'type = "plot_card"',
                f'id = "image-{index}"',
                f'image = "03_results/figures/{name}"',
                f'title.en = "1.{index} {component_en}"',
                f'title.zh = "1.{index} {component_zh}"',
                'note.en = "Renderer-owned deterministic MIME mapping is required for this asset."',
                'note.zh = "该资源必须使用 renderer 内部的确定性 MIME 映射。"',
            ]
        )
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--profile", choices=("core", "fungal-equivalent"), default="core")
    args = parser.parse_args()
    assets = write_images(args.root, args.profile)
    build_spec(args.root, args.spec, args.profile, assets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
