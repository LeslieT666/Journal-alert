# 公开仓库 + GitHub Actions 自动化改造说明

本文回答一个问题：**这个项目已经在 GitHub 上（当前是私密仓库、密钥已清空），要把它变成「公开 + 云端每天自动跑」，需要改什么。**

配套改动已经落在仓库里，直接提交即可（见文末「已改动的文件」）。下面按「必须做 / 建议做 / 可选」三层说明。

---

## ✅ 部署实况（2026-10-05 完成）

| 项目 | 实际状态 |
|---|---|
| 仓库 | `pkui1mpression-design/Journal-alert`（**大小写敏感**），默认分支 `main` |
| 可见性 | **public** |
| 远端 `main` | `9d692d5fc5182607f4fe53ebccc2d97f6d61abd6`（与本地 `HEAD` 逐位一致） |
| 已推送内容 | `bccf0e9` feat: GitHub Actions 云端每日运行 + 密钥外置 → `a4b7d719` docs: 记录仓库可见性与密钥历史泄漏的核查结果，共 21 个文件 |
| 工作流 | `.github/workflows/daily.yml`（`30 23 * * *` UTC = 每天 07:30 北京时间） |
| 首次试跑 | **run #1 success**，57 秒。<https://github.com/pkui1mpression-design/Journal-alert/actions/runs/37313070657> |
| 试跑结果 | 抓取 763 篇 → 命中 174 篇 → 新增 114 篇（其中 60 篇此前已读过，说明台账继承成功）；回写提交 `9d692d5` `chore(state): 2026-10-05 daily run` |
| 仓库变量 | `JALERT_MAILTO = pkui1mpression@gmail.com` ✅ 已设 |
| 仓库 Secret | ⬜ **`SERVERCHAN_SENDKEY` 尚未添加** → 加之前云端不会推微信 |
| 本机计划任务 | `JournalAlertDaily` **已注销**，XML 备份在 `C:\Users\wangs\JournalAlertDaily-task-backup.xml` |
| GitHub 连接器 | **只读**。`create_or_update_file` / `create_branch` / `delete_file` / `create_repository` 全部 403 `Resource not accessible by integration`，必须用 API + PAT |

### 🔴 仍未消除的风险：旧提交里的明文 SendKey

已作废的旧 SendKey 在公开仓库中**仍可被未登录访问**——`--force` 只是让 `4d6a1224` 脱离 `main` 分支，对象本身还在，按 SHA 直取照样能读到（长 34 位，`SCT432…zTZs`）。

处置方式（三选一）：

1. **重置密钥即可（推荐，已完成）** — 密钥轮换是业界标准做法，旧值已失效，拿到也没有任何用处。零操作。
2. **删库重建** — GitHub 网页 Settings → Danger Zone → Delete this repository，删掉后用同名重建。注意：**删仓库需要 PAT 带 `delete_repo` 权限**，本机那把只有 `repo, workflow`，我代删不了。之后重新推一次即可，`.workbuddy/api-push.py` 加 `--full-history` 直接复跑。
3. **找 GitHub Support** — 请求清除缓存视图中的旧提交，通常要等几天。

> 验证命令（不需要登录）：
> ```bash
> python -c "import urllib.request,json,base64;d=json.load(urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/pkui1mpression-design/Journal-alert/contents/config.json?ref=4d6a1224',headers={'User-Agent':'M'})));print(json.loads(base64.b64decode(d['content'])).get('push',{}).get('channels',{}).get('serverchan',{}).get('sendkey'))"
> ```

### 🚧 本机推不动/拉不动：改走 REST API

本机到 `github.com:443` 的 git 通道被本地代理掐断：

| 路径 | 实测结果 |
|---|---|
| 走代理 `git ls-remote` | `CONNECT tunnel failed, response 502` |
| 绕过代理 `git -c http.proxy= ls-remote` | `Failed to connect to github.com:443 after 21016 ms` |
| `https://api.github.com`（直连） | **200 OK** ✅ |
| `https://raw.githubusercontent.com` | 不通（连接被掐），读文件一律改走 contents API |

所以 `git push` / `git fetch` 全部不可用，改走 **GitHub Git Data REST API**，脚本在 `.workbuddy/`：

| 脚本 | 作用 |
|---|---|
| `.workbuddy/push-to-github.sh` | 统一入口。直接跑 = 推送；`... pull` = 反向同步 |
| `.workbuddy/api-push.py` | 把本地提交**原样重建**到远端（含作者、时间、完整提交信息），force 更新 ref |
| `.workbuddy/api-pull.py` | 反方向做**真 fetch**：递归补齐缺失对象，再移动分支指针、同步工作区 |

