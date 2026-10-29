#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dark Souls III 双语字幕文本工具 (中文主语言 + 英文副语言，双向)。

工作方式（UXM 松散文件环境）:
  1. 从 <game>/msg/<lang>/*.msgbnd.dcx 取出文本包 (zhocn + engus)
  2. 用 Yabber 解 DCX -> BND4 -> FMG，得到 <lang>/msg/<LANG>/64bit/*.fmg
  3. 按条目 id 把两种语言的文本合并成「中文\\n英文」，并同时写回两个语言槽
     （游戏显示中文时下方出现英文；显示英文时下方出现中文）
  4. 按配置的开关决定哪些 FMG（地图大字/对话/物品/菜单/教程...）参与合并
  5. 重新打包回 .msgbnd.dcx，输出到 mod 目录，供 UXM 松散文件加载

用法:
  python dualsub.py --list                        # 列出文本包和 FMG，生成配置模板
  python dualsub.py                               # 按配置生成全部
  python dualsub.py --filter menu_dlc1            # 只处理某个文本包（调试）
  python dualsub.py --game "D:\\...\\Game" --out "D:\\game\\dark souls3\\mod\\DualSubtitle"
"""
from __future__ import annotations

import argparse
import fnmatch
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

YABBER_DIR = os.environ.get("YABBER_DIR", "")
DEFAULT_OUT = r"D:\game\dark souls3\mod\DualSubtitle"
DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dualsub.config.json")

YABBER_HELP = (
    "Yabber 未找到 / Yabber not found.\n"
    "  用 --yabber 参数、config 里的 \"yabber_dir\"、或 YABBER_DIR 环境变量指向\n"
    "  同时含 Yabber.exe 与 Yabber.DCX.exe 的文件夹。\n"
    "  Pass --yabber <dir>, set \"yabber_dir\" in the config, or set the YABBER_DIR\n"
    "  environment variable to the folder holding Yabber.exe and Yabber.DCX.exe.\n"
    "  Download: https://github.com/JKAnderson/Yabber/releases"
)


def find_yabber(hint: str = "") -> str:
    """定位 Yabber 目录（必须同时有 Yabber.exe 和 Yabber.DCX.exe）。"""
    cands = []
    if hint:
        cands.append(hint)
    if YABBER_DIR:
        cands.append(YABBER_DIR)
    exe = shutil.which("Yabber.exe") or shutil.which("Yabber")
    if exe:
        cands.append(os.path.dirname(os.path.abspath(exe)))
    roots = [
        r"D:\game\TOOL", r"D:\Tools", r"D:\tool", r"C:\Tools", r"C:\tool",
        os.environ.get("LOCALAPPDATA", ""), os.path.expanduser("~\\Downloads"),
        os.path.expanduser("~"),
    ]
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for pat in ("Yabber*", os.path.join("*", "Yabber*")):
            cands.extend(sorted(glob.glob(os.path.join(root, pat))))
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "Yabber.exe")) \
                and os.path.isfile(os.path.join(c, "Yabber.DCX.exe")):
            return os.path.abspath(c)
    raise SystemExit(YABBER_HELP)


def default_game() -> str:
    """自动定位 DS3 的 Game 目录（环境变量 -> Steam 库 -> 常见路径）。"""
    env = os.environ.get("DS3_GAME_DIR", "")
    if env and os.path.isfile(os.path.join(env, "DarkSoulsIII.exe")):
        return env
    roots = []
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as k:
            steam = winreg.QueryValueEx(k, "SteamPath")[0]
        roots.append(steam)
        vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
        if os.path.isfile(vdf):
            with open(vdf, encoding="utf-8", errors="replace") as fh:
                for m in re.finditer(r'"path"\s+"([^"]+)"', fh.read()):
                    roots.append(m.group(1).replace("\\\\", "\\"))
    except Exception:
        pass
    roots += [r"D:\steam\steamapps\common", r"E:\steam\steamapps\common",
              r"F:\steam\steamapps\common", r"C:\Program Files (x86)\Steam\steamapps\common"]
    for r in roots:
        cand = os.path.join(r, "DARK SOULS III", "Game")
        if os.path.isfile(os.path.join(cand, "DarkSoulsIII.exe")):
            return cand
    return r"D:\steam\steamapps\common\DARK SOULS III\Game"

NULL_MARKERS = {"%null%", "null", ""}

# 各类文本的中文说明（用于配置文件和 --list 输出）
CATEGORY_HINT = {
    "ダイアログ": "对话（通用对话框）",
    "会話": "NPC 对话字幕",
    "ムービー字幕": "过场动画字幕",
    "イベントテキスト": "事件/剧情文本",
    "インゲームメニュー": "游戏内菜单",
    "キーガイド": "按键提示",
    "FDP_キーガイド": "按键提示(FDP)",
    "FDP_ダイアログ": "对话框(FDP)",
    "FDP_メニューテキスト": "菜单文本(FDP)",
    "FDP_一行ヘルプ": "一行帮助(FDP)",
    "FDP_システムメッセージ_win64": "系统消息(PC)",
    "FDP_システムメッセージ_ps4": "系统消息(PS4)",
    "FDP_システムメッセージ_xboxone": "系统消息(Xbox)",
    "マップ": "地图/区域大字",
    "地名": "地名",
    "アイテム": "物品名/说明",
    "武器": "武器",
    "防具": "防具",
    "指輪": "戒指",
    "魔術": "法术",
    "奇跡": "奇迹",
    "呪術": "咒术",
    "スキル": "技能",
}


def norm(t: str) -> str:
    return re.sub(r"\s+", "", t or "").lower()


def is_null(t) -> bool:
    return t is None or t.strip().lower() in NULL_MARKERS


class Yabber:
    def __init__(self, directory: str):
        self.exe = os.path.join(directory, "Yabber.exe")
        self.dcx = os.path.join(directory, "Yabber.DCX.exe")
        for p in (self.exe, self.dcx):
            if not os.path.exists(p):
                raise SystemExit(f"Yabber not found in: {directory}\n{YABBER_HELP}")

    def run(self, tool: str, path: str) -> None:
        proc = subprocess.run([tool, path], capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            raise RuntimeError(f"Yabber failed: {path}\n{proc.stdout}\n{proc.stderr}")


class FmgXml:
    """FMG 的 Yabber XML: <fmg><entries><text id="...">��文</text>..."""

    def __init__(self, path: str):
        self.path = path
        self.tree = ET.parse(path)
        self.root = self.tree.getroot()
        self.entries = {}
        parent = self.root.find("entries")
        if parent is None:
            raise RuntimeError(f"Not a valid FMG XML: {path}")
        for el in parent:
            self.entries[el.attrib.get("id")] = el

    def write(self) -> None:
        self.tree.write(self.path, xml_declaration=True, encoding="utf-8")

    def merge(self, other: "FmgXml", sep, log, skip_texts=None) -> int:
        """把 other 的文本追加到 self 的每条后面，并把 self 的文本追加到 other。
        sep 为 None 时按条目自动选择：原文含换行用换行，否则用 ' / '（单行控件）。
        skip_texts 中的原文（精确匹配）不合并，避免窄按钮/标签被截断。
        返回修改条数。"""
        changed = 0
        skip_texts = skip_texts or ()
        for key, el in self.entries.items():
            other_el = other.entries.get(key)
            if other_el is None:
                continue
            t1, t2 = el.text, other_el.text
            if is_null(t1) or is_null(t2):
                continue
            if norm(t1) == norm(t2):
                continue
            if t1.strip() in skip_texts:
                continue
            # 幂等：已经合并过的（含两种语言）跳过
            if (t1.endswith(t2) and t1 != t2) or (t2.endswith(t1) and t2 != t1):
                continue
            use_sep = sep
            if use_sep is None:
                use_sep = "\n" if ("\n" in t1 or "\n" in t2) else " / "
            new1, new2 = t1 + use_sep + t2, t2 + use_sep + t1
            el.text, other_el.text = new1, new2
            changed += 1
            if len(new1) > 400:
                log(f"  ! entry {key} is long after merge ({len(new1)} chars)")
        return changed

    def replace_texts_from(self, other: "FmgXml") -> int:
        """en_only 模式：用另一种语言的文本替换本文件中的文本。"""
        changed = 0
        for key, el in self.entries.items():
            other_el = other.entries.get(key)
            if other_el is None:
                continue
            if is_null(el.text) or is_null(other_el.text):
                continue
            if norm(el.text) == norm(other_el.text):
                continue
            el.text = other_el.text
            changed += 1
        return changed


def find_fmg_dir(unpacked: str) -> str:
    for root, _dirs, files in os.walk(unpacked):
        if any(f.lower().endswith(".fmg") for f in files):
            return root
    raise RuntimeError(f"No FMG found in unpacked dir: {unpacked}")


def stem_of(path: str) -> str:
    name = os.path.basename(path)
    for suffix in (".msgbnd.dcx", ".msgbnd"):
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return os.path.splitext(name)[0]


def load_config(path: str) -> dict:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    return {"primary": "zhocn", "secondary": "engus", "separator": "\n",
            "default_enabled": True, "categories": dict(DEFAULT_CATEGORIES)}


# English category names -> internal FMG filename patterns (first match wins)
CATEGORY_RULES = [
    ("Dialogue", ["会話*"]),
    ("Cutscene Subtitles", ["ムービー字幕*"]),
    ("Dialogue Boxes", ["ダイアログ*", "FDP_ダイアログ*"]),
    ("Event Text", ["イベントテキスト*"]),
    ("Menu Text", ["*メニューテキスト*", "メニューその他*", "メニュー共通テキスト*", "インゲームメニュー*"]),
    ("Key Prompts", ["キーガイド*", "FDP_キーガイド*"]),
    ("Help Text", ["*一行ヘルプ*", "項目ヘルプ*"]),
    ("System Messages", ["FDP_システムメッセージ*"]),
    ("Place Names", ["地名*"]),
    ("Item Lore", ["*うんちく*"]),
    ("Item Descriptions", ["*説明*"]),
    ("Item Names", ["*名.fmg", "*名_dlc*.fmg", "NPC名*"]),
    ("Blood Messages", ["血文字*"]),
]

DEFAULT_CATEGORIES = {
    "Dialogue": True,
    "Cutscene Subtitles": True,
    "Dialogue Boxes": True,
    "Event Text": True,
    "Menu Text": True,
    "Key Prompts": True,
    "Help Text": True,
    "System Messages": True,
    "Place Names": True,
    "Item Names": True,
    "Item Descriptions": "off",
    "Item Lore": "off",
    "Blood Messages": True,
    "Other": True,
}

# Old Chinese category names are still accepted in config files
CATEGORY_ALIASES = {
    "对话字幕": "Dialogue",
    "过场字幕": "Cutscene Subtitles",
    "对话框": "Dialogue Boxes",
    "事件/剧情文本": "Event Text",
    "菜单文字": "Menu Text",
    "按键提示": "Key Prompts",
    "帮助提示": "Help Text",
    "系统消息": "System Messages",
    "地名/区域大字": "Place Names",
    "物品名称": "Item Names",
    "物品说明": "Item Descriptions",
    "物品背景故事": "Item Lore",
    "血字留言": "Blood Messages",
    "其他文本": "Other",
}


def category_of(fmg: str) -> str:
    base = os.path.basename(fmg)
    for name, pats in CATEGORY_RULES:
        if any(fnmatch.fnmatchcase(base, p) for p in pats):
            return name
    return "Other"


def _cat_value(cfg: dict, fmg: str):
    cats = cfg.get("categories")
    if not cats:
        return None
    name = category_of(fmg)
    if name in cats:
        return cats[name]
    # accept legacy Chinese names too
    for alias, canon in CATEGORY_ALIASES.items():
        if canon == name and alias in cats:
            return cats[alias]
    return None


def _value_mode(v) -> str:
    """把分类的值统一成模式: append / off / en_only"""
    if isinstance(v, dict):
        if v.get("mode"):
            return str(v["mode"])
        return "append" if v.get("enabled", True) else "off"
    if isinstance(v, str):
        return v
    return "append" if v else "off"


def enabled_for(cfg: dict, msgbnd: str, fmg: str) -> bool:
    v = _cat_value(cfg, fmg)
    if v is not None:
        return _value_mode(v) != "off"
    node = cfg.get("files", {})
    for key in (msgbnd, stem_of(msgbnd)):
        if key in node:
            entry = node[key]
            if not entry.get("enabled", cfg.get("default_enabled", True)):
                return False
            rules = entry.get("fmg", {})
            for pat, val in rules.items():
                if fnmatch.fnmatchcase(fmg, pat):
                    if isinstance(val, dict):
                        return bool(val.get("enabled", True))
                    return bool(val)
    # 未配置的文件走默认；FMG 级规则全局生效
    rules = cfg.get("fmg", {})
    for pat, val in rules.items():
        if fnmatch.fnmatchcase(fmg, pat):
            if isinstance(val, dict):
                return bool(val.get("enabled", True))
            return bool(val)
    return cfg.get("default_enabled", True)


def mode_for(cfg: dict, pack: str, fmg: str) -> str:
    """合并模式:
      append  - 追加另一种语言（默认）
      off     - 不合并（长说明默认，避免框内显示不全）
      en_only - 用英文替换当前语言的文本（适合想读英文原文的说明）
    """
    v = _cat_value(cfg, fmg)
    if v is not None:
        return _value_mode(v)
    entry = cfg.get("files", {}).get(stem_of(pack), {}).get("fmg", {})
    v = entry.get(fmg)
    if isinstance(v, dict) and v.get("mode"):
        return v["mode"]
    base = os.path.splitext(fmg)[0]
    if any(m in base for m in ("説明", "うんちく")):
        return "off"
    return "append"


def discover(game: str, primary: str, secondary: str) -> list[str]:
    """两种语言都有、且能配对处理的文本包。"""
    a = os.path.join(game, "msg", primary)
    b = os.path.join(game, "msg", secondary)
    if not os.path.isdir(a) or not os.path.isdir(b):
        raise SystemExit(f"msg language dirs not found: {a} / {b}")
    names = {f.lower(): f for f in os.listdir(a) if f.lower().endswith(".msgbnd.dcx")}
    have = {f.lower() for f in os.listdir(b)}
    return sorted(names[k] for k in names if k in have)


def separator_for(cfg: dict, pack: str, fmg: str) -> str:
    """决定两种语言之间的分隔符。单行控件（名称/地名/提示）用 ' / '，
    多行控件（对话字幕/说明）用换行。配置文件可对单个 FMG 覆盖。"""
    stem = stem_of(pack)
    entry = cfg.get("files", {}).get(stem, {}).get("fmg", {})
    v = entry.get(fmg)
    if isinstance(v, dict) and v.get("separator") is not None:
        return v["separator"]
    base = os.path.splitext(fmg)[0]
    # 多行控件：对话/字幕/长说明 -> 换行
    multiline_marks = ("会話", "ムービー字幕", "説明", "うんちく", "ダイアログ")
    if any(m in base for m in multiline_marks):
        return "\n"
    # 单行控件：名称/地名/菜单/提示 -> 同一行
    one_line_marks = (
        "名.fmg", "地名", "一行ヘルプ", "キーガイド", "システムメッセージ",
        "メニューテキスト", "インゲームメニュー", "項目ヘルプ",
    )
    if any(m in base for m in one_line_marks) or base.endswith("名"):
        return " / "
    # 其余按条目自动判断（短标签单行，长文本换行）
    return None


def build_one(game: str, out: str, cfg: dict, name: str, log, keep_work: bool,
              yabber_dir: str = "") -> dict:
    primary, secondary = cfg["primary"], cfg["secondary"]
    sep = cfg.get("separator", "\n")
    if sep == "\\n":
        sep = "\n"
    skip_texts = set(cfg.get("skip_merge_texts", []))
    stem = stem_of(name)
    work = os.path.join(out, "_work", stem)
    if os.path.isdir(work):
        shutil.rmtree(work)
    os.makedirs(work, exist_ok=True)

    y = Yabber(yabber_dir or cfg.get("yabber_dir") or find_yabber())
    stats = {"file": name, "fmg_total": 0, "fmg_merged": 0, "entries": 0, "skipped_fmg": 0}

    results = {}  # lang -> final dcx path
    for lang in (primary, secondary):
        src = os.path.join(game, "msg", lang, name)
        wdir = os.path.join(work, lang)
        os.makedirs(wdir, exist_ok=True)
        dcx = os.path.join(wdir, name)
        shutil.copy2(src, dcx)
        y.run(y.dcx, dcx)                      # DCX -> msgbnd
        msgbnd = dcx[:-4]
        y.run(y.exe, msgbnd)                   # BND4 -> folder
        unpacked = os.path.join(wdir, f"{stem}-msgbnd")
        fmg_dir = find_fmg_dir(unpacked)
        results[lang] = {"dcx": dcx, "msgbnd": msgbnd, "unpacked": unpacked, "fmg_dir": fmg_dir}

    fmg_dirs = {lang: results[lang]["fmg_dir"] for lang in results}
    all_fmg = sorted({f for d in fmg_dirs.values() for f in os.listdir(d) if f.lower().endswith(".fmg")})
    stats["fmg_total"] = len(all_fmg)

    primary_fmgs = set(os.listdir(fmg_dirs[primary]))
    secondary_fmgs = set(os.listdir(fmg_dirs[secondary]))

    for fmg in all_fmg:
        if fmg not in primary_fmgs or fmg not in secondary_fmgs:
            log(f"  - skip {fmg} (missing on one side)")
            stats["skipped_fmg"] += 1
            continue
        if not enabled_for(cfg, name, fmg):
            log(f"  - off {fmg}")
            stats["skipped_fmg"] += 1
            continue
        fmg_mode = mode_for(cfg, name, fmg)
        if fmg_mode == "off":
            log(f"  - skip {fmg} (long text, keep original)")
            stats["skipped_fmg"] += 1
            continue
        p1 = os.path.join(fmg_dirs[primary], fmg)
        p2 = os.path.join(fmg_dirs[secondary], fmg)
        y.run(y.exe, p1)                       # fmg -> xml
        y.run(y.exe, p2)
        x1, x2 = FmgXml(p1 + ".xml"), FmgXml(p2 + ".xml")
        if fmg_mode == "en_only":
            n = x1.replace_texts_from(x2)
        else:
            fmg_sep = separator_for(cfg, name, fmg)
            n = x1.merge(x2, fmg_sep, log, skip_texts)
        if n:
            x1.write(); x2.write()
            y.run(y.exe, p1 + ".xml")          # xml -> fmg
            y.run(y.exe, p2 + ".xml")
            stats["fmg_merged"] += 1
            stats["entries"] += n
            log(f"  + {fmg}: {n} entries")
        else:
            log(f"  = {fmg}: nothing to merge")

    for lang in (primary, secondary):
        r = results[lang]
        y.run(y.exe, r["unpacked"])            # folder -> msgbnd
        y.run(y.dcx, r["msgbnd"])              # msgbnd -> dcx
        dst = os.path.join(out, "msg", lang, name)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(r["msgbnd"] + ".dcx", dst)
        log(f"  -> {dst}")

    if not keep_work:
        shutil.rmtree(work, ignore_errors=True)
    return stats


def do_list(game: str, cfg_path: str, primary: str, secondary: str) -> None:
    """生成中文分类配置（不需要日文文件名）。"""
    template = {
        "primary": primary,
        "secondary": secondary,
        "separator": "\n",
        "default_enabled": True,
        "categories": dict(DEFAULT_CATEGORIES),
    }
    with open(cfg_path, "w", encoding="utf-8") as fh:
        json.dump(template, fh, ensure_ascii=False, indent=2)
    print(f"Wrote category config: {cfg_path}")
    print("Available categories:")
    for name in list(DEFAULT_CATEGORIES):
        print(f"  - {name}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="DS3 双语字幕文本工具")
    ap.add_argument("--game", default=None, help="游戏 Game 目录 (默认自动定位)")
    ap.add_argument("--out", default=DEFAULT_OUT, help="输出 mod 目录")
    ap.add_argument("--config", default=DEFAULT_CONFIG, help="配置文件")
    ap.add_argument("--yabber", default="", help="Yabber 所在文件夹（含 Yabber.exe / Yabber.DCX.exe）")
    ap.add_argument("--primary", default=None, help="主语言目录 (默认 zhocn)")
    ap.add_argument("--secondary", default=None, help="副语言目录 (默认 engus)")
    ap.add_argument("--filter", default=None, help="只处理名称匹配的文本包 (通配符)")
    ap.add_argument("--source", default=None, help="原始 msg 来源目录（默认与 --game 相同）")
    ap.add_argument("--list", action="store_true", help="列出文本包并生成配置模板")
    ap.add_argument("--keep-work", action="store_true", help="保留中间文件")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)
    if args.primary:
        cfg["primary"] = args.primary
    if args.secondary:
        cfg["secondary"] = args.secondary
    primary, secondary = cfg.get("primary", "zhocn"), cfg.get("secondary", "engus")

    game = args.game or default_game()
    if not os.path.isdir(game):
        raise SystemExit(f"Game directory not found: {game}\n"
                         "用 --game 指定 {游戏}\\Game 目录。")

    if args.list:
        do_list(game, args.config, primary, secondary)
        return 0

    src_game = args.source or game
    names = discover(src_game, primary, secondary)
    # ngword 是屏蔽词表，不参与双语显示
    names = [n for n in names if not stem_of(n).lower().startswith("ngword")]
    if args.filter:
        names = [n for n in names if fnmatch.fnmatchcase(stem_of(n), args.filter)]
    if not names:
        raise SystemExit("No text packs to process (base text may not be unpacked)")

    t0 = time.time()
    print(f"Game: {game}")
    print(f"Output: {args.out}")
    print(f"Languages: {primary} + {secondary}, {len(names)} packs\n")
    all_stats = []
    for name in names:
        print(f"[{name}]")
        all_stats.append(build_one(src_game, args.out, cfg, name, print, args.keep_work, args.yabber))
        print()

    # 本体文本文件: 游戏读 menu.msgbnd / item.msgbnd 时若没有松散副本会回退到归档原版，
    # 导致本体文本不生效。用累积版 DLC2（没有则 DLC1）的生成结果补一份本体文件名。
    for base in ("menu", "item"):
        for lang in (primary, secondary):
            for cand in (f"{base}_dlc2.msgbnd.dcx", f"{base}_dlc1.msgbnd.dcx"):
                src = os.path.join(args.out, "msg", lang, cand)
                if os.path.exists(src):
                    dst = os.path.join(args.out, "msg", lang, f"{base}.msgbnd.dcx")
                    shutil.copy2(src, dst)
                    print(f"[base] {lang}\\{base}.msgbnd.dcx <- {cand}")
                    break

    total_fmg = sum(s["fmg_merged"] for s in all_stats)
    total_entries = sum(s["entries"] for s in all_stats)
    print(f"Done: {len(all_stats)} packs, {total_fmg} FMGs, {total_entries} entries, "
          f"in {time.time() - t0:.1f}s")
    print(f"Mod files in: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
