# 大气环境文献日报（journal-alert）

把「期刊定期推送」变成**按关键词筛选后的微信推送 + 本地 Markdown 每日阅读报**，全自动、每天定时运行。

它**不依赖你的邮箱**：直接抓取期刊官网 RSS，并用 OpenAlex / Crossref 官方 API 兜底和补充摘要，因此不受邮箱改版、RSS 邮件格式、Outlook 客户端类型的任何影响。

---

## 1. 它做什么

```
16 本目标期刊 ──┬─ RSS（官网推送源）
                ├─ OpenAlex API（按 ISSN + 日期）
                └─ Crossref API（按 ISSN + 日期）
                        │
                        ▼
        合并去重（DOI 优先）→ 时间窗过滤
                        │
                        ▼
   关键词打分（标题 ×3 / 摘要 ×1，同义词扩展）
                        │
                        ▼
    排除规则（撤稿/勘误/社论/Nature 新闻稿）
                        │
                        ▼
   SQLite 历史库去重 ──► 只保留「从未见过」的新文献
                        │
                        ├─► Markdown 每日阅读报（必读 / 值得一读 / 其他相关）
                        └─► 微信推送摘要（Server酱 / PushPlus / Bark）
```

**分级规则**（可在 `config.json` 的 `tiers` 里改）：

| 级别 | 条件 | 含义 |
|---|---|---|
| 🔥 必读 | 得分 ≥ 12 | 至少一个关键词命中标题，且另有命中 |
| 值得一读 | 得分 ≥ 6 | 一个关键词命中标题 |
| 其他相关 | 得分 ≥ 3 | 仅摘要命中 |
| 丢弃 | 得分 < 3 | 不进入报告 |

得分 = Σ（关键词权重 × 字段倍数）。默认权重 3，标题倍数 3，摘要倍数 1。所以「标题命中一个关键词」= 9 分。

---

## 2. 目录结构

| 路径 | 作用 |
|---|---|
| `config.json` | **唯一需要你改的文件**：期刊、关键词、分级阈值、推送密钥 |
| `run.py` | 主程序（命令行入口） |
| `jalert/fetch.py` | 三源抓取与解析（RSS/Atom/RDF、OpenAlex、Crossref） |
| `jalert/score.py` | 关键词打分、同义词匹配、排除规则 |
| `jalert/state.py` | SQLite 历史库（跨天去重 + 累积文献台账） |
| `jalert/report.py` | Markdown 报告与推送文案生成 |
| `jalert/push.py` | Server酱 / PushPlus / Bark 推送 |
| `reports/YYYY-MM-DD.md` | **每日阅读报**（正文） |
| `reports/YYYY-MM-DD.json` | 同日结构化数据（可再导入 Excel/Obsidian） |
| `state/daily/YYYY-MM-DD.json` | 当日报表快照（同一天多次运行会合并，不会互相覆盖） |
| `state/seen.sqlite` | 历史库：`articles` 表是累积文献台账，`runs` 表是运行日志 |
| `logs/` | 运行日志与调度器日志 |
| `run_daily.cmd` | 供计划任务调用的启动脚本（自动寻找可用的 Python） |
| `make_package.py` | 打包成可移植 zip，供复制到另一台电脑 |
| `推送配置指南.md` | 微信推送密钥的申请步骤与排查表 |
| `部署到新电脑.md` | 换电脑时的复制清单、Python 安装、计划任务重注册 |
| `GitHub-公开与自动化.md` | 公开仓库前要清什么、GitHub Actions 云端每天自动跑、密钥改走 Secrets |
| `.github/workflows/daily.yml` | 云端定时任务定义（每天 07:30 东八区跑 `run.py --once`） |
| `config.local.json` | **不入库**的本机覆盖层，推送密钥写这里 |
| `.gitignore` / `LICENSE` | 入库清单 / MIT 许可证 |

**打包到另一台电脑**（完整清单见 [部署到新电脑.md](部署到新电脑.md)）：

```powershell
& $PY make_package.py                 # 生成便携 zip（自动排除日志/旧日报/缓存，并清空推送密钥）
& $PY make_package.py --fresh         # 不要已读台账，新电脑从零开始
& $PY make_package.py --keep-secrets  # 保留密钥：只在自己电脑之间用 U 盘直接拷时才用
```