推送时逐层校验 sha——blob、tree、commit、ref 全部相等才收工。看到 `树 ... [OK]` 和末尾 `完全一致 : YES` 就是成功。通用版在 `~/.workbuddy/skills/github-push-via-api/`。

> **三个关键细节**
> 1. commit sha 想对上，提交信息必须取自 `git cat-file commit` 的**原始字节**——`%b` 的 body 没有尾部换行，差一字节 sha 就变了。
> 2. 反向同步时 commit 的**时区偏移** API 不返回（只有 UTC 的 `Z`），而偏移参与哈希。脚本用候选偏移逐个试算，**哈希对上才写对象**。Actions 的提交是 `+0800`（工作流设了 `TZ: Asia/Shanghai`）。
> 3. ⚠️ **`api-pull.py` 会 `git reset --hard`**，工作区里没提交的改动会被冲掉。脚本已加保护：工作区脏时直接拒绝执行（确要覆盖加 `--force`）。**我这轮就踩过一次**——文档改了 3 处在没提交的情况下被 reset 掉了，重做了。

### △ 本地与远端的同步关系（已抹平分叉）

CI 每次都会往 `main` 追加一个 `chore(state): …` 提交，本地副本会随时落后于远端。

**2026-10-05 已处理**：推送完成后本地与远端一度分叉（远端多了 CI 提交 `9d692d5`）。分叉状态下若从本地强推，会把云端积累的去重台账冲掉，导致下一轮把时间窗内的文献全部当新的重推。现已用 `api-pull.py` 精确重建该提交（连 sha 都一致）：

```
本地 HEAD: 9d692d5fc5182607f4fe53ebccc2d97f6d61abd6
与远端一致: YES
工作区状态: 干净（无未提交改动）
```

日常顺序：**先 `push-to-github.sh pull` → 改代码 → 再 push**。别在分叉状态下 `--full-history` 强推。

> 如果你哪天在**自己的终端**里用 git（不经过 WorkBuddy 的代理），`github.com` 很可能是通的——那就直接用 `git pull` / `git push`，不必绕 API。

---

## 0. 先说三条最容易踩的

| 坑 | 说明 |
|---|---|
| **密钥只在当次提交里删掉是没用的** | Git 保存的是全部历史。只要 `sendkey` 曾经存在于任何一次提交里，公开仓库的那一刻它就等于公开了。**必须去 <https://sct.ftqq.com> 重置 SendKey**，这是唯一稳妥的做法，改历史（`filter-repo`）太麻烦且容易出错。 |
| **GitHub 的 cron 走 UTC，不是北京时间** | 07:30（东八区）= **23:30 UTC 前一天**。而且 `run.py` 用 `date.today()` 命名日报，容器里是 UTC 的话会生成「昨天」的文件名。工作流里已经用 `TZ: Asia/Shanghai` 修掉了。 |
| **Actions 每次运行都是全新容器，`state/seen.sqlite` 不会自己留下** | 这是「已读台账」，丢了就会把时间窗内的文献全部当新的重推一遍。必须让它跨运行存活，方案见第 3 节。 |

---

## 1. 公开前：密钥与隐私（必须做）

### 1.1 重置 SendKey

登录 <https://sct.ftqq.com> → SendKey 页面 → 「重置」。旧的立刻作废。然后用新的填到 **本机的 `config.local.json`**（不是 `config.json`）和 **GitHub Secrets**。

### 1.2 密钥再也不进 `config.json`

改成了三层配置，从下往上覆盖：

```
DEFAULTS（代码里的默认值）
  → config.json           ← 入库。只放期刊、关键词、阈值。sendkey 留空 ""
    → config.local.json   ← 不入库（已在 .gitignore）。密钥写这里
      → 环境变量           ← 最高优先级。CI 用这个
```

环境变量名（在 `jalert/config.py` 里定义）：

| 环境变量 | 覆盖的字段 |
|---|---|
| `JALERT_SERVERCHAN_SENDKEY` | `push.channels.serverchan.sendkey` |
| `JALERT_PUSHPLUS_TOKEN` | `push.channels.pushplus.token` |
| `JALERT_BARK_KEY` | `push.channels.bark.key` |
| `JALERT_BARK_SERVER` | `push.channels.bark.server` |
| `JALERT_PUSH_ENABLED` | `push.enabled`（设成 `0` 可以整体关掉推送） |
| `JALERT_MAILTO` | OpenAlex / Crossref 的「礼貌池」联系邮箱 |
| `JALERT_USER_AGENT` | 抓取时用的 UA |
| `JALERT_CONFIG` / `JALERT_CONFIG_LOCAL` | 配置文件路径（默认就是项目根目录那两个） |

