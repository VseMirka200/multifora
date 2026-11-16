"""Записывает размер и число файлов Windows-сборки."""

import argparse
import json
from pathlib import Path


def collect_bundle_metrics(bundle):
    bundle = Path(bundle)
    groups = {}
    total = 0
    files = sorted(path for path in bundle.rglob("*") if path.is_file())
    for path in files:
        size = path.stat().st_size
        total += size
        parts = path.relative_to(bundle).parts
        group = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
        data = groups.setdefault(group, {"bytes": 0, "files": 0})
        data["bytes"] += size
        data["files"] += 1
    return {"total_bytes": total, "file_count": len(files), "groups": groups}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-mib", type=float, required=True)
    parser.add_argument("--max-files", type=int, required=True)
    args = parser.parse_args(argv)
    metrics = collect_bundle_metrics(args.bundle)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(metrics["total_bytes"] > args.max_mib * 1024 * 1024 or metrics["file_count"] > args.max_files)


if __name__ == "__main__":
    raise SystemExit(main())
