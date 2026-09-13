#!/usr/bin/env python3
"""Build the plain-text NAI artist preset library from the authoritative Markdown files.

The source document is intentionally kept as Markdown.  This script is the single
repeatable conversion step used to create ``public/artist-library.json``; it does
not read or process preview images.

``artist_pool`` extracts per-preset artist names with a real tokenizer (weight
groups ``N::…::``, bracket groups ``{…}/[…]/(…)``, ``artist:`` labels, ``#``
comments, Chinese/ASCII separators, trailing weights, unbalanced parentheses)
instead of a single regex.  Candidates are validated against a quality-tag
stoplist plus a corpus-bootstrapped known-artist set, and spelling variants of
the same artist (``ask (askzy)`` / ``ask(askzy)`` / ``ask_(askzy)``) are merged
into one canonical entry.  ``--report`` prints per-candidate decisions for
tuning; fixtures run on every build and abort on regressions.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from tempfile import NamedTemporaryFile

HEADING_RE = re.compile(r"^###\s+(\d+)\.\s+(.+?)\s*$")

# Characters that must never survive inside a pool entry.
_FORBIDDEN = ":：#|/@<>\""

# Quality / style / meta vocabulary that must never be mistaken for an artist.
# Keys are canonicalised (casefolded, spaces/underscores/backslashes removed).
_STOP_RAW = [
    "best quality", "amazing quality", "worst quality", "low quality",
    "normal quality", "good quality", "high quality", "quality", "very aesthetic",
    "aesthetic", "absurdres", "highres", "lowres", "masterpiece", "detailed",
    "ultra-detailed", "extremely detailed", "delicate details", "highly detailed skin",
    "hyperdetailed skin", "detailed skin", "oily shiny skin", "real skin radiance",
    "realistic", "photorealistic", "semi-realistic", "4k", "8k", "monochrome",
    "greyscale", "grayscale", "black and white", "white background",
    "simple background", "screentones", "halftone", "photo", "photo (medium)",
    "photo(medium)", "photo_(medium)", "image", "3d", "2d", "medium", "newest",
    "oldest", "early", "mid", "late", "very early", "very late", "year", "text",
    "english text", "textless", "textless version", "text focus", "translation",
    "watermark", "signature", "username", "logo", "jpeg artifacts", "blurry",
    "sketch", "lineart", "no lineart", "flat color", "limited palette",
    "artist collaboration", "artist collabo", "collaboration", "collab",
    "comedic", "hetero", "vulgar", "long description", "illustration",
    "romantic style", "dark theme", "like a photo", "anime style", "cartoon",
    "year 2023", "year 2024", "year 2025", "year_2023", "year_2024", "year_2025",
    "data in year 2025", "chinese clothes", "chinese updo",
    "chinese fairy sophisticated charm", "no modern elements",
    "realistic skin texture", "soft lighting", "cinematic lighting",
    "soulful portrait", "front view", "dynamic pose", "standing", "sitting",
    "1girl", "1boy", "solo", "portrait", "upper body", "full body",
    "cowboy shot", "close-up", "from above", "from below", "from side",
    "looking at viewer", "smile", "open mouth", "blush", "long hair",
    "short hair", "twintails", "ponytail", "bangs", "brown hair", "black hair",
    "blue eyes", "brown eyes", "large breasts", "huge breasts", "nsfw", "sfw",
    "nude", "topless", "panties", "pussy", "sex", "cum", "nipples", "ass",
    "explicit", "risqué", "sensitive", "general", "verbose", "prompt",
    "weight", "negative", "positive", "resolution", "aspect ratio", "ratio",
    "steps", "sampler", "scale", "guidance", "seed", "variation", "strength",
    # --- 第二轮人工审查补充（2026-08）---
    # 构图/镜头/氛围
    "pov", "perspective", "scenic", "atmospheric", "cinematic", "bustling",
    "bloom", "bokeh", "backlighting", "caustics", "shadow", "lighting",
    "soft shadow", "colored shadow", "colored_shadow", "gradient", "particles",
    "sparkle", "glow", "glowing", "glistening", "shiny", "shiny_skin",
    "smooth", "smoothshading", "impasto", "dithering", "hatching",
    "chiaroscuro", "chiaroscuromasterpiece", "hdr", "c4d", "cg", "render",
    "noise", "overexposure", "upscaled", "downscaled", "draft", "unfinished",
    "frame", "border", "borderless", "blank_page", "blank page", "collage",
    "split_screen", "split screen", "cross-section", "cross-section view",
    "drive shot", "wide_anglelow_angle", "iconic", "microdisplacement",
    "photogrammetry", "photo-referenced", "photorealisti", "hyper-realistic",
    "hyperrealistic", "hyperdetailed", "cel-shading", "hard-edge", "gestural",
    "painterly", "texture", "ink", "inkblot", "ink_wash_painting",
    "ink wash painting", "pixel", "pixel_art", "pixel art", "ukiyo-e",
    "nihonga", "bijin-ga", "webtoon", "manga", "comic", "comics", "artbook",
    "2koma", "3koma", "4koma", "anime", "animated", "animation", "cartoonish",
    "anime_coloring", "anime colors", "anime_face", "anime_syle",
    # 通用形容词
    "adorable", "alluring", "amazing", "appealing", "artistic", "attractive",
    "authoritative", "beautiful", "charming", "creative", "crisp", "cute",
    "dark", "delicate", "delightful", "dreamy", "elegant", "enchanting",
    "endearing", "energetic", "engaging", "expressive", "eye-catching",
    "fantasy", "fascinating", "fashion", "feminine", "fresh", "graceful",
    "heartwarming", "impressive", "lovely", "low", "memorable", "modern",
    "medieval", "whimsical", "stylish", "trendy", "vibrant", "vivid",
    "voluptuous", "warm", "sweet", "sexy", "seductive", "youthful", "quiet",
    "questionable", "popular", "pleasant", "pretty", "normal", "real",
    "red", "green", "bright", "clean", "clear", "lack", "moss", "ferns",
    "wind", "heart", "sweat", "feet", "eyelash", "hair", "location", "people",
    "crowd", "indoor", "outdoors", "multiple", "multiple_boys", "multiple views",
    "multiple_views", "dual_persona", "dual persona", "official_art",
    "official art", "commentary_request", "chinese_commentary", "constraint",
    "source_anime", "novelance", "daylightallure", "solipsist", "tally",
    "besmiled", "aestivation", "afternoon", "halloween", "hatching",
    "displeasing", "deformed", "trembling", "jitome", "heavy_breathing",
    # 解剖/NSFW
    "breasts", "large_breasts", "medium_breasts", "large_areolae", "puffy",
    "huge_nipples", "gigantic_ass", "gigantic_breasts", "gigantic breasts",
    "gigantic ass", "cameltoe", "cleavage", "navel", "groin", "loli", "milf",
    "cum_string", "crotch_cutout", "pussy_exposure", "pussy_juice_puddle",
    "love_handles", "plump", "curvy", "petite", "pale_skin", "white_skin",
    "white skin", "oil_skin", "oiled", "saliva_trail", "skindentation",
    "see-through", "x-ray", "censored", "uncensored", "mature_eyes",
    "mature_female", "healthyman", "glabrous", "facepaint",
    # 企划/作品/媒介名（非画师）
    "granblue_fantasy", "granblue fantasy", "majo_no_tabitabi",
    "majo no tabitabi", "douluo_dalu", "gachiakuta", "brown_dust_2",
    "brown dust 2", "toaru_kagaku_no_railgun_official_art", "sos adult",
    "sos_adult", "pen (medium)", "watercolor_(medium)", "blender_(medium)",
    "koikatsu_(medium)", "fumo (doll)", "raiden mei(apho)",
    # 疑似错拼/拼接垃圾
    "name", "mm", "ui", "no", "what", "break", "lora模型", "artist_name",
    "zer0zer0", "wlopc", "wolp",
    "monocrome", "undefinedundefined", "amazing.high_detail",
    "best_illustration", "best_proportions", "extremely_detailed_eyes_and_face",
    "realistic_skin_surface", "shexyolocation", "ai-assisted", "ai-generated",
    # --- 第三轮人工审查补充 ---
    "2.5d", "abs", "ic", "celebrity", "chibi", "color", "colorful",
    "minimalism", "negative_space", "pants", "speech_bubble", "toned",
    "handwritten", "incredibly_absurdres", "hanfu", "filigree", "lamp",
    "banishment", "by", "collaborations", "artist collaborations",
    "画师串名",
]

# 括号内是这些词时不是画师 handle（风格/媒介/版权标注）
HANDLE_STOP = {"medium", "style", "copyright", "doll", "comic", "puffy", "apho"}
# 这些 handle 需要剥掉保留主体（主体本身是画师）
HANDLE_STRIP = {"inkwashpainting", "persona5"}


def _key(name: str) -> str:
    """Canonical comparison key: casefold, drop separators/escapes entirely."""
    k = name.casefold().replace("\\", "")
    k = re.sub(r"[\s_]+", "", k)
    return k


def _base_key(name: str) -> str | None:
    """Key of ``name(handle)`` without the handle suffix; None if not handle-form."""
    m = re.fullmatch(r"(.*?)\s*\([\w\-\u4e00-\u9fff]+\)", name.strip())
    return _key(m.group(1)) if m else None


STOP_KEYS = {_key(s) for s in _STOP_RAW if s}

# Multi-word plain names verified by hand against the corpus (used only when the
# candidate carries neither an ``artist:`` label nor a ``(handle)`` suffix).
ALLOW_MULTIWORD_RAW: list[str] = []
ALLOW_MULTIWORD = {_key(s) for s in ALLOW_MULTIWORD_RAW}

_HANDLE = "\x01"  # sentinel replacing parens of ``name(handle)`` so the scanner keeps them atomic
_HANDLE_CLOSE = "\x02"


def _protect_handles(text: str) -> str:
    # 保留 name 与 (handle) 之间的分隔符（_ 或空格），变体归并时才能选出规范形
    pattern = re.compile(r"([\w\\'\-])([\s_]*)\(([\w\-\u4e00-\u9fff]{1,40})\)")
    return pattern.sub(lambda m: f"{m.group(1)}{m.group(2)}{_HANDLE}{m.group(3)}{_HANDLE_CLOSE}", text)


_WEIGHT_GROUP = re.compile(r"[-+]?\d+(?:\.\d+)?\s*::")


def _iter_candidates(body: str) -> list[str]:
    """Split a prompt into raw candidate strings (weights/brackets/comments removed)."""
    text = re.sub(r"\\+\(", "(", str(body))  # 源文件存在 \( 与 \\( 两种转义写法
    text = re.sub(r"\\+\)", ")", text)
    text = _protect_handles(text)
    out: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        if buf:
            out.append("".join(buf).strip())
            buf.clear()

    def scan(seg: str) -> None:
        i = 0
        while i < len(seg):
            m = _WEIGHT_GROUP.match(seg, i)
            if m:
                flush()
                close = seg.find("::", m.end())
                end = len(seg) if close == -1 else close + 2
                scan(seg[m.end():close if close != -1 else len(seg)])
                i = end
                continue
            ch = seg[i]
            if ch in "{[(":
                close_ch = {"{": "}", "[": "]", "(": ")"}[ch]
                depth, j = 0, i
                while j < len(seg):
                    if seg[j] == ch:
                        depth += 1
                    elif seg[j] == close_ch:
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                flush()
                scan(seg[i + 1:j])
                i = j + 1 if j < len(seg) else len(seg)
                continue
            if ch in ",，、：\n;":
                flush()
                i += 1
                continue
            if ch == "#":
                flush()
                return  # comment: remainder of this segment is annotation
            buf.append(ch)
            i += 1
        flush()

    scan(text)
    return out


def _balance(candidate: str) -> str:
    """Strip stray unmatched parentheses left over from polluted source text."""
    c = candidate
    while c.endswith("("):
        c = c[:-1]
    while c.startswith(")"):
        c = c[1:]
    while c.count("(") < c.count(")") and c.endswith(")"):
        c = c[:-1]
    while c.count(")") < c.count("(") and c.startswith("("):
        c = c[1:]
    return c.strip()


def _clean(raw: str) -> str:
    c = raw.replace(_HANDLE, "(").replace(_HANDLE_CLOSE, ")")
    c = re.sub(r"#.*$", "", c).strip()
    # artist: / artist : / artist_ 前缀（源文件存在多种手写变体）
    c = re.sub(r"^artists?[\s_:+]*", "", c, flags=re.I).strip()
    c = re.sub(r"^(?:art\s+)?by\s+", "", c, flags=re.I).strip()
    c = _balance(c)
    # trailing weights, possibly chained: name:1.2, name::0.8, (name:1.2)
    c = re.sub(r"(?:\s*:+\s*[-+]?\d+(?:\.\d+)?)+\s*$", "", c).strip()
    c = _balance(c)
    while len(c) >= 2 and c[0] in "{[(" and c[-1] in "}])" and c.count(c[0]) == c.count(c[-1]):
        c = c[1:-1].strip()
        c = re.sub(r"^artists?[\s_:+]*", "", c, flags=re.I).strip()
        c = re.sub(r"(?:\s*:+\s*[-+]?\d+(?:\.\d+)?)+\s*$", "", c).strip()
        c = _balance(c)
    # 风格括号尾缀剥壳保留主体: xuedaixun(ink_wash_painting) -> xuedaixun
    m = re.fullmatch(r"(.*?)\s*\(([\w\-\u4e00-\u9fff]{1,40})\)", c)
    if m and _key(m.group(2)) in HANDLE_STRIP:
        c = m.group(1).strip()
    # 拼接的年份标签: meion_year2025 -> meion
    c = re.sub(r"[\s_]*years?20\d\d$", "", c, flags=re.I).strip()
    # 括号后拼接的数字: konomi_(konomi_takeshi) 25 -> konomi_(konomi_takeshi)
    c = re.sub(r"(\))[\s_]+\d{1,4}$", r"\1", c).strip()
    # 尾部多余句点: alchemaniac. -> alchemaniac
    c = re.sub(r"\.+$", "", c).strip()
    # 尾部悬挂下划线: channel_ -> channel
    c = c.rstrip("_").strip()
    return re.sub(r"\s+", " ", c).strip()


_LABELLED = re.compile(r"artists?\s*:", re.I)


def _shape_ok(c: str) -> bool:
    """结构合法性（不依赖已知集）：无非法字符、括号配对、非停用词（含剥 handle 后）。"""
    if not c or len(c) > 60:
        return False
    if any(ch in _FORBIDDEN for ch in c):
        return False
    if c.count("(") != c.count(")"):
        return False
    k = _key(c)
    if not k or k in STOP_KEYS:
        return False
    base = _base_key(c)
    return base is None or base not in STOP_KEYS


def _validate(c: str, known_multiword: set[str], known_base: set[str]) -> bool:
    if not _shape_ok(c):
        return False
    if len(c) < 2 or re.fullmatch(r"[-+.\d\s]+", c):
        return False  # 单字符与纯数字/权重残渣
    k = _key(c)
    base = _base_key(c)
    if base is not None:  # handle-form: name(handle)
        if not re.fullmatch(r"[\w'\s\-]+?\(([\w\-\u4e00-\u9fff]{1,40})\)", c):
            return False
        return _key(re.search(r"\(([\w\-\u4e00-\u9fff]{1,40})\)", c).group(1)) not in HANDLE_STOP
    if len(c.split(" ")) == 1:
        return bool(re.fullmatch(r"[\w\-'.]+", c, re.UNICODE))
    # plain multi-word: only allow-list or corpus-known multi-word artists
    return k in ALLOW_MULTIWORD or k in known_multiword or base in known_base


def _bootstrapped_knowns(bodies: list[str]) -> tuple[set[str], set[str]]:
    """High-confidence artists: explicit ``artist:`` labels + ``name(handle)`` tags."""
    multiword: set[str] = set()
    base_keys: set[str] = set()

    def add(c: str) -> None:
        if len(c.split(" ")) > 1:
            multiword.add(_key(c))
            bk = _base_key(c)
            if bk:
                base_keys.add(bk)

    handle_re = re.compile(r"([\w\\'\-]+(?:\s[\w\\'\-]+)?)\s*\(([\w\-\u4e00-\u9fff]{1,40})\)")
    for body in bodies:
        text = re.sub(r"\\+\(", "(", str(body))
        text = re.sub(r"\\+\)", ")", text)
        for whole, _handle in handle_re.findall(text):
            cand = _clean(whole)
            if _shape_ok(cand) and re.fullmatch(r"[\w'\s\-]+?\([\w\-\u4e00-\u9fff]{1,40}\)", cand):
                add(cand)
        for raw in _iter_candidates(body):
            if not _LABELLED.search(raw):
                continue
            cand = _clean(raw)
            # 带 artist: 标签即高置信，只需结构合法即可进入已知集
            if _shape_ok(cand):
                add(cand)
    return multiword, base_keys


def _variant_key(name: str) -> str:
    """Key that unifies spelling variants of one artist: ask (askzy) ≡ ask_(askzy)."""
    return _key(name)


def _variant_rank(name: str) -> int:
    """body 内多拼写变体去重时的优先级：name_(handle) > 含下划线 > 括号形 > 裸名。"""
    return 0 if "_(" in name else (1 if "_" in name else (2 if "(" in name else 3))


def artist_pool(body: str, known_multiword: set[str] | None = None,
                known_base: set[str] | None = None) -> list[str]:
    known_multiword = known_multiword if known_multiword is not None else set()
    known_base = known_base if known_base is not None else set()
    best: dict[str, str] = {}  # variant key -> 目前最优规范形
    order: list[str] = []
    for raw in _iter_candidates(body):
        cand = _clean(raw)
        if not _validate(cand, known_multiword, known_base):
            continue
        vk = _variant_key(cand)
        if vk not in best:
            best[vk] = cand
            order.append(vk)
        elif _variant_rank(cand) < _variant_rank(best[vk]):
            best[vk] = cand
    return [best[vk] for vk in order]


def _merge_variants(all_names: list[str]) -> tuple[dict[str, str], dict[str, int]]:
    """Map every spelling variant to one canonical representative.

    规范形优先于词频：name_(handle) > 含下划线 > 空格括号形 > 裸名。
    裸名（ask_askzy）通过"去括号键"并入唯一对应的括号组（ask_(askzy)）。
    """
    freq: Counter[str] = Counter(all_names)
    groups: dict[str, dict[str, int]] = {}  # full key -> {raw: freq}
    for name, n in freq.items():
        groups.setdefault(_variant_key(name), {})[name] = n
    # 括号组暴露三个匹配键：完整键 ask(askzy)、去括号键 askaskzy、基名键 ask
    paren_keys = {k for k, m in groups.items() if any("(" in n for n in m)}
    owner_index: dict[str, list[str]] = {}
    for key in paren_keys:
        members = groups[key]
        sample = next(iter(members))
        bk = _base_key(sample)
        candidates = {key.replace("(", "").replace(")", "")}
        if bk:
            candidates.add(bk)
        for ck in candidates:
            owner_index.setdefault(ck, []).append(key)
    for bare_key in [k for k in groups if k not in paren_keys]:
        owners = owner_index.get(bare_key, [])
        if len(owners) == 1:
            groups[owners[0]].update(groups.pop(bare_key))

    def cls(n: str) -> int:
        return 0 if "_(" in n else (1 if "_" in n else (2 if "(" in n else 3))

    rep: dict[str, str] = {}
    for key, members in groups.items():
        best = sorted(members, key=lambda n: (cls(n), -members[n], n))[0]
        for n in members:
            rep[n] = best
    return rep, freq


# --- fixture 自检：任何解析回归都会让构建直接失败 ---
FIXTURES: list[tuple[str, set[str]]] = [
    ("artist:wlop, as109:1.2", {"wlop", "as109"}),
    ("(artist:wlop,as109:0.8)", {"wlop", "as109"}),
    ("2.5::cc_lin::, 0.9::ningen_mame::", {"cc_lin", "ningen_mame"}),
    ("0.8::dino(dinoartforame), wanke, liduke ::", {"dino(dinoartforame)", "wanke", "liduke"}),
    ("artist:henriiku_(ahemaru)  #{{{{huge_nipples}}}}", {"henriiku_(ahemaru)"}),
    ("(fuzichoco), atdan), (baocaizi:1.2)", {"fuzichoco", "atdan", "baocaizi"}),
    ("ask (askzy)，ask(askzy)、ask_(askzy)", {"ask_(askzy)"}),
    ("-4::artist collaboration::, {{masterpiece}}, best quality, year_2025, 4k", set()),
    ("achiki,au_(d_elete),[hito_komoru,tianliang_duohe_fangdongye],{toosaka_asagi},year_2023,",
     {"achiki", "au_(d_elete)", "hito_komoru", "tianliang_duohe_fangdongye", "toosaka_asagi"}),
    ("1.2::misaka12003-gou ::, misaka_12003-gou", {"misaka_12003-gou"}),
    ("{{Chinese fairy sophisticated charm}}, no modern elements", set()),
    ("aoi_sakura_(seak5545)、aoisakura(seak5545)、aoi sakura (seak5545)", {"aoi_sakura_(seak5545)"}),
    # --- 第二轮规则 ---
    ("[shuri_\\\\(84k\\\\)], artist:shuri_(84k)", {"shuri_(84k)"}),
    ("by ask (askzy), ask_(askzy), artist_ciloranko", {"ask_(askzy)", "ciloranko"}),
    ("meion,year_2025, meion_year2025, sos_adult_year2025", {"meion"}),
    ("alchemaniac., alchemaniac, Artistjasony", {"alchemaniac", "jasony"}),
    ("konomi_(konomi_takeshi) 25, xuedaixun(ink_wash_painting)", {"konomi_(konomi_takeshi)", "xuedaixun"}),
    ("1.5::2::3D::, artist:drive shot, pen (medium), large_areolae(puffy)", set()),
    ("machi (7769), machi_(7769), machi_(machi0910)", {"machi_(7769)", "machi_(machi0910)"}),
    ("channel_, channel_(caststation), au, au_(d_elete)", {"channel_(caststation)", "au_(d_elete)"}),
    ("artist:sho, artist_sho, sho_(sho_lwlw)", {"sho_(sho_lwlw)"}),
    ("画师串名：artist:wlop, artist:as109", {"wlop", "as109"}),
    ("5::soejima_shigenori(persona_5)::", {"soejima_shigenori"}),
]


def run_fixtures() -> None:
    bodies = [b for b, _ in FIXTURES]
    km, kb = _bootstrapped_knowns(bodies)
    for body, expected in FIXTURES:
        pool = artist_pool(body, km, kb)
        rep, _freq = _merge_variants(pool)  # 与 build() 的规范形后处理保持一致
        got = {rep[n] for n in pool}
        if got != expected:
            raise ValueError(f"fixture 失败: {body!r}\n  期望 {sorted(expected)}\n  实际 {sorted(got)}")


def parse_presets(path: Path) -> list[dict[str, object]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    headings = [(i, int(m.group(1)), m.group(2).strip())
                for i, line in enumerate(lines) if (m := HEADING_RE.match(line))]
    if not headings:
        raise ValueError(f"未找到 ### 编号预设: {path}")

    presets: list[dict[str, object]] = []
    for pos, (line_no, source_id, original_name) in enumerate(headings):
        end = headings[pos + 1][0] if pos + 1 < len(headings) else len(lines)
        opening = next((j for j in range(line_no + 1, end)
                        if lines[j].strip().lower().startswith("```text")), None)
        if opening is None:
            raise ValueError(f"预设 #{source_id}「{original_name}」缺少 text 代码块")
        closing = next((j for j in range(opening + 1, end)
                        if lines[j].strip().startswith("```")), None)
        if closing is None:
            raise ValueError(f"预设 #{source_id}「{original_name}」代码块未闭合")
        body = "\n".join(lines[opening + 1:closing]).strip()
        if not body:
            # Empty bodies occur in the source and are still valid plain-text presets.
            body = ""
        presets.append({"sourceId": source_id, "originalName": original_name, "body": body})

    ids = [int(p["sourceId"]) for p in presets]
    if len(ids) != len(set(ids)):
        raise ValueError("预设编号重复")
    return presets


def parse_rename_table(path: Path) -> dict[int, dict[str, str]]:
    result: dict[int, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [clean_cell(x) for x in line.strip().strip("|").split("|")]
        if len(cells) < 4 or not cells[0].startswith("#"):
            continue
        match = re.fullmatch(r"#\s*(\d+)", cells[0])
        if not match:
            continue
        result[int(match.group(1))] = {"name": cells[1], "originalName": cells[2], "category": cells[3]}
    if not result:
        raise ValueError(f"未解析到重命名表: {path}")
    return result


def clean_cell(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^\*+|\*+$", "", value).strip()
    return value


def parse_recommendations(path: Path) -> list[int]:
    text = path.read_text(encoding="utf-8-sig")
    # The first table is the overall RP recommendation list. Keep its source IDs.
    section = text.split("## 肉感", 1)[0]
    return [int(n) for n in re.findall(r"\|\s*#(\d+)\s*\|", section)]


def build(source: Path, rename: Path, recommendations: Path, report: bool = False) -> dict[str, object]:
    presets = parse_presets(source)
    renames = parse_rename_table(rename)
    if len(presets) != 299:
        print(f"提示: 权威源当前解析到 {len(presets)} 条（说明文字可能已更新）", file=sys.stderr)

    known_multiword, known_base = _bootstrapped_knowns([str(p["body"]) for p in presets])

    output_presets: list[dict[str, object]] = []
    category_counts: Counter[str] = Counter()
    all_pool_names: list[str] = []
    decisions: list[tuple[str, str, str]] = []
    for index, preset in enumerate(presets, 1):
        source_id = int(preset["sourceId"])
        metadata = renames.get(source_id)
        if metadata is None:
            raise ValueError(f"预设 #{source_id}「{preset['originalName']}」缺少重命名/分类映射")
        if metadata["originalName"] != preset["originalName"]:
            # Names are authoritative too; an ID-only accidental shift must not silently pass.
            raise ValueError(
                f"预设 #{source_id} 原名不一致: 源文件为「{preset['originalName']}」，"
                f"重命名表为「{metadata['originalName']}」"
            )
        category_counts[metadata["category"]] += 1
        body = str(preset["body"])
        if report:
            for raw in _iter_candidates(body):
                cand = _clean(raw)
                ok = _validate(cand, known_multiword, known_base)
                decisions.append((body[:0] + f"#{source_id}", raw, f"{'ACCEPT' if ok else 'reject'} {cand!r}"))
        pool = artist_pool(body, known_multiword, known_base)
        all_pool_names.extend(pool)
        output_presets.append({
            "id": index,
            "sourceId": source_id,
            "name": metadata["name"],
            "originalName": preset["originalName"],
            "category": metadata["category"],
            "prompt": body,
            "artistPool": pool,
        })

    rep, _freq = _merge_variants(all_pool_names)
    global_pool = sorted({rep[n] for n in all_pool_names}, key=str.casefold)
    for index, preset in enumerate(output_presets, 0):
        preset["artistPool"] = list(dict.fromkeys(rep[n] for n in preset["artistPool"]))  # type: ignore[index]

    if report:
        for sid, raw, verdict in decisions:
            print(f"{sid}  {verdict:<48} ← {raw[:70]!r}")
        empty = [p["id"] for p in output_presets if not p["artistPool"]]
        print(f"\n空池预设 {len(empty)} 个: {empty}", file=sys.stderr)

    recommended = parse_recommendations(recommendations)
    return {
        "version": 2,
        "source": "nai_artist_presets_clean.md",
        "count": len(output_presets),
        "categories": [{"name": name, "count": category_counts[name]}
                       for name in sorted(category_counts)],
        "recommendedIds": recommended,
        "artistPool": global_pool,
        "presets": output_presets,
    }


def assert_clean(data: dict[str, object]) -> None:
    """门禁：禁止权重量、反斜杠转义、残缺括号、分隔符、变体重复混入输出。
    重复检查只看全局池内部和单预设池内部——跨预设重复是正常的。"""
    def check(name: str) -> None:
        if any(ch in _FORBIDDEN for ch in name):
            raise ValueError(f"画师名含非法字符: {name!r}")
        if "\\" in name:
            raise ValueError(f"画师名残留转义符: {name!r}")
        if name != name.strip() or not name:
            raise ValueError(f"画师名含首尾空白: {name!r}")
        if name.count("(") != name.count(")"):
            raise ValueError(f"画师名括号不配对: {name!r}")
        if re.search(r"[,，、]", name):
            raise ValueError(f"画师名含分隔符: {name!r}")

    def check_no_dupes(names: list[str], scope: str) -> None:
        seen: set[str] = set()
        for name in names:
            check(name)
            k = _key(name)
            if k in seen:
                raise ValueError(f"{scope}变体归并失败，重复画师: {name!r}")
            seen.add(k)

    check_no_dupes(list(data["artistPool"]), "全局池")  # type: ignore[arg-type]
    for p in data["presets"]:  # type: ignore[union-attr]
        check_no_dupes(list(p["artistPool"]), f"预设#{p['sourceId']} ")  # type: ignore[arg-type]


def write_json(data: dict[str, object], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=destination.parent,
                            prefix=destination.name + ".", suffix=".tmp", delete=False) as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(destination)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=root / "nai_artist_presets_clean.md")
    parser.add_argument("--rename", type=Path, default=root / "预设重命名表.md")
    parser.add_argument("--recommendations", type=Path, default=root / "推荐与分类.md")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "public" / "artist-library.json")
    parser.add_argument("--report", action="store_true", help="打印逐候选判定结果用于调参")
    parser.add_argument("--skip-fixtures", action="store_true")
    args = parser.parse_args()
    if not args.skip_fixtures:
        run_fixtures()
        print(f"fixtures OK ({len(FIXTURES)} cases)")
    data = build(args.source, args.rename, args.recommendations, report=args.report)
    if not data["presets"] or not data["artistPool"]:  # type: ignore[index]
        raise ValueError("输出预设或 artistPool 为空")
    assert_clean(data)
    write_json(data, args.output)
    empty = sum(1 for p in data["presets"] if not p["artistPool"])  # type: ignore[union-attr]
    print(f"OK: {data['count']} presets, {len(data['artistPool'])} artists, "  # type: ignore[index]
          f"{len(data['categories'])} categories, {empty} empty-pool presets -> {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        raise SystemExit(1)
