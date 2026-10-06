#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""把 GitHub 上 reports/ 目录的日报镜像到本地——这个库的同步引擎。

为什么不用 git
--------------
本机到 github.com:443 的 git 通道不稳定（代理 CONNECT 502、TLS 握手失败、
传输中途断流轮着来），但 api.github.com 一直可用。这个库是只读镜像，
不需要提交历史，所以直接用 REST API 拉当前文件反而最稳。

顺带避开了行尾的坑：API 返回的是仓库里的原始字节（LF），写进来就是 LF，
不会像 git 那样被 core.autocrlf 在检出时改成 CRLF。

仓库是公开的，因此**不需要任何 token**，也不用担心密钥泄漏。

用法
----
    python 同步.py              正常同步
    python 同步.py --list       只看远端有哪些日报，不下载
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = "pkui1mpression-design/Journal-alert"
FOLDER = "reports"
API = "https://api.github.com"
UA = "jalert-obsidian-sync"
TIMEOUT = 45
RETRIES = 3

HERE = Path(__file__).resolve().parent
DEST = HERE / FOLDER

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def say(message: str = "") -> None:
    print(message, flush=True)


def api_get(path: str) -> object:
    """GET API，带重试。公开仓库，不带认证头。"""
    last = None
    for attempt in range(1, RETRIES + 1):
        req = urllib.request.Request(
            API + path,
            headers={"Accept": "application/vnd.github+json", "User-Agent": UA},
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise
            last = f"HTTP {exc.code}"
        except Exception as exc:  # 网络类错误都归到这里
            last = f"{type(exc).__name__}: {exc}"
        if attempt < RETRIES:
            time.sleep(2 * attempt)
    raise RuntimeError(f"连续 {RETRIES} 次都没连上 GitHub（{last}）")


def blob_sha(data: bytes) -> str:
    """本地算 git blob 的 sha，用来判断远端是否真的变了。

    只比大小或时间戳不可靠；算出和远端一致的 sha 才能确定「没必要动」，
    这样没更新的日子文件 mtime 不变，Obsidian 不会白重载一遍。
    """
    digest = hashlib.sha1()
    digest.update(b"blob %d\0" % len(data))
    digest.update(data)
    return digest.hexdigest()


def main() -> int:
    list_only = "--list" in sys.argv

    say(f"仓库：{REPO}")
    say(f"目标：{DEST}")
    say()

    try:
        entries = api_get(f"/repos/{REPO}/contents/{FOLDER}")
    except urllib.error.HTTPError as exc:
        say(f"[失败] GitHub API 返回 HTTP {exc.code}")
        say("       公开仓库不该出现 401/403，若是 404 请确认仓库地址和目录名。")
        return 1
    except Exception as exc:
        say(f"[失败] {exc}")
        say("       检查一下网络；本脚本走 api.github.com，不经过 git 通道。")
        return 1

    if not isinstance(entries, list):
        say("[失败] API 返回的不是目录列表。")
        return 1

    remote = [e for e in entries if e.get("type") == "file" and e["name"].endswith(".md")]
    remote.sort(key=lambda e: e["name"], reverse=True)

    if list_only:
        say(f"远端共有 {len(remote)} 篇日报：")
        for entry in remote:
            say(f"  {entry['name']}  {entry['size']:>7} bytes  {entry['sha'][:10]}")
        return 0

    if not remote:
        say("[提醒] 远端 reports/ 里没有 .md 文件。")
        return 1

    DEST.mkdir(parents=True, exist_ok=True)

    added, changed, same, failed = [], [], [], []
    for entry in remote:
        name = entry["name"]
        target = DEST / name
        try:
            raw = entry.get("content")
            if not raw:
                # 目录列表对小文件会直接给 content；万一没有就单独取一次
                detail = api_get(f"/repos/{REPO}/contents/{FOLDER}/{name}")
                raw = detail["content"]
            data = base64.b64decode(raw, validate=False)
        except Exception as exc:
            failed.append((name, str(exc)))
            continue

        if target.is_file():
            local = target.read_bytes()
            if blob_sha(local) == entry["sha"]:
                same.append(name)
                continue
            # 内容对不上，但可能是行尾差异造成的假变化，比对一下归一化后的结果
            if local.replace(b"\r\n", b"\n") == data:
                target.write_bytes(data)  # 只修行尾，不算内容更新
                same.append(name)
                continue
            target.write_bytes(data)
            changed.append(name)
        else:
            target.write_bytes(data)
            added.append(name)

    say(f"远端 {len(remote)} 篇 ｜ 新增 {len(added)} ｜ 更新 {len(changed)} ｜ 无变化 {len(same)}")
    for name in added:
        say(f"  + {name}")
    for name in changed:
        say(f"  ~ {name}")
    if failed:
        say(f"  下载失败 {len(failed)} 篇：")
        for name, why in failed:
            say(f"    ! {name}  {why}")
    say()
    say("完成。" if not failed else "部分完成（有几篇没下下来，可稍后重跑）。")
    return 0 if not failed else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        say("\n已中断。")
        raise SystemExit(130)
