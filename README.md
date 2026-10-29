# DualSubtitle · 中英双语文本 / Chinese–English dual-language text

DARK SOULS III 1.15.0 — 以中文显示时下方给出英文，以英文显示时下方给出中文。

**[中文](#中文) · [English](#english)**

---

## 中文

把游戏显示语言**再加一份另一语言的文本**：显示简体中文时，英文跟在后面（换行或 `中文 / English`）；显示英文时，中文跟在后面。只改 `msg\` 下的文本包，不动 exe、params、存档，可随时还原。

### 安装

1. 下载或 clone 本仓库（`msg\` 里就是生成好的文本包），整个文件夹放到任意位置。
2. 关闭游戏。
3. 运行 `install.ps1`（右键 → 使用 PowerShell 运行，或 `powershell -ExecutionPolicy Bypass -File install.ps1`）。脚本会自动到 Steam 库里找 `DARK SOULS III\Game`；找不到就直接传路径：`install.ps1 -GameDir "X:\...\DARK SOULS III\Game"`。
4. 游戏需为**松散文件**环境（UXM / Nuxe 解包过，`Game\msg\` 里是散开的文本包），否则替换的文件不会被读取。
5. 离线启动游戏。若另有 mod 也改 `msg`，两者会互相覆盖。

卸载：`restore.ps1` 按安装时写的清单把每个文件还原成**安装前的原始字节**；`restore.ps1 -DryRun` 只看不改。有文件还原不了时清单和备份会保留，可以重试。

### 成品实际覆盖哪些文本

以仓库里的 `tools\dualsub.config.json` 为准 —— 默认只开两类：

| 文本类别 | 默认 | 说明 |
|---|---|---|
| 会話（NPC 对话） | **开** | 全部条目双语 |
| ムービー字幕（过场字幕） | **开** | 全部条目双语 |
| イベントテキスト（事件文本） | **开**（部分生效） | 约 335 条目双语，其余条目两语言文本位置不同，未合并 |
| 菜单、按键提示、道具名/说明、帮助文本、血文字、系统消息 | 关 | 保持游戏原本的单语显示 |

想让这些也双语，改 `tools\dualsub.config.json` 后重新生成（见下）。长描述类受界面高度限制，建议用 `"en_only"` 只换成英文。

### 重新生成

需要 **Python 3.9+** 和 **Yabber**（<https://github.com/JKAnderson/Yabber/releases>，解压即可）。

```powershell
# 告诉脚本 Yabber 在哪（三选一）
#   1) build.ps1 -YabberDir "D:\Tools\Yabber 1.3.1"
#   2) 在 tools\dualsub.config.json 里填 "yabber_dir": "D:\\Tools\\Yabber 1.3.1"
#   3) 设环境变量 YABBER_DIR
powershell -ExecutionPolicy Bypass -File build.ps1 -YabberDir "D:\Tools\Yabber 1.3.1"
powershell -ExecutionPolicy Bypass -File install.ps1
```

配置项：

| 键 | 作用 |
|---|---|
| `yabber_dir` | Yabber 所在文件夹（含 `Yabber.exe` 与 `Yabber.DCX.exe`） |
| `primary` / `secondary` | 主/副语言目录，默认 `zhocn` / `engus` |
| `separator` | 默认分隔符，默认换行 |
| `default_enabled` | 未列出的类别是否默认合并 |
| `skip_merge_texts` | 不合并的短词（是 / 否 / 确定 / 取消），避免菜单错位 |
| `categories` | 每类开关：`true` 双语 · `"off"`/`false` 保持原样 · `"en_only"` 只换英文 · `"append"` 强行追加 |

`build.ps1` 以游戏里的原始文本包为源；若本 mod 已装进游戏，先 `restore.ps1` 再生成，否则会把已经双语的内容再合并一次。

### 文件

```
msg\zhocn\menu.msgbnd.dcx     ← 生成物（内容同 menu_dlc2 累积版，游戏读本体文件名时用）
msg\zhocn\menu_dlc1.msgbnd.dcx
msg\zhocn\menu_dlc2.msgbnd.dcx
msg\zhocn\item*.msgbnd.dcx     同样生成，但默认配置不合并道具文本（内容同原版）
msg\engus\...                 同上，英文槽
source\msg\...                原版文本包副本，重新生成时作为源
tools\dualsub.py              生成器
tools\dualsub.config.json     类别开关 + Yabber 路径
build.ps1 / install.ps1 / restore.ps1
```

`item*.msgbnd.dcx` 也一并替换，但默认配置在道具文本上一个条目都没合并，内容与原版相同。

### 已知限制

- 道具说明面板高度固定，中文 + 英文塞不下；`Item Descriptions` / `Item Lore` 默认关闭，想看英文就设成 `"en_only"`。
- 游戏更新或 Steam「验证文件完整性」会覆盖这些文件，重跑 `install.ps1`。
- 只改文本。别的 mod 也换 `msg` 时，请以那个 mod 的文件为源重新生成。

---

## English

Adds the *other* language underneath the one you already display: with Simplified Chinese selected, English follows (on a new line, or `中文 / English` on one line); with English selected, Chinese follows. Only the text packs under `msg\` are replaced — exe, params and saves are untouched, and everything can be removed again.

### Install

1. Download or clone this repository — `msg\` already holds the generated text packs — and put the whole folder anywhere.
2. Close the game.
3. Run `install.ps1` (right-click → Run with PowerShell, or `powershell -ExecutionPolicy Bypass -File install.ps1`). It looks for `DARK SOULS III\Game` in your Steam libraries; otherwise pass it: `install.ps1 -GameDir "X:\...\DARK SOULS III\Game"`.
4. The game needs the loose-file setup (unpacked with UXM / Nuxe, i.e. `Game\msg\` exists as real files) — otherwise the replaced packs are never read.
5. Start the game offline. If another mod also replaces `msg` files, the two overwrite each other.

Uninstall: `restore.ps1` puts every file back to its exact pre-install bytes using the manifest the installer wrote. `restore.ps1 -DryRun` reports only. If a file cannot be restored, the manifest and the remaining backups are kept so you can retry.

### What is actually bilingual in the shipped build

The shipped `tools\dualsub.config.json` decides this — by default two categories are on:

| Category | Default | Notes |
|---|---|---|
| 会話 (NPC dialogue) | **on** | every entry |
| ムービー字幕 (cutscene subtitles) | **on** | every entry |
| イベントテキスト (event text) | **on** (partial) | ~335 entries merged; the rest keep their two languages in different places and are left alone |
| Menus, key prompts, item names/descriptions, help text, blood messages, system messages | off | single language, as in the base game |

Enable more in `tools\dualsub.config.json` and rebuild (below). Long description panels cannot fit both languages — prefer `"en_only"` for those.

### Rebuild

Requires **Python 3.9+** and **Yabber** (<https://github.com/JKAnderson/Yabber/releases>, just extract it).

```powershell
# point the script at Yabber (any one of these)
#   1) build.ps1 -YabberDir "D:\Tools\Yabber 1.3.1"
#   2) set "yabber_dir" in tools\dualsub.config.json
#   3) set the YABBER_DIR environment variable
powershell -ExecutionPolicy Bypass -File build.ps1 -YabberDir "D:\Tools\Yabber 1.3.1"
powershell -ExecutionPolicy Bypass -File install.ps1
```

Configuration keys:

| Key | Meaning |
|---|---|
| `yabber_dir` | folder holding `Yabber.exe` and `Yabber.DCX.exe` |
| `primary` / `secondary` | language folders, default `zhocn` / `engus` |
| `separator` | default join separator, a newline |
| `default_enabled` | merge categories that are not listed |
| `skip_merge_texts` | short strings never merged (是 / 否 / 确定 / 取消) |
| `categories` | per-category switch: `true` bilingual · `"off"`/`false` untouched · `"en_only"` English only · `"append"` force-append |

`build.ps1` reads the vanilla packs from the game folder. If this mod is already installed, run `restore.ps1` first, or the already-bilingual files get merged twice.

### Files

```
msg\zhocn\menu.msgbnd.dcx     generated (same content as the cumulative menu_dlc2, used for the base filename)
msg\zhocn\menu_dlc1.msgbnd.dcx
msg\zhocn\menu_dlc2.msgbnd.dcx
msg\zhocn\item*.msgbnd.dcx     generated too, but the default config merges no item text (matches vanilla)
msg\engus\...                 the same for the English slot
source\msg\...                pristine copies of the vanilla packs, used as the build source
tools\dualsub.py              generator
tools\dualsub.config.json     category switches + Yabber path
build.ps1 / install.ps1 / restore.ps1
```

`item*.msgbnd.dcx` are replaced too, but the default config merges nothing in the item text, so their content matches the base game.

### Known limitations

- The item description panel has a fixed height: Chinese + English never fits. `Item Descriptions` / `Item Lore` default to off; use `"en_only"` to read the English instead.
- Game updates and Steam "verify integrity" overwrite these files; rerun `install.ps1`.
- Text only. If another mod also replaces `msg` files, regenerate from that mod's files as the source.

### License

Scripts: MIT — see [LICENSE](LICENSE). The generated text is modified FromSoftware / Bandai Namco game text, included for offline single-player modding, not for commercial use. Not affiliated with FromSoftware or Bandai Namco.
