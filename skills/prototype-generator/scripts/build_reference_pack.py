#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from reference_utils import ensure_reference_pack


def main():
    parser = argparse.ArgumentParser(description="为 prototype-generator HTML 流程构建参考包")
    parser.add_argument("work_dir")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()

    manifest = ensure_reference_pack(Path(args.work_dir))
    output = json.dumps(manifest, ensure_ascii=False, indent=2)
    print(output)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
