#!/usr/bin/env python3
"""Run LastZ store task APIs for a user id.

Use only with your own account/user id.
"""

from __future__ import annotations

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


STORE_ORIGIN = "https://store.last-z.com"
WEBSITE_ORIGIN = "https://last-z.com"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class ApiTask:
    name: str
    url: str
    origin: str
    referer: str
    payload: dict[str, Any]
    include_login_cookie: bool = False


@dataclass(frozen=True)
class TaskResult:
    task_name: str
    ok: bool
    status: int | None = None
    response_text: str = ""
    error: str = ""


def build_tasks(uid: str, day: int, vip_level: int) -> list[ApiTask]:
    return [
        ApiTask(
            name="七日簽到",
            url=f"{STORE_ORIGIN}/sendday7_new.php",
            origin=WEBSITE_ORIGIN,
            referer=f"{WEBSITE_ORIGIN}/",
            payload={
                "uid": uid,
                "day": day,
                "dtype": 0,
                "lang": "hk",
            },
        ),
        ApiTask(
            name="進入積分商城頁面",
            url=f"{STORE_ORIGIN}/getshop.php",
            origin=WEBSITE_ORIGIN,
            referer=f"{WEBSITE_ORIGIN}/",
            payload={
                "uid": uid,
                "fromOrigin": "website",
            },
        ),
        ApiTask(
            name="完成任務：登入",
            url=f"{STORE_ORIGIN}/sendtask_new.php",
            origin=WEBSITE_ORIGIN,
            referer=f"{WEBSITE_ORIGIN}/",
            payload={
                "uid": uid,
                "type": "login",
                "lang": "hk",
                "fromOrigin": "website",
            },
        ),
        ApiTask(
            name="完成任務：瀏覽會員中心頁面",
            url=f"{STORE_ORIGIN}/sendtask_new.php",
            origin=WEBSITE_ORIGIN,
            referer=f"{WEBSITE_ORIGIN}/",
            payload={
                "uid": uid,
                "type": "viewucenter",
                "lang": "hk",
                "fromOrigin": "website",
            },
        ),
        ApiTask(
            name="完成任務：瀏覽積分商城頁面",
            url=f"{STORE_ORIGIN}/sendtask_new.php",
            origin=WEBSITE_ORIGIN,
            referer=f"{WEBSITE_ORIGIN}/",
            payload={
                "uid": uid,
                "type": "viewshop",
                "lang": "hk",
                "fromOrigin": "website",
            },
        ),
        ApiTask(
            name="每日購買任意禮包或購買金碼數量達到 1000",
            url=f"{STORE_ORIGIN}/sendtask_new.php",
            origin=WEBSITE_ORIGIN,
            referer=f"{WEBSITE_ORIGIN}/",
            payload={
                "uid": uid,
                "type": "buy1000",
                "lang": "hk",
                "fromOrigin": "website",
            },
        ),
        ApiTask(
            name="首次購買金磚數量達到 2000",
            url=f"{STORE_ORIGIN}/sendtask_new.php",
            origin=STORE_ORIGIN,
            referer=f"{STORE_ORIGIN}/",
            include_login_cookie=True,
            payload={
                "uid": uid,
                "type": "first2000",
                "fromkoc": "",
                "lang": "zh-HK",
            },
        ),
        ApiTask(
            name="領取每週特權禮包",
            url=f"{STORE_ORIGIN}/sendvip.php",
            origin=WEBSITE_ORIGIN,
            referer=f"{WEBSITE_ORIGIN}/",
            payload={
                "uid": uid,
                "vlevel": vip_level,
                "type": "week",
                "lang": "hk",
            },
        ),
    ]


def make_headers(uid: str, task: ApiTask, user_agent: str) -> dict[str, str]:
    headers = {
        "Usertoken": uid,
        "User-Agent": user_agent,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Accept-Language": "zh-TW,zh;q=0.6",
        "Origin": task.origin,
        "Referer": task.referer,
    }
    if task.include_login_cookie:
        headers["Cookie"] = 'status={%22loginStatus%22:true}'
    return headers


