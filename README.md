# skillshare

這是個人使用的 AI CLI 設定集合，提供可重複使用的 `skills`、`agents` 與 RTK（命令輸出整理）整合，並透過 [`skillshare`](https://github.com/runkids/skillshare) 將單一來源同步到 Claude Code、Codex CLI 與 Pi。

本儲存庫不是獨立應用程式；主要內容是 Markdown、YAML、TOML、Python 與 JavaScript 設定檔。`config.yaml` 是同步規則的來源，`skills/`、`extras/` 與 `extensions/` 則是實際要管理的內容。

## 提供內容

- `skills/`：AI 可使用的技能，每個技能以 `SKILL.md` 定義用途與執行規則，並可附帶參考文件與腳本。
- `agents/`：可同步到不同 AI CLI 的代理設定；共用模板會依目標工具轉換成對應格式。
- `rtk`：透過 PreToolUse hook 將適合的 Bash 指令交給 `rtk` 處理；未安裝 `rtk` 時會保留原指令，不影響基本操作。

## 快速開始

目前設定預期此儲存庫位於 `~/.config/skillshare`。確認 `skillshare` 已安裝並在 `PATH` 後：

```bash
cd ~/.config/skillshare

# 查看來源、目標與同步狀態
skillshare status

# 預覽所有技能、代理與 extras 的變更
skillshare sync --dry-run

# 先掃描安全性，再套用到所有目標
skillshare audit --no-tui --yes
skillshare sync --all

# 確認同步後是否仍有差異
skillshare status
skillshare diff --stat
```

常用的部分同步指令如下：

```bash
skillshare sync          # 只同步 skills
skillshare sync agents   # 只同步 agents
skillshare sync --all    # 同步 skills、agents 與 extras
```

若儲存庫放在其他路徑，請同步調整 `config.yaml` 中 `sources.skills` 與各 `extras[].source` 的 `~/.config/skillshare/...` 路徑，或建立對應的 project-mode 設定。

## 如何使用技能

同步完成後，各 AI CLI 會從自己的目標目錄載入技能。呼叫語法依工具而異，例如：

```text
Claude Code：/<技能名稱>
Codex CLI：  $<技能名稱>
```

技能名稱就是 `skills/<name>/` 的目錄名稱。每個技能的主要說明與執行規則都在該目錄的 `SKILL.md`。代理則由各 AI CLI 的 agents 目錄載入。

`SKILL.md` 的 `disable-model-invocation` 會控制是否只能由使用者明確呼叫：

- `true`：只能由使用者明確呼叫。
- `false` 或未設定：模型可依描述自動判斷是否使用。

每個技能的詳細使用方式請直接查看對應的 `SKILL.md`；不要直接修改同步後的目標檔案。

## 目錄結構

```text
.
├── config.yaml                         # skillshare 的來源、目標與 extras 設定
├── skills/
│   ├── <name>/SKILL.md                  # 技能主文件
│   ├── <name>/agents/openai.yaml        # 可選的 agent 顯示資訊
│   ├── <name>/references/               # 技能按需讀取的參考文件
│   ├── <name>/scripts/                  # 技能使用的輔助腳本
│   └── .metadata.json                   # 外部技能的來源、版本與雜湊資訊
├── extras/
│   ├── all/agents/                      # 共用 agents
│   ├── all/hooks/                       # 共用 hooks
│   ├── claude/                          # Claude Code 指令與 agents
│   └── codex/                           # Codex CLI 指令與 agents
└── extensions/
    ├── agents_convert_tool/             # Markdown/YAML 轉換核心
    ├── claude-agents/                   # 轉成 Claude agent Markdown
    └── codex-agents/                    # 轉成 Codex agent TOML
```

## 同步目標與例外

`config.yaml` 目前使用 `merge` 模式，將來源內容合併到下列目標：

| 目標 | 技能路徑 | 備註 |
| --- | --- | --- |
| Claude Code | `~/.claude/skills` | 依設定檔的排除規則同步。 |
| Codex CLI | `~/.codex-cli/skills` | 同步來源中的技能。 |
| Pi | `~/.pi/agent/skills` | 同步來源中的技能。 |

`extras` 另外管理下列內容：

- Claude 指令、`CLAUDE.md`、設定與 status line：`extras/claude/instructions` → `~/.claude`。
- Codex 指令、`AGENTS.md` 與 `config.toml`：`extras/codex/instructions` → `~/.codex-cli`。
- 共用 agents：`extras/all/agents` 依目標工具轉換到 agents 目錄。
- RTK hook：`extras/all/hooks` 同時同步到 Claude 與 Codex 的 hooks 目錄。

若要調整哪些目標接收哪些技能，請修改 `config.yaml` 的 `targets` 或排除規則，再執行 `skillshare sync --dry-run` 檢查結果。

## 新增或修改內容

### 新增技能

可以使用 CLI 建立模板：

```bash
skillshare new my-skill --global
```

接著編輯 `skills/my-skill/SKILL.md`，必要時加入 `references/`、`scripts/` 或 `agents/openai.yaml`。完成後建議依序執行：

```bash
skillshare audit ./skills/my-skill --no-tui
skillshare sync --dry-run
skillshare sync --all
```

外部技能可用 `skillshare install <來源>` 加入來源目錄；若要更新已追蹤的外部來源，先用 `skillshare check` 查看，再依需求執行 `skillshare update`。

### 新增或修改 agent

共用 agent 放在 `extras/all/agents/`，專用 agent 放在對應的 `extras/<target>/agents/`。共用模板可使用 target-specific frontmatter，`claude-agents` 與 `codex-agents` extension 會將它轉換成目標工具格式。

```markdown
---
name: example
description: Handle a bounded example task.
claude:
  model: sonnet
codex:
  model: gpt-5.3-codex-spark
---

Mission: Describe the agent's bounded outcome and validation target.
```

請修改來源檔，不要直接修改 `~/.claude` 或 `~/.codex-cli` 中的同步結果。

## 驗證

這個儲存庫目前沒有統一的套件建置流程。修改內容後，可用下列指令檢查格式與同步狀態：

```bash
git diff --check
skillshare status
```

部分影像處理腳本需要 Python 3、`Pillow` 或 `numpy`；這些依賴只在實際執行相關腳本時需要。

同步前可用下列指令檢查檔案層級差異：

```bash
skillshare diff --stat
skillshare diff --patch
```

由於目標採 `merge` 模式，若目標目錄有本機修改，請先檢查差異；`skillshare sync --force` 可能覆寫目標中的本機內容。