包里会自动放一份 `先读我-安装三步.txt`。已实测：解压到**含空格的任意路径**后 `run_daily.cmd --doctor` 返回「一切正常」。

---

## 3. 常用命令

在**项目根目录**下（把 `PY` 换成你的 Python 路径，见第 7 节）：

```powershell
# 完整跑一次：抓取 → 筛选 → 写报告 → 推送
& $PY run.py --once

# 只检查 16 本刊 × 3 个数据源的连通性，不写任何文件
& $PY run.py --check

# 试运行：不写库、不写报告、不推送，直接把报告打到屏幕上
& $PY run.py --dry-run --print

# 放大时间窗到 14 天（适合第一次使用，先看一批历史文献）
& $PY run.py --once --days 14

# 只用 RSS，不用 API（更快）
& $PY run.py --once --sources rss

# 不要推送
& $PY run.py --once --no-push

# 自检推送通道（配好密钥后立刻验证，不用等第二天）
& $PY run.py --test-push

# 改完关键词/分级阈值后，重排今天的日报，不必重新联网抓取
& $PY run.py --rerender

# 环境自检：Python 版本、目录写入权限、配置完整性、三个海外站点连通性
& $PY run.py --doctor
```

---

## 4. 改关键词与期刊

编辑 `config.json`：

```jsonc
"keywords": [
  {
    "label": "空气污染",              // 报告里显示的中文名
    "weight": 3,                      // 权重，越大越优先
    "terms": [                        // 命中的英文写法，全部小写、不分大小写匹配
      "air pollution", "pm2.5", "particulate matter", "aerosol", "ozone"
    ]
  }
]
```

要点：

* **`terms` 是召回率的关键**。同一个概念要列出各种英文写法（`pm2.5` / `pm25`、`aerosol` / `aerosols` 复数不用写，匹配时已按字母数字边界处理）。
* 匹配使用「字母数字边界」，所以 `no2` 不会误命中 `no2something`，`soa` 也不会命中 `soap`。
* 想临时屏蔽某类内容，加到 `exclude_terms`（命中即整条丢弃，默认已屏蔽撤稿/勘误/社论）。
* `exclude_doi_prefixes` 默认屏蔽 `10.1038/d41586（Nature 新闻/评论/播客）`，只保留研究论文。
* 增删期刊：`journals` 数组里加 `{ "name": ..., "issn": ..., "rss": ... }`。`issn` 必须准确，OpenAlex/Crossref 靠它取数。
* **只想每天看最重要的几篇**：`output.max_entries`（默认 `0` = 不限，当前设为 `10`）。超过就只列得分最高的 N 篇，按「必读 → 值得一读 → 其他相关」的层级截取；**全部命中仍会进历史库和 `reports/YYYY-MM-DD.json`**，所以把数值调大后执行 `run.py --rerender` 即可把其余几篇补回报告，不用重新联网抓取。

---

## 5. 开启微信推送

三个渠道任选，**填了密钥才生效**，没填的会自动跳过（不会报错）。

> 📖 **手把手的申请步骤见 [推送配置指南.md](推送配置指南.md)**（含 Server酱 扫码取 Key、关注服务号、填文件、自检四步）。配完用 `run.py --test-push` 立刻验证。

### Server酱（推荐，最简单）
1. 打开 <https://sct.ftqq.com>，用微信扫码登录。
2. 复制你的 `SendKey`（形如 `SCT123456xxxxxxxx`）。
3. 填入 `config.json`：
```jsonc
"push": {
  "enabled": true,
  "channels": {
    "serverchan": { "enabled": true, "sendkey": "SCT123456xxxxxxxx" }
  }
}
```
4. 微信关注「Server酱」服务号即可收到。免费版每天有额度，本工具每天只推 1 条，够用。

### PushPlus
1. 打开 <https://www.pushplus.plus>，微信扫码登录，复制 `token`。
2. 填入 `pushplus.token`，并把 `pushplus.enabled` 设为 `true`。

### Bark（iPhone）
1. App Store 安装 Bark，打开后复制那串 key（形如 `abcDEF123`）。
2. 填入 `bark.key`，把 `bark.enabled` 设为 `true`。默认服务器 `https://api.day.app`。

推送内容是**摘要卡片**：标题为「大气环境文献日报 YYYY-MM-DD：新增 N 篇，必读 M 篇」，正文列出最多 `push.max_items`（默认 6）条，格式为「标题（可点击）+ 期刊 · 日期 · 命中关键词」。完整内容在本地 Markdown 日报里。

