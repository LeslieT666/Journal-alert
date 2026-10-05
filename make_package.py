#!/usr/bin/env python
"""Build a clean, portable zip of this project for copying to another PC.

Usage::

    python make_package.py                 # include state/ (migration: keep read history)
    python make_package.py --fresh         # exclude state/ (new PC starts from scratch)
    python make_package.py --out E:\\      # where to write the zip (default: parent dir)

Excluded always: logs/, reports/, _probe/, __pycache__/, *.pyc, .write-test
"""

from __future__ import annotations

import argparse
import json
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# NOTE: "Journal-alert" 和 ".obsidian" 是用户的个人笔记库（Obsidian 库就建在项目
# 目录里）。这个 zip 是可以对外分享的，绝不能把个人笔记打进去 —— 之前漏了这两个，
# 导致 .obsidian/ 和 欢迎.md 混进了包里。
ALWAYS_EXCLUDE_DIRS = {
    "logs", "reports", "_probe", "__pycache__", ".git", ".workbuddy",
    "Journal-alert", ".obsidian",
}
ALWAYS_EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
ALWAYS_EXCLUDE_NAMES = {".write-test", "config.local.json", ".env", ".env.local", "欢迎.md"}
STATE_DIRS = {"state"}
SECRET_FIELDS = {"serverchan": "sendkey", "pushplus": "token", "bark": "key"}

QUICKSTART = """\
journal-alert 便携包
======================================================================
这个包已排除本机运行痕迹：日志(logs/)、旧日报(reports/)、
诊断脚本(_probe/)、Python 缓存(__pycache__/)。

state/ 里是「已读台账」。
  保留它 -> 新电脑不会重复推送你在旧电脑上已看过的文献（迁移推荐）
  删掉它 -> 从零开始，新电脑第一次运行会把时间窗内所有文献都当成新的

三步跑起来
----------------------------------------------------------------------
1) 装 Python 3.10 或更高版本，安装时勾选 "Add python.exe to PATH"
   https://www.python.org/downloads/
   本项目只用标准库，不需要 pip install 任何东西。

2) 环境自检（先做这一步，能提前发现 90% 的部署问题）
   在解压出来的目录里执行：
       run_daily.cmd --doctor

3) 注册每日计划任务（周一至周五 07:30）
   完整命令见 README.md 第 7.2 节，可直接复制粘贴。
   注意那条命令里的 $settings 不能省，否则笔记本上电池供电时不会运行。

可选：开通微信推送
   见 README.md 第 6 节（约 3 分钟），配好后执行：
       run_daily.cmd --test-push

文档导航
----------------------------------------------------------------------
README.md    <- 唯一的文档：快速开始、每日自动运行、微信推送、
                换电脑迁移、关键词与期刊配置、数据源、故障排查

注意事项
----------------------------------------------------------------------
- config.local.json 里放推送密钥（明文）。别把这个包分享给别人。
- 计划任务不会跟着文件夹走，必须在新电脑上重新注册一次。
- 项目放在哪个盘、哪个目录都行，代码里没有写死路径。
"""


def build_file_list(include_state: bool) -> list[Path]:
    files: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        parts = set(rel.parts[:-1])
        if rel.parts[:2] == ("state", "daily"):  # transient per-day snapshots
            continue
        if parts & ALWAYS_EXCLUDE_DIRS:
            continue
        if not include_state and parts & STATE_DIRS:
            continue
        if path.suffix.lower() in ALWAYS_EXCLUDE_SUFFIXES:
            continue
        if path.name in ALWAYS_EXCLUDE_NAMES:
            continue
        if ".bak-" in path.name:  # state/seen.sqlite.bak-YYYYMMDD
            continue
        if path.name == "先读我-安装三步.txt":
            # Regenerated from QUICKSTART below, so the packaged copy is always
            # current and never appears twice in the archive.
            continue
        if path.name.startswith("~$"):
            continue
        files.append(path)
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fresh", action="store_true",
                        help="exclude state/ so the new PC starts with an empty history")
    parser.add_argument("--out", default=str(ROOT.parent),
                        help="directory to write the zip into (default: parent of this project)")
    parser.add_argument("--name", default=f"journal-alert-portable-{date.today():%Y%m%d}.zip",
                        help="zip file name")
    parser.add_argument("--keep-secrets", action="store_true",
                        help="keep push keys inside the package (only for direct USB copies)")
    args = parser.parse_args(argv)

    include_state = not args.fresh
    strip_secrets = not args.keep_secrets
    files = build_file_list(include_state)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / args.name
    if target.exists():
        target.unlink()

    total = 0
    stripped = []
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            arcname = (Path(ROOT.name) / path.relative_to(ROOT)).as_posix()
            if strip_secrets and path.name == "config.json":
                data = json.loads(path.read_text(encoding="utf-8"))
                for channel, field in SECRET_FIELDS.items():
                    node = data.get("push", {}).get("channels", {}).get(channel)
                    if isinstance(node, dict) and node.get(field):
                        stripped.append(f"{channel}.{field}")
                        node[field] = ""
                text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
                zf.writestr(arcname, text)
                total += len(text.encode("utf-8"))
                continue
            zf.write(path, arcname)
            total += path.stat().st_size
        zf.writestr(f"{ROOT.name}/先读我-安装三步.txt", QUICKSTART)

    print(f"已打包 {len(files)} 个文件（原始 {total / 1024:.0f} KB）")
    print(f"输出   : {target}")
    print(f"压缩后 : {target.stat().st_size / 1024:.0f} KB")
    print(f"含 state/ 已读台账: {'是（迁移模式）' if include_state else '否（全新模式）'}")
    print(f"推送密钥          : {'已清空 -> ' + ', '.join(stripped) if stripped else '无需处理（本来就没填）'}")

    skipped = []
    for name in sorted(ALWAYS_EXCLUDE_DIRS | (set() if include_state else STATE_DIRS)):
        if (ROOT / name).exists():
            skipped.append(name + "/")
    print(f"已排除 : {' '.join(skipped)}")
    if stripped:
        print()
        print("注意：为了让这个包可以安全地用邮件/网盘/U盘传递，推送密钥已从包里清空。")
        print("      到新电脑后照 README.md 第 6 节填一次即可（约 30 秒）。")
        print("      如果只在自己两台电脑之间用 U 盘直接拷、想省掉这一步，改用：")
        print("          python make_package.py --keep-secrets")
    print()
    print("下一步：把 zip 拷到新电脑，解压后先跑 run_daily.cmd --doctor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
