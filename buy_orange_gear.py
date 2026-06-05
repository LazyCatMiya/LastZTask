#!/usr/bin/env python3
"""Manually buy orange gear from the LastZ points shop."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
from pathlib import Path

from lastz_tasks import (
    DEFAULT_USER_AGENT,
    STORE_ORIGIN,
    WEBSITE_ORIGIN,
    ApiTask,
    build_ssl_context,
    post_json,
)
from run_daily_tasks import DEFAULT_ACCOUNTS_FILE, Account, load_accounts


DEFAULT_LID = 202606
DEFAULT_ITEM_TYPE = "253014_1_20"
DEFAULT_COUNT = 1


def build_buy_task(uid: str, *, lid: int, item_type: str, count: int) -> ApiTask:
    return ApiTask(
        name="用積分購買橙裝",
        url=f"{STORE_ORIGIN}/sendshop.php",
        origin=WEBSITE_ORIGIN,
        referer=f"{WEBSITE_ORIGIN}/",
        payload={
            "lid": lid,
            "uid": uid,
            "type": item_type,
            "lang": "hk",
            "count": count,
            "fromOrigin": "website",
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manually buy orange gear with points.")
    parser.add_argument("uid", nargs="?", help="單一玩家 user id / uid")
    parser.add_argument("--all-accounts", action="store_true", help="對 accounts.json 中所有啟用帳號執行")
    parser.add_argument("--accounts", type=Path, default=DEFAULT_ACCOUNTS_FILE, help="帳號設定檔，預設 accounts.json")
    parser.add_argument("--lid", type=int, default=DEFAULT_LID, help=f"商品 lid，預設 {DEFAULT_LID}")
    parser.add_argument("--item-type", default=DEFAULT_ITEM_TYPE, help=f"商品 type，預設 {DEFAULT_ITEM_TYPE}")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help=f"購買數量，預設 {DEFAULT_COUNT}")
    parser.add_argument("--account-delay", type=float, default=1.0, help="每個帳號間隔秒數，預設 1.0")
    parser.add_argument("--timeout", type=float, default=20, help="單次請求逾時秒數，預設 20")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="自訂 User-Agent")
    parser.add_argument("--ca-file", help="指定自訂 CA 憑證檔，用來修正本機憑證鏈問題")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="跳過 HTTPS 憑證驗證；只建議在你信任目前網路時暫時使用",
    )
    parser.add_argument("--quiet", action="store_true", help="不輸出執行過程與結果")
    parser.add_argument("--dry-run", action="store_true", help="只列出將送出的 API，不真的呼叫")
    return parser.parse_args()


def account_list(args: argparse.Namespace) -> list[Account]:
    if args.all_accounts:
        return load_accounts(args.accounts)

    uid = args.uid.strip() if args.uid else input("請輸入玩家 id / uid: ").strip()
    if not uid:
        raise ValueError("uid 不可為空")
    return [Account(name=uid, uid=uid)]


def is_ok_response(text: str) -> bool:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return False
    return data.get("code") == 0


def main() -> int:
    args = parse_args()
    if args.count < 1:
        print("錯誤：count 必須大於 0", file=sys.stderr)
        return 2

    try:
        accounts = account_list(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"讀取帳號設定失敗：{exc}", file=sys.stderr)
        return 2

    ssl_context = build_ssl_context(insecure=args.insecure, ca_file=args.ca_file)
    if args.insecure and not args.dry_run and not args.quiet:
        print("警告：已啟用 --insecure，HTTPS 憑證將不會被驗證。", file=sys.stderr)

    failed_accounts: list[str] = []
    for index, account in enumerate(accounts, start=1):
        task = build_buy_task(account.uid, lid=args.lid, item_type=args.item_type, count=args.count)
        if not args.quiet:
            print(f"\n[{index}/{len(accounts)}] {account.name} ({account.uid})")
            print(f"POST {task.url}")
            print(json.dumps(task.payload, ensure_ascii=False, indent=2))

        if args.dry_run:
            continue

        try:
            status, text = post_json(account.uid, task, args.user_agent, args.timeout, ssl_context)
            ok = 200 <= status < 300 and is_ok_response(text)
            message = f"HTTP {status}: {text}"
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            ok = False
            message = f"HTTP {exc.code}: {text}"
        except (urllib.error.URLError, TimeoutError) as exc:
            ok = False
            message = str(exc)

        if not ok:
            failed_accounts.append(f"{account.name}: {message}")

        if not args.quiet:
            print(message)

        if index < len(accounts) and args.account_delay > 0:
            time.sleep(args.account_delay)

    if args.quiet:
        return 1 if failed_accounts else 0

    print("\n========== Summary ==========")
    if failed_accounts:
        print("以下帳號購買失敗：")
        for failed_account in failed_accounts:
            print(f"- {failed_account}")
        return 1

    print("購買橙裝執行完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
