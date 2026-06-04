#!/usr/bin/env python3
"""Run LastZ task APIs for every account in accounts.json."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lastz_tasks import DEFAULT_USER_AGENT, build_ssl_context, run_tasks_for_uid


DEFAULT_ACCOUNTS_FILE = Path(__file__).with_name("accounts.json")


@dataclass(frozen=True)
class Account:
    name: str
    uid: str


def load_accounts(path: Path) -> list[Account]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("accounts.json 必須是一個陣列")

    accounts: list[Account] = []
    for item in data:
        account = parse_account(item)
        if account:
            accounts.append(account)

    if not accounts:
        raise ValueError("accounts.json 沒有可執行的帳號")

    return accounts


def parse_account(item: Any) -> Account | None:
    if not isinstance(item, dict):
        raise ValueError("每個帳號必須是物件，例如 {\"name\": \"甜璃\", \"uid\": \"...\"}")

    if item.get("enabled", True) is False:
        return None

    name = str(item.get("name", "")).strip()
    uid = str(item.get("uid", "")).strip()
    if not name or not uid:
        raise ValueError("每個啟用的帳號都需要 name 和 uid")

    return Account(name=name, uid=uid)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LastZ task APIs for configured accounts.")
    parser.add_argument("--accounts", type=Path, default=DEFAULT_ACCOUNTS_FILE, help="帳號設定檔，預設 accounts.json")
    parser.add_argument("--day", type=int, default=1, help="七日簽到 day 值，預設 1")
    parser.add_argument("--vip-level", type=int, default=1, help="VIP 等級 vlevel，預設 1")
    parser.add_argument("--task-delay", type=float, default=0.8, help="同一帳號每個 API 間隔秒數，預設 0.8")
    parser.add_argument("--account-delay", type=float, default=2.0, help="每個帳號間隔秒數，預設 2.0")
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


def main() -> int:
    args = parse_args()

    try:
        accounts = load_accounts(args.accounts)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"讀取帳號設定失敗：{exc}", file=sys.stderr)
        return 2

    ssl_context = build_ssl_context(insecure=args.insecure, ca_file=args.ca_file)
    if args.insecure and not args.dry_run and not args.quiet:
        print("警告：已啟用 --insecure，HTTPS 憑證將不會被驗證。", file=sys.stderr)

    failed_accounts: list[str] = []
    for index, account in enumerate(accounts, start=1):
        if not args.quiet:
            print(f"\n========== [{index}/{len(accounts)}] {account.name} ({account.uid}) ==========")
        results = run_tasks_for_uid(
            account.uid,
            day=args.day,
            vip_level=args.vip_level,
            delay=args.task_delay,
            timeout=args.timeout,
            user_agent=args.user_agent,
            ssl_context=ssl_context,
            dry_run=args.dry_run,
            quiet=args.quiet,
        )

        failed = [result.task_name for result in results if not result.ok]
        if failed:
            failed_accounts.append(f"{account.name}: {', '.join(failed)}")

        if not args.dry_run and index < len(accounts) and args.account_delay > 0:
            time.sleep(args.account_delay)

    if args.quiet:
        return 1 if failed_accounts else 0

    print("\n========== Summary ==========")
    if failed_accounts:
        print("以下帳號有失敗任務：")
        for failed_account in failed_accounts:
            print(f"- {failed_account}")
        return 1

    print("全部帳號執行完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
