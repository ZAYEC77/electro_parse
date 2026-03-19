from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from electro_parse import parse_schedule_image


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def _format_report_json(value: object, indent: int = 0) -> str:
    space = " " * indent
    next_space = " " * (indent + 2)

    if isinstance(value, dict):
        if not value:
            return "{}"
        items = []
        for key, item in value.items():
            formatted_item = _format_report_json(item, indent + 2)
            items.append(f'{next_space}{json.dumps(key, ensure_ascii=False)}: {formatted_item}')
        return "{\n" + ",\n".join(items) + f"\n{space}" + "}"

    if isinstance(value, list):
        rendered = ", ".join(json.dumps(item, ensure_ascii=False) for item in value)
        return f"[{rendered}]"

    return json.dumps(value, ensure_ascii=False)


def _iter_source_images(image_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in image_dir.iterdir()
        if path.is_file()
        and not path.name.startswith(".")
        and ".debug." not in path.name
        and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
    )


def generate_report(
    *,
    image_dir: str | Path = "images",
    report_dir: str | Path = "report",
    row_count: int = 12,
    column_count: int = 24,
    max_colors: int = 10,
) -> Path:
    image_dir = Path(image_dir)
    report_dir = Path(report_dir)
    assets_dir = report_dir / "assets"

    images = _iter_source_images(image_dir)
    if not images:
        raise ValueError(f"No source images found in {image_dir}")

    report_dir.mkdir(parents=True, exist_ok=True)
    if assets_dir.exists():
        shutil.rmtree(assets_dir)
    assets_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Electro Parse Report",
        "",
        f"Source directory: `{image_dir}`",
        "",
    ]

    for image_path in images:
        debug_name = f"{image_path.stem}.debug{image_path.suffix.lower()}"
        debug_path = assets_dir / debug_name
        source_link = image_path.relative_to(image_dir) if image_path.is_relative_to(image_dir) else image_path.name
        parsed = parse_schedule_image(
            image_path,
            row_count=row_count,
            column_count=column_count,
            max_colors=max_colors,
            debug_output=debug_path,
        )

        lines.extend(
            [
                f"## [{image_path.name}](../{image_dir.name}/{source_link.as_posix() if isinstance(source_link, Path) else source_link})",
                "",
                f"![{image_path.name}](assets/{debug_name})",
                "",
                "<details>",
                "<summary>Показати розпізнані дані</summary>",
                "",
                "```json",
                _format_report_json(parsed),
                "```",
                "</details>",
                "",
            ]
        )

    report_path = report_dir / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Markdown report with debug images.")
    parser.add_argument("--images", type=Path, default=Path("images"), help="Directory with source images")
    parser.add_argument("--report", type=Path, default=Path("report"), help="Directory for report output")
    parser.add_argument("--rows", type=int, default=12, help="Number of matrix rows to parse")
    parser.add_argument("--columns", type=int, default=24, help="Number of hour columns to parse")
    parser.add_argument("--max-colors", type=int, default=10, help="Palette size for image quantization")
    args = parser.parse_args()

    report_path = generate_report(
        image_dir=args.images,
        report_dir=args.report,
        row_count=args.rows,
        column_count=args.columns,
        max_colors=args.max_colors,
    )
    print(report_path)


if __name__ == "__main__":
    main()
