"""Validate the layout of a frozen/installed Windows build.

Runs without third-party modules; this lets CI check the packaging itself.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


def check_bundle(bundle: Path) -> list[str]:
    missing = []
    for relative in (
        'Multifora.exe',
        'bin/gswin64/gswin64c.exe',
        'bin/gswin64/gsdll64.dll',
    ):
        path = bundle / relative
        if not path.is_file() or path.stat().st_size == 0:
            missing.append(relative)

    internal = bundle / '_internal'
    if not internal.is_dir():
        missing.append('_internal/')
    else:
        for name in ('icon.ico', 'checkbox_checked.svg'):
            if not any(internal.rglob(name)):
                missing.append(f'_internal/**/{name}')
        for name in ('qwindows.dll', 'qoffscreen.dll'):
            if not any(internal.rglob(name)):
                missing.append(f'_internal/**/{name}')
    return missing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args(argv)
    missing = check_bundle(args.bundle)
    if missing:
        print('Incomplete Windows bundle:', file=sys.stderr)
        for item in missing:
            print(f'  - {item}', file=sys.stderr)
        return 1
    print(f'Bundle contents verified: {args.bundle}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