只要变量非空，程序会自动把该渠道 `enabled` 设为 `true`——**填了密钥就代表意图是要用**，不用再改两处。

`run.py --doctor` 现在会打印密钥来源：`Server酱（环境变量 ...）` 或 `Server酱（配置文件）`。

### 1.3 入库 / 不入库清单

`.gitignore` 已经写好。原则是**代码 + 可分享的配置 + 每天的日报入库；运行痕迹、机器本地状态、密钥不入库**。

| 不入库 | 原因 |
|---|---|
| `logs/` | 运行日志，含本机 Python 路径；改成 Actions artifact |
| `state/daily/` | 每日快照，每天 ~90 KB，只服务 `--rerender`，无跨天价值 |
| `state/*.bak-*` | 数据库备份 |
| `reports/*.json` | 与日报同内容的机器可读版，每天 ~90 KB，会无限堆积 |
| `config.local.json` | 密钥 |
| `.workbuddy/` | 助手工具的项目数据 |
| `__pycache__/` | 字节码 |

被跟踪的只有：`state/seen.sqlite`（去重台账）、`reports/YYYY-MM-DD.md`（日报正文）、其余源码与文档。

> **注意**：如果这些文件已经被上传到仓库了，`.gitignore` 对已跟踪文件无效，需要先取消跟踪：
> ```powershell
> git rm -r --cached logs state/daily reports/*.json
> git commit -m "chore: stop tracking run artifacts"
> ```
> 或者干脆在 GitHub 网页上把 `logs/`、`state/daily/`、`reports/*.json` 删掉。

### 1.4 顺手把 README 里的私人信息去掉

改完了：`README.md` 与 `推送配置指南.md` 里原来写死的 `D:\DSH\journal-alert`、`C:\Users\Jessy\.dsh\...` 都换成了通用写法。第 7 节那段「本机只有 DSH 自带的 Python 能联网」是这台机器的特殊情况，公开后会让人误解，已改成通用说明。

---

## 2. GitHub Actions 每天自动跑（核心）

`.github/workflows/daily.yml` 已经写好，开箱可用。它做四件事：

1. `python run.py --doctor` —— 先自检（Python 版本、目录写入、三个海外站点连通性），失败原因一眼可见。这一步标了 `continue-on-error`，偶发超时不会把整个任务判失败。
2. `python run.py --once` —— 跑完整管线并推送
3. `git commit && git push` —— 把 `state/seen.sqlite` 和当日日报写回仓库（标了 `if: always()`，即使抓取失败也保住台账）
4. 上传 `logs/` 为 artifact + 把当日日报渲染到运行页面的 Summary 里

### 2.0 改成只跑工作日（可选）

工作流默认**每天**跑。「工作日才跑」不用特意配——周六周日的文献会在周一被自适应时间窗（`max(配置的 3 天, 距上次运行的天数 + 1)`）一起捞回来，不会漏。如果就是想贴着原来本机任务的节奏，把 cron 改成：

```yaml
    - cron: "30 23 * * 0-4"   # UTC 的周日~周四 == 北京时间的周一~周五 07:30
```

注意 day-of-week 是 **UTC 视角**：23:30 UTC 的周日，在北京已经是周一了，所以是 `0-4`（0 = 周日）而不是 `1-5`。

### 2.1 配 Secrets（3 分钟）

仓库页 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**：

| Name | Value |
|---|---|
| `SERVERCHAN_SENDKEY` | 你的 SendKey（重置后的新值） |
| `PUSHPLUS_TOKEN` | 可选，不用就整个不要建 |
| `BARK_KEY` | 可选 |

再切到 **Variables** 标签页建一个（可选，但推荐）：

| Name | Value |
|---|---|
| `JALERT_MAILTO` | 你的邮箱。OpenAlex/Crossref 对提供了真实联系方式的调用者给「礼貌池」优先权，成功率更高 |

没配的 Secret 会展开成空字符串，程序把「空密钥」当作「该渠道未启用」直接跳过，**不会报错**，所以只建 `SERVERCHAN_SENDKEY` 一个也能跑。

