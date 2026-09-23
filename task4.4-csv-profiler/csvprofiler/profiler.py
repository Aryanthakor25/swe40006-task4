"""Profiling logic. Only uses the standard library so the image needs no pip install."""
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

MISSING = {"", "na", "n/a", "null", "none", "nan", "-"}


class ProfileError(Exception):
    """Raised when a file can't be read as CSV."""


def _to_number(value: str):
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return None


def profile_column(name: str, values: list[str]) -> dict:
    present = [v.strip() for v in values if v is not None and v.strip().lower() not in MISSING]
    missing = len(values) - len(present)
    numbers = [n for n in (_to_number(v) for v in present) if n is not None]

    col = {
        "name": name,
        "count": len(present),
        "missing": missing,
        "missing_pct": round(100 * missing / len(values), 2) if values else 0.0,
        "unique": len(set(present)),
    }

    # Call a column numeric if at least 90% of the present values parse as numbers
    if present and len(numbers) / len(present) >= 0.9:
        col["type"] = "numeric"
        col["non_numeric"] = len(present) - len(numbers)
        col["min"] = min(numbers)
        col["max"] = max(numbers)
        col["mean"] = round(statistics.fmean(numbers), 4)
        col["median"] = statistics.median(numbers)
        col["stdev"] = round(statistics.stdev(numbers), 4) if len(numbers) > 1 else 0.0
    else:
        col["type"] = "text"
        col["top_values"] = Counter(present).most_common(3)
    return col


def profile_csv(path: Path) -> dict:
    path = Path(path)
    try:
        with path.open(newline="", encoding="utf-8-sig") as fh:
            sample = fh.read(4096)
            fh.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel
            reader = csv.DictReader(fh, dialect=dialect)
            if not reader.fieldnames:
                raise ProfileError(f"{path.name}: no header row found")
            rows = list(reader)
    except UnicodeDecodeError as exc:
        raise ProfileError(f"{path.name}: not a UTF-8 text file ({exc.reason})") from exc

    columns = [profile_column(name, [r.get(name) for r in rows]) for name in reader.fieldnames]
    total_cells = len(rows) * len(columns)
    total_missing = sum(c["missing"] for c in columns)
    return {
        "file": path.name,
        "rows": len(rows),
        "columns": len(columns),
        "missing_cells": total_missing,
        "completeness_pct": round(100 * (1 - total_missing / total_cells), 2) if total_cells else 100.0,
        "column_profiles": columns,
    }


def to_markdown(profile: dict) -> str:
    lines = [
        f"# Data profile: {profile['file']}",
        "",
        f"- Rows: **{profile['rows']}**",
        f"- Columns: **{profile['columns']}**",
        f"- Missing cells: **{profile['missing_cells']}** (completeness {profile['completeness_pct']}%)",
        "",
        "| Column | Type | Count | Missing % | Unique | Min | Max | Mean | Median | Top values |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in profile["column_profiles"]:
        if c["type"] == "numeric":
            extra = [c["min"], c["max"], c["mean"], c["median"], ""]
        else:
            top = ", ".join(f"{v} ({n})" for v, n in c["top_values"])
            extra = ["", "", "", "", top]
        cells = [c["name"], c["type"], c["count"], c["missing_pct"], c["unique"], *extra]
        lines.append("| " + " | ".join(str(x) for x in cells) + " |")
    return "\n".join(lines) + "\n"


def write_outputs(profile: dict, out_dir: Path) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(profile["file"]).stem
    json_path = out_dir / f"{stem}.profile.json"
    md_path = out_dir / f"{stem}.profile.md"
    json_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(profile), encoding="utf-8")
    return [json_path, md_path]
