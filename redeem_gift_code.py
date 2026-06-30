#!/usr/bin/env python3
"""Disabled LastZ gift-code redemption entry point."""

from __future__ import annotations

import argparse
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gift-code redemption is temporarily disabled.",
    )
    parser.add_argument("code", nargs="?", help="保留參數；目前不會送出兌換請求")
    parser.add_argument("--quiet", action="store_true", help="不輸出停用說明")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.quiet:
        print(
            "禮物碼領取功能已暫時停用：giftcenter uuid 可能需要登入流程取得，"
            "目前無法可靠自動兌換。",
            file=sys.stderr,
        )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