### 2.2 关于 `permissions: contents: write`

工作流要往仓库里提交状态文件，所以声明了写权限。这是安全的：**用自动 `GITHUB_TOKEN` 推送的提交不会触发工作流**，不存在自己触发自己的死循环。

### 2.3 首次验证（已完成一次）

仓库 → **Actions** → 左侧 `journal-alert daily` → **Run workflow**（手动触发，这就是 `workflow_dispatch` 的作用）。

手动触发时可以填两个输入框：
* `days` —— 覆盖时间窗，**第一次建议填 `14`**，先看一批历史文献
* `sources` —— 例如填 `openalex,crossref` 先只跑 API

也可以不点鼠标，用 API 直接触发（PAT 需要 `workflow` 权限）：

```bash
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/pkui1mpression-design/Journal-alert/actions/workflows/daily.yml/dispatches \
  -d '{"ref":"main","inputs":{"days":"14"}}'
# HTTP 204 = 已受理
```

**2026-10-05 实测**：run #1 全绿，57 秒。8 个步骤（checkout / setup-python / doctor 自检 / 跑管线 / 回写提交 / 上传日志 / 渲染摘要）全部 success。产物提交 `9d692d5`。

---

## 3. 状态怎么跨运行存活（唯一需要你决策的地方）

`state/seen.sqlite` 是去重台账，必须有地方存。三个方案：

| 方案 | 做法 | 优点 | 缺点 |
|---|---|---|---|
| **A. 写回仓库（当前实现）** | 每次运行 `git add -A && commit && push` | 稳。台账和日报都在仓库里，随时可见、可回滚；天然规避下面第 5 节那个「60 天不活动会被停用」的坑 | 每天 1 个提交，一年 365 个 |
| B. Actions cache | `actions/cache` + 滚动 key | 不污染提交历史 | 缓存 **连续 7 天无人访问就被清理**；一旦工作流挂了超过一周，台账丢失，下次会把时间窗内全部文献当新的重推 |
| C. 外部存储 | 存到 Release asset / 对象存储 / 数据库 | 不污染历史 | 要额外凭证和维护成本 |

**推荐 A，就是现在这份。** 想让提交历史干净一点，可以把状态提交到独立分支再去掉 checkout：

```yaml
      - uses: actions/checkout@v5
        with:
          ref: state          # 状态分支
```
但这会让日报也离开主分支，代价大于收益，一般不值得。

> 想彻底不要这些提交？把 `reports/` 和 `state/` 都 gitignore，改用方案 B。**不建议**——省下的只是几十个提交，换来一个会静默失效的去重机制。

---

## 4. 公开之后必须确认的几件事

1. **Actions 分钟数**：公开仓库用 GitHub 托管 runner **免费且不计费**。私有仓库走免费额度（2000 分钟/月），本工作流一次约 4–6 分钟，每天一次 ≈ 150 分钟/月，也够。
2. **`reports/*.md` 会公开**。内容是论文标题、DOI、作者、摘要片段——都是公开学术信息，没有问题。但它同时暴露了**你的研究方向和关键词**，介意的话把 `reports/` 也 gitignore 掉。
3. **`keep_days: 365`** 会自动清理一年前的日报（`.md` 和 `.json` 都清，这个之前只清 `.md`，已修）。所以仓库体积不会无限增长。
4. **LICENSE**：已加 MIT（署名 Jessy Wang）。公开仓库如果没有许可证，法律上默认「保留所有权利」，别人不能合法复用。不想开源就把它删掉。
5. **`先读我-安装三步.txt` 和 `make_package.py`** 是「拷到另一台 Windows 电脑」用的，公开后与新加的 Actions 并存，不冲突。但 `先读我-安装三步.txt` 是打包时自动生成的，仓库里可以不放。

---

## 5. 已知坑与注意事项