> ⚠️ 安全提醒：推送密钥是明文密码。**不要写进 `config.json`**——那个文件是要提交到 Git 的。请在项目根目录建一个 `config.local.json` 放密钥，它已被 `.gitignore` 排除；在 GitHub Actions 里则用仓库 Secrets（见 [GitHub-公开与自动化.md](GitHub-公开与自动化.md)）。

---

## 6. 每天自动运行

### 方式 A：Windows 计划任务（已为你配置好）

**已经注册好了**，任务名 `JournalAlertDaily`，**每周一至周五 07:30** 运行，下次运行时间可在任务计划程序里看到。

查看任务：

```powershell
schtasks /query /tn "JournalAlertDaily" /fo LIST /v
```

立刻手动跑一次：

```powershell
schtasks /run /tn "JournalAlertDaily"
```

改时间（改成每天 08:00）：

```powershell
schtasks /create /tn "JournalAlertDaily" /tr "cmd.exe /c <项目目录>\run_daily.cmd" /sc daily /st 08:00 /f
```

改成只工作日（当前配置）：

```powershell
schtasks /create /tn "JournalAlertDaily" /tr "cmd.exe /c <项目目录>\run_daily.cmd" /sc weekly /d MON,TUE,WED,THU,FRI /st 07:30 /f
```

删除任务：

```powershell
schtasks /delete /tn "JournalAlertDaily" /f
```

计划任务跑完的痕迹分三个文件：

| 文件 | 内容 |
|---|---|
| `logs\jalert-YYYY-MM.log` | **最详细**：每本刊每个数据源的条数与耗时、失败原因。按月分文件 |
| `logs\run-last.log` | 最近一次运行的完整控制台输出（含崩溃 traceback），每次运行覆盖，不会无限增长 |
| `logs\runner.log` | 只记启动时间、选中的 Python 路径、退出码。快速判断「昨天到底跑没跑」 |

`run_daily.cmd` 的两种模式：**不带参数**（计划任务用）输出写进 `logs\run-last.log`；**带参数**（如 `--doctor`、`--check`）输出直接打在屏幕上，方便交互排查。

> **电脑不需要一直开着。** 详见下面的行为表。

**已为你调整过的任务设置**（笔记本上的必要修正，Windows 默认值会坑人）：

| 设置 | 默认值 | 已改为 | 原因 |
|---|---|---|---|
| 只在交流电下运行（DisallowStartIfOnBatteries） | true | **false** | 否则电池供电时 07:30 根本不会启动，笔记本上大概率错过 |
| 切换到电池时停止（StopIfGoingOnBatteries） | true | **false** | 否则运行途中拔电源会把抓取掐断 |
| 错过后尽快启动（StartWhenAvailable） | 未设置 | **true** | 睡眠/关机/未登录而错过 07:30 时，下次可用就补跑 |
| 唤醒计算机运行（WakeToRun） | 未设置 | **false** | 不会把睡眠中的电脑叫醒；想改见下 |
| 重复运行时 | — | 忽略新实例 | 上一次没跑完不会叠着跑 |

这几项都能在「任务计划程序」→ 双击该任务 → 「条件」和「设置」标签页里看到并随时改。

#### 07:30 时电脑处于不同状态，会发生什么

| 状态 | 结果 |
|---|---|
| 开机且已登录 | 准时运行，准时推送 |
| 睡眠 / 休眠 | **不会唤醒**（`WakeToRun=false`，且电池供电下 Windows 的唤醒定时器本身也是禁用的）；下次开机登录后由 `StartWhenAvailable` 补跑，推送时间即你开机的时间 |
| 完全关机 | 同上，下次开机登录后补跑 |
| 开着但没人登录（锁屏/注销） | 不会运行（任务是 InteractiveToken，要求已登录会话）；登录后补跑 |

**补跑不会漏文献。** 时间窗是自适应的：`max(配置的 3 天, 距上次成功运行的天数 + 1)`，上限为 `max_catchup_days`（默认 30 天）。所以电脑关了两周也不会漏掉中间的文献——下次运行会自动回抓。用 `--days N` 手动指定时关闭该自适应。

#### 想让睡眠中的电脑也在 07:30 自动醒来跑（可选）

