#!/usr/bin/env python3
"""Redeem a LastZ gift code for every configured account."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from lastz_tasks import DEFAULT_USER_AGENT, WEBSITE_ORIGIN, build_ssl_context
from run_daily_tasks import DEFAULT_ACCOUNTS_FILE, Account, load_accounts


GIFT_ORIGIN = "https://giftcenter.last-z.com"


def make_headers(uid: str, user_agent: str) -> dict[str, str]:
    return {
        "Usertoken": uid,
        "User-Agent": user_agent,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-TW,zh;q=0.6",
        "Origin": WEBSITE_ORIGIN,
        "Referer": f"{WEBSITE_ORIGIN}/",
    }


def build_gift_url(uid: str, code: str) -> str:
    query = urllib.parse.urlencode({"uid": uid, "code": code})
    return f"{GIFT_ORIGIN}/code.php?{query}"


def redeem_code(
    account: Account,
    *,
    code: str,
    user_agent: str,
    timeout: float,
    ssl_context,
) -> tuple[bool, str]:
    request = urllib.request.Request(
        build_gift_url(account.uid, code),
        headers=make_headers(account.uid, user_agent),
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout, context=ssl_context) as response:
        text = response.read().decode("utf-8", errors="replace")

    if not 200 <= response.status < 300:
        return False, f"HTTP {response.status}: {text}"

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return False, text

    ok = data.get("errorCode") == "ok"
    return ok, text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Redeem a LastZ gift code for configured accounts.")
    parser.add_argument("code", help="兌換碼，例如 CELEBRATE300K")
    parser.add_argument("--accounts", type=Path, default=DEFAULT_ACCOUNTS_FILE, help="帳號設定檔，預設 accounts.json")
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


def main() -> int:
    args = parse_args()
    code = args.code.strip()
    if not code:
        print("錯誤：code 不可為空", file=sys.stderr)
        return 2

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
        url = build_gift_url(account.uid, code)
        if not args.quiet:
            print(f"\n[{index}/{len(accounts)}] {account.name} ({account.uid})")
            print(f"GET {url}")

        if args.dry_run:
            continue

        try:
            ok, text = redeem_code(
                account,
                code=code,
                user_agent=args.user_agent,
                timeout=args.timeout,
                ssl_context=ssl_context,
            )
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            ok = False
            message = f"HTTP {exc.code}: {text}"
        except (urllib.error.URLError, TimeoutError) as exc:
            ok = False
            message = str(exc)
        else:
            message = text

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
        print("以下帳號兌換失敗：")
        for failed_account in failed_accounts:
            print(f"- {failed_account}")
        return 1

    print("全部帳號兌換完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