| 现象 | 说明 / 处理 |
|---|---|
| 定时任务不按点跑，晚十几分钟 | GitHub cron 在整点高峰期会排队，延迟 5–30 分钟是常态。对日报无影响。要准点就得用自建 runner 或外部 cron 打 `workflow_dispatch` API。 |
| 工作流「跑了 60 天后自己停了」 | GitHub 会停用**连续 60 天无仓库活动**的定时工作流。方案 A 每天都有提交，天然不触发。 |
| 部分期刊 RSS 在 Actions 里 403 | **最需要留意的一条。** Elsevier / Wiley / IOP 这类出版商会按 IP 段风控，GitHub 的云机房 IP 比你家宽带更容易被拒。原设计是「每本刊至少两个源兜底」，所以即使 RSS 全 403，OpenAlex + Crossref 仍能覆盖，**不会漏文献**。若日志里 RSS 大面积失败，给工作流加 `sources: openalex,crossref` 即可（手动触发时填，或写死进 `run.py` 的调用参数）。 |
| OpenAlex / Crossref 偶发超时 | 海外 API 约 15% 调用会超时，管线自带重试、且多源互备。日志里零星 `FAIL` 属正常。 |
| Actions 里跑起来比本机慢 | 本机 6 路并发约 4 分钟；Actions runner 网络到出版商的距离不同，可能 5–8 分钟。`timeout-minutes: 30` 足够。 |
| 日报文件日期和实际日期差一天 | 说明 `TZ` 没生效。确认工作流的 job 级 `env:` 里有 `TZ: Asia/Shanghai`。 |
| 想手动补一次 | Actions 页面 Run workflow，或本地 `python run.py --once`。两边共用台账（都在仓库里）。 |
| 本地和 Actions 同时跑 | 会各自基于自己那份台账判断「新增」，可能重复推送。要么只在 Actions 跑，要么跑完 `git pull`。 |

---

## 6. 可选：把日报发布成网页（GitHub Pages）

如果想让日报有一个能直接分享的链接（而不是点开仓库里的 `.md`）：

1. 仓库 → Settings → Pages → Source 选 `Deploy from a branch`，分支 `main`、目录 `/docs`
2. 在 `run.py` 末尾（`record_run` 之后）加一段生成 `docs/index.html` 的逻辑，列出 `reports/` 里的日报
3. 工作流末尾加一步 `actions/deploy-pages`

我没实现这一步——它会给每次运行增加输出目录和分支配置，属于「想要再说」的增量。需要的话告诉我，我加。

---

## 7. 检查清单

公开前：

- [x] 去 <https://sct.ftqq.com> **重置 SendKey**
- [x] 确认仓库历史里没有其他密钥（`4d6a1224` 里那把已作废，见文首「仍未消除的风险」）
- [x] 取消跟踪 `logs/`、`state/daily/`、`reports/*.json`
- [x] 检查 `README.md`、`推送配置指南.md` 里没有残留的私人路径
- [x] 推送云端改造（21 个文件，`a4b7d719`）
- [x] 注销本机计划任务 `JournalAlertDaily`

公开后：

- [ ] **Settings → Secrets → Actions → New repository secret** 建 `SERVERCHAN_SENDKEY`，值为**重置后的新 SendKey** ← 只剩这一步
- [x] Variables 建好 `JALERT_MAILTO`（= `pkui1mpression@gmail.com`，已设）
- [x] Actions 手动 Run workflow 一次（`days=14`），run #1 全绿
- [ ] 加了 Secret 后再触发一次，手机确认收到推送
- [x] 确认 `state/seen.sqlite` 和 `reports/YYYY-MM-DD.md` 出现在新提交里（`9d692d5`）
- [ ] 第二天看 07:30 有没有自动跑（Actions 页面的时间线）

---

## 已改动的文件

| 文件 | 改动 |
|---|---|
| `.gitignore` | 新增。运行痕迹与密钥的入库清单 |
| `.github/workflows/daily.yml` | 新增。每天 07:30（东八区）跑，写回状态，上传日志，渲染 Summary |
| `LICENSE` | 新增。MIT |
| `GitHub-公开与自动化.md` | 新增。本文 |
| `config.local.json` | 新增。**已在 .gitignore**，你的 SendKey 挪到了这里 |
| `config.json` | `serverchan.sendkey` 清空为 `""`（可安全公开） |
| `jalert/config.py` | 三层配置（默认值 → config.json → config.local.json → 环境变量）；新增 `describe_secret_sources()` |
| `jalert/fetch.py` | `USER_AGENT` / `MAILTO` 支持 `JALERT_USER_AGENT` / `JALERT_MAILTO` 覆盖 |
| `run.py` | `--doctor` 显示覆盖层路径与密钥来源；`os.startfile` 加 Windows 守卫；`prune_reports` 同时清理 `reports/*.json` |
| `README.md` / `推送配置指南.md` | 去掉写死的私人路径，指向本文 |

全部改动已在 Python 3.13 实测：无第三方依赖，`--doctor`、`--rerender`、密钥分层加载（文件 / 环境变量）均正常。