```powershell
# 1) 打开任务的唤醒开关
$t = Get-ScheduledTask -TaskName "JournalAlertDaily"
$t.Settings.WakeToRun = $true
Set-ScheduledTask -TaskName "JournalAlertDaily" -Settings $t.Settings

# 2) 关键补充：默认只在插电时允许唤醒，电池下要单独打开
powercfg /setdcvalueindex SCHEME_CURRENT SUB_SLEEP RTCWAKE 1
powercfg /setactive SCHEME_CURRENT
```

实测你这台机器的唤醒定时器设置是：**交流电 启用 / 电池 禁用**，所以第 2 步不能省，否则拔了电源照样叫不醒。代价是 07:30 电脑会短暂亮起或转一下风扇；电脑完全关机时仍无法唤醒（只有极少数机型支持关机定时开机）。

如果把项目挪到别的目录，记得用上面的 `schtasks /create` 重新指一次路径。

### 方式 B：开机自启
把 `run_daily.cmd` 的快捷方式放进启动文件夹：
`Win+R` → `shell:startup` → 把快捷方式粘进去。缺点是每次开机才跑，不是固定时间。

### 方式 C：GitHub Actions（电脑不用开机）

仓库里已经带了一份 `.github/workflows/daily.yml`：云端每天 07:30（东八区）跑一次，推送照发，日报和去重台账自动提交回仓库。免费、不用挂机、不受「笔记本睡眠 / 关机 / 未登录」影响。

配置步骤（申请密钥 → 填仓库 Secrets → 手动跑一次验证）见 **[GitHub-公开与自动化.md](GitHub-公开与自动化.md)**。

> 注意：本机计划任务（方式 A/B）和云端 Actions 请**只开一个**。两边各有独立的去重台账，同时开会把同一批文献推两次。

---

## 7. 关于 Python（重要）

* 本工具**只用 Python 标准库**（`urllib`、`sqlite3`、`xml.etree`、`json`、`gzip`），**不需要 pip 安装任何东西**。这是刻意的设计：依赖越少，几年后越不容易因为环境变化而失效（也让它能在 GitHub Actions 上零安装直接跑）。
* 需要 **Python 3.10 或更高版本**。
* 所有网络访问都由 Python 完成，不要试图用 `curl` / PowerShell 复现——很多机器上这些客户端被代理或安全软件挡住，而 Python 能通。
* `run_daily.cmd` 会自动找 Python，**你不用改脚本**。查找顺序：
  1. `py -3` 启动器（官方安装包会一起装上）
  2. PATH 里的 `python.exe`
  3. `%LOCALAPPDATA%\Programs\Python`、`C:\Program Files\Python`、`C:\Python` 等常见位置
  4. `%USERPROFILE%\.dsh\dsh-runtimes\*`（如果装了 DSH）

  每一步都会实测能否 `import sqlite3, urllib.request`，所以会自动挡掉微软商店那个「假的 python」。换电脑、换用户名都不用改脚本，详见 [部署到新电脑.md](部署到新电脑.md)。

---

## 7.5 配置的分层（`config.json` vs `config.local.json`）

`config.json` 是**可以公开分享**的那一份：期刊、关键词、阈值、分级规则。**里面不放任何密钥。**

密钥放 `config.local.json`（与 `config.json` 同目录，已被 `.gitignore` 排除）。它会被深合并到 `config.json` 之上，写多少层覆盖多少层，不用把整个 `push` 段抄一遍：

```jsonc
// config.local.json —— 只写要覆盖的部分
{
  "push": {
    "channels": {
      "serverchan": { "enabled": true, "sendkey": "SCT..." }
    }
  }
}
```

在 GitHub Actions 里则完全不碰文件，用仓库 Secrets 通过环境变量注入（`JALERT_SERVERCHAN_SENDKEY` 等）。环境变量优先级最高，会盖掉上面两层。`run.py --doctor` 会告诉你密钥最终是从哪儿来的。

---

## 8. 数据源说明（2026-10-04 实测）

**结论：16 本刊里 15 本有可用 RSS；ACS 的 ES&T 已停用 RSS，由 OpenAlex + Crossref 双保险；每一本刊都至少有两个独立数据源覆盖，所以任何单一源失效都不会漏掉整本刊。**