def build_ssl_context(insecure: bool, ca_file: str | None) -> ssl.SSLContext | None:
    if insecure:
        return ssl._create_unverified_context()
    if ca_file:
        return ssl.create_default_context(cafile=ca_file)
    return None


def post_json(
    uid: str,
    task: ApiTask,
    user_agent: str,
    timeout: float,
    ssl_context: ssl.SSLContext | None,
) -> tuple[int, str]:
    body = json.dumps(task.payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        task.url,
        data=body,
        headers=make_headers(uid, task, user_agent),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout, context=ssl_context) as response:
        return response.status, response.read().decode("utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Input a LastZ user id and call the captured store task APIs."
    )
    parser.add_argument("uid", nargs="?", help="玩家 user id / uid")
    parser.add_argument("--day", type=int, default=5, help="七日簽到 day 值，預設 5")
    parser.add_argument("--vip-level", type=int, default=1, help="VIP 等級 vlevel，預設 1")
    parser.add_argument("--delay", type=float, default=0.8, help="每個 API 間隔秒數，預設 0.8")
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


def require_uid(uid: str | None) -> str:
    if uid:
        return uid.strip()
    return input("請輸入玩家 id / uid: ").strip()


def run_tasks_for_uid(
    uid: str,
    *,
    day: int,
    vip_level: int,
    delay: float,
    timeout: float,
    user_agent: str,
    ssl_context: ssl.SSLContext | None,
    dry_run: bool,
    quiet: bool = False,
) -> list[TaskResult]:
    tasks = build_tasks(uid=uid, day=day, vip_level=vip_level)
    results: list[TaskResult] = []

    for index, task in enumerate(tasks, start=1):
        if not quiet:
            print(f"\n[{index}/{len(tasks)}] {task.name}")
            print(f"POST {task.url}")
            print(json.dumps(task.payload, ensure_ascii=False, indent=2))

        if dry_run:
            results.append(TaskResult(task_name=task.name, ok=True))
            continue

        try:
            status, text = post_json(uid, task, user_agent, timeout, ssl_context)
        except urllib.error.HTTPError as exc:
            error_text = exc.read().decode("utf-8", errors="replace")
            if not quiet:
                print(f"HTTP {exc.code}: {error_text}", file=sys.stderr)
            results.append(
                TaskResult(
                    task_name=task.name,
                    ok=False,
                    status=exc.code,
                    response_text=error_text,
                    error=f"HTTP {exc.code}",
                )
            )
        except (urllib.error.URLError, TimeoutError) as exc:
            if not quiet:
                print(f"請求失敗：{exc}", file=sys.stderr)
            results.append(TaskResult(task_name=task.name, ok=False, error=str(exc)))
        else:
            if not quiet:
                print(f"HTTP {status}: {text}")
            results.append(
                TaskResult(task_name=task.name, ok=200 <= status < 300, status=status, response_text=text)
            )

        if index < len(tasks) and delay > 0:
            time.sleep(delay)

    return results


def main() -> int:
    args = parse_args()
    uid = require_uid(args.uid)
    if not uid:
        print("錯誤：uid 不可為空", file=sys.stderr)
        return 2

    ssl_context = build_ssl_context(insecure=args.insecure, ca_file=args.ca_file)
    if args.insecure and not args.dry_run and not args.quiet:
        print("警告：已啟用 --insecure，HTTPS 憑證將不會被驗證。", file=sys.stderr)

    results = run_tasks_for_uid(
        uid,
        day=args.day,
        vip_level=args.vip_level,
        delay=args.delay,
        timeout=args.timeout,
        user_agent=args.user_agent,
        ssl_context=ssl_context,
        dry_run=args.dry_run,
        quiet=args.quiet,
    )

    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
