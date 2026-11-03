"""Write deterministic Windows bundle metrics and enforce a size budget."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def collect_bundle_metrics(bundle: Path) -> dict[str, object]:
    files = [path for path in bundle.rglob("*") if path.is_file()]
    groups: dict[str, dict[str, int]] = defaultdict(lambda: {"bytes": 0, "files": 0})
    total_bytes = 0
    for path in files:
        relative = path.relative_to(bundle)
        parts = relative.parts
        group = f"{parts[0]}/{parts[1]}" if len(parts) >= 2 and parts[0] in {"_internal", "bin"} else parts[0]
        size = path.stat().st_size
        total_bytes += size
        groups[group]["bytes"] += size
        groups[group]["files"] += 1

    ordered_groups = dict(sorted(groups.items(), key=lambda item: item[1]["bytes"], reverse=True))
    return {
        "bundle": str(bundle),
        "total_bytes": total_bytes,
        "total_mib": round(total_bytes / (1024 * 1024), 2),
        "file_count": len(files),
        "groups": ordered_groups,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-mib", type=float, default=675.0)
    parser.add_argument("--max-files", type=int, default=1500)
    args = parser.parse_args(argv)

    metrics = collect_bundle_metrics(args.bundle)
    metrics["budget"] = {
        "max_mib": args.max_mib,
        "max_files": args.max_files,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Bundle metrics: {metrics['total_mib']} MiB, {metrics['file_count']} files -> {args.output}")
    errors = []
    if metrics["total_bytes"] > args.max_mib * 1024 * 1024:
        errors.append(f"bundle size {metrics['total_mib']} MiB exceeds {args.max_mib} MiB")
    if metrics["file_count"] > args.max_files:
        errors.append(f"bundle file count {metrics['file_count']} exceeds {args.max_files}")
    if errors:
        print("Bundle performance budget failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