| 期刊 | RSS | OpenAlex | Crossref |
|---|---|---|---|
| Nature | ✅ 75 | ⏱ 偶发超时 | ✅ 5 |
| Science | ✅ 45 | ✅ 42 | ✅ 46 |
| Nature Climate Change | ✅ 8 | ✅ | ✅ 1 |
| Nature Geoscience | ✅ 8 | ⏱ 偶发超时 | ✅ 1 |
| Nature Sustainability | ✅ 8 | ✅ | ✅ |
| Nature Cities | ✅ 8 | ✅ 1 | ✅ 1 |
| Nature Communications | ✅ 8 | ✅ 34 | ✅ 61 |
| Science Advances | ✅ 83 | ⏱ 偶发超时 | ✅ 83 |
| Earth's Future | ✅ 9 | ✅ 4 | ✅ 30 |
| Atmospheric Chemistry and Physics | ✅ 20 | ✅ 5 | ✅ 5 |
| Environmental Science & Technology | ❌ ACS 已停 RSS | ✅ 23 | ✅ 25 |
| Environmental Research Letters | ✅ 10 | ✅ 5 | ✅ 14 |
| Geophysical Research Letters | ✅ 26 | ✅ 5 | ✅ 13 |
| Journal of Geophysical Research: Atmospheres | ✅ 14 | ✅ 5 | ✅ 6 |
| Atmospheric Environment | ✅ 55 | ✅ 1 | ✅ 60 |
| Remote Sensing of Environment | ✅ 86 | ✅ 7 | ✅ 60 |

数字是实测某一天时间窗内的条数，仅代表量级。⏱ 表示海外 API 偶发连接超时（重试后多数会成功，即便一直失败也有另外两个源兜底）。

踩坑记录（以后加期刊时有用）：

* **Wiley / AGU 的 RSS 地址必须用「不带横线」的 ISSN**：`https://agupubs.onlinelibrary.wiley.com/feed/19448007/most-recent`。带横线的 `1944-8007` 一律 404，这一条卡了很久。
* **ACS（ES&T）已停止提供 RSS**，落地页里也没有 feed 链接，只能靠 OpenAlex + Crossref。
* **ScienceDirect（Elsevier）的 RSS 可用**：`https://rss.sciencedirect.com/publication/science/<不带横线的ISSN>`，而且条数很多（Atmospheric Environment 55 条、RSE 86 条）。
* **Copernicus（ACP）**：`https://acp.copernicus.org/xml/rss2_0.xml`。
* **IOP（ERL）**：`https://iopscience.iop.org/journal/rss/1748-9326`。
* **Nature 的 RSS 里混有大量新闻/评论/播客**（DOI 前缀 `10.1038/d41586`），已由 `exclude_doi_prefixes` 过滤掉，只留研究论文。
* **Elsevier 的日期是「期号日期」，可能在未来**（例如今天 10-04，条目显示 12-01）。报告里这类条目会自动标注「在线预发表」，排序时也按今天处理，不会顶到最前面。
* **Crossref 的日期字段可能只有年份**（`date-parts: [[2026]]`），早期版本会因此崩溃，现已容错。
* **OpenAlex/Crossref 对国内网络偶发超时**，所以设了 45 秒超时 + 重试，并把抓取做成 6 路并发（顺序抓取要 16 分钟，并发后约 4 分钟）。


---

## 9. 故障排查

| 现象 | 原因与处理 |
|---|---|
| 报告里「数据源状态」出现 ❌ | 正常现象，单个源失败不影响整体。常见原因：出版商反爬（ACS/IOP/ScienceDirect 常见 403）、对方临时故障。会靠 OpenAlex/Crossref 兜底。 |
| 一次运行时间很长 | OpenAlex 大刊（如 Science、Nature Communications）返回条数多，加上失败重试会慢。可以 `--sources rss` 只用 RSS 提速，或在 `window.max_items_per_journal` 调小。 |
| 推送没收到 | 看 `logs/jalert-YYYY-MM.log` 里 `push ... FAIL` 那行。最常见是 SendKey 填错，或微信没关注服务号。 |
| 报告里空空的 | 看日志里 `keyword matched X/Y`。若 Y 很大而 X=0，说明关键词 `terms` 没覆盖到实际用词，去 `config.json` 加词。 |
| 想重看某天 | 直接打开 `reports\YYYY-MM-DD.md`；历史台账查 `state\seen.sqlite` 的 `articles` 表。 |
| 想重新推送一次 | 删掉 `state/seen.sqlite` 里对应行即可（或简单删库重来，会重新报告时间窗内所有文献）。 |
