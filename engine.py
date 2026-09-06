#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
老澳/澳门/香港 开奖数据 · 统计研究 & 推算引擎（多地区版）
========================================================
输入 : 三个地区的 CSV（同格式：年份,期号,正码1..6(生肖/五行),特码(生肖/五行)）
输出 : analysis.json  -> { regions_order:[...], regions:{地区:{...}} }
       每个地区的数据结构与旧版单地区 analysis.json 完全一致，便于前端逐地区消费。

说明 : 本引擎只做「历史数据统计 + 多因子打分」，不涉及任何"必中"承诺。
       彩票本质是独立随机事件，任何模型都无法提高真实中奖概率。
       本工具定位为「数据可视化 + 参考选号」，请勿用于赌博投入。
"""

import csv
import json
import re
import sys
import math
import os
from collections import defaultdict, Counter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "analysis.json")

# 三个地区配置：(展示名, CSV文件名)
# 注：新澳门（55128.cn）与「澳门」号码相同，用户确认仪表盘只保留 老澳/澳门/香港 三地区。
REGIONS = [
    ("老澳", "老澳_2024-2026完整开奖.csv"),
    ("澳门", "澳门.csv"),
    ("香港", "香港.csv"),
]

CELL_RE = re.compile(r'(\d+)\(([^/]+)/([^)]+)\)')
ZODIAC_ORDER = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
ELEMENTS = ["金", "木", "水", "火", "土"]
RANGES = [("01-10", 1, 10), ("11-20", 11, 20), ("21-30", 21, 30),
          ("31-40", 31, 40), ("41-49", 41, 49)]

# 波色标准映射（六合彩：红波/蓝波/绿波）
WAVE = {}
for _n in [1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46]:
    WAVE[_n] = "红波"
for _n in [3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48]:
    WAVE[_n] = "蓝波"
for _n in [5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49]:
    WAVE[_n] = "绿波"
WAVE_COLORS = ["红波", "蓝波", "绿波"]


def omission(seq_present, draws):
    """seq_present: list[bool]（旧→新，每期是否出现）。返回 当前遗漏/历史最大遗漏/最近出现期号。"""
    cur = 0
    for ap in reversed(seq_present):
        if ap:
            break
        cur += 1
    maxo = run = 0
    for ap in seq_present:
        run = 0 if ap else run + 1
        if run > maxo:
            maxo = run
    last_idx = None
    for i in range(len(seq_present) - 1, -1, -1):
        if seq_present[i]:
            last_idx = i
            break
    last_issue = draws[last_idx]["issue"] if last_idx is not None else None
    return {"current": cur, "max": maxo, "last_issue": last_issue}


def parse_cell(c):
    """'48(羊/土)' -> (48, '羊', '土') ; 解析失败返回 None"""
    m = CELL_RE.search(c)
    if not m:
        return None
    return int(m.group(1)), m.group(2), m.group(3)


def analyze(csv_path, source_name):
    """对单个地区的 CSV 做完整统计分析，返回与旧版一致的数据字典。"""
    draws = []          # 每期: {issue, year, mains:[6], special, all7:[7]}
    num_zodiac = defaultdict(Counter)
    num_element = defaultdict(Counter)

    with open(csv_path, encoding="gb18030", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            issue = row["期号"].strip()
            year = row["年份"].strip()
            mains, special = [], None
            all7 = []
            ok = True
            for col in [f"正码{i}" for i in range(1, 7)] + ["特码"]:
                p = parse_cell(row[col])
                if not p:
                    ok = False
                    break
                num, zod, ele = p
                num_zodiac[num][zod] += 1
                num_element[num][ele] += 1
                if col == "特码":
                    special = num
                else:
                    mains.append(num)
                all7.append(num)
            if not ok or len(mains) != 6 or special is None:
                continue
            draws.append({"issue": issue, "year": year,
                          "mains": mains, "special": special, "all7": all7})

    total_draws = len(draws)
    total_slots = total_draws * 7
    print(f"[{source_name}] 有效期数={total_draws}, 总号码槽位={total_slots}", file=sys.stderr)

    # ---------- 号码频率 ----------
    freq_main = Counter()
    freq_special = Counter()
    freq_total = Counter()
    for d in draws:
        for n in d["mains"]:
            freq_main[n] += 1
        freq_special[d["special"]] += 1
        for n in d["all7"]:
            freq_total[n] += 1

    p = 1 / 49.0
    exp_total = total_slots * p
    var_total = total_slots * p * (1 - p)
    exp_main = total_draws * 6 * p
    exp_special = total_draws * p

    last_seen = {}
    last_special_seen = {}
    seen = {}
    seen_special = {}
    for idx in range(total_draws - 1, -1, -1):
        d = draws[idx]
        for n in d["all7"]:
            if n not in seen:
                seen[n] = total_draws - 1 - idx
        if d["special"] not in seen_special:
            seen_special[d["special"]] = total_draws - 1 - idx
    for n in range(1, 50):
        last_seen[n] = seen.get(n, total_draws)
        last_special_seen[n] = seen_special.get(n, total_draws)

    # ---------- 生肖 / 五行 分布 ----------
    zodiac_counter = Counter()
    element_counter = Counter()
    zodiac_special = Counter()
    element_special = Counter()
    for d in draws:
        for n in d["mains"]:
            zodiac_counter[num_zodiac[n].most_common(1)[0][0]] += 1
            element_counter[num_element[n].most_common(1)[0][0]] += 1
        sz = num_zodiac[d["special"]].most_common(1)[0][0]
        se = num_element[d["special"]].most_common(1)[0][0]
        zodiac_special[sz] += 1
        element_special[se] += 1
        zodiac_counter[sz] += 1
        element_counter[se] += 1

    # ---------- 生肖遗漏预警（正码 / 特码） ----------
    # 每个号码固定对应一个生肖（取主生肖）
    num_to_zodiac = {n: num_zodiac[n].most_common(1)[0][0] for n in range(1, 50)}
    # 每期正码(①–⑥)出现的生肖集合；每期特码对应生肖
    main_zodiac_seq = [set(num_to_zodiac[n] for n in d["mains"]) for d in draws]
    spec_zodiac_seq = [num_to_zodiac[d["special"]] for d in draws]

    def _warn_for(get_present):
        items = []
        for z in ZODIAC_ORDER:
            items.append({"zodiac": z, **omission(get_present(z), draws)})
        items.sort(key=lambda x: -x["current"])
        return items

    zodiac_warning_main = _warn_for(lambda z: [z in main_zodiac_seq[i] for i in range(total_draws)])
    zodiac_warning_special = _warn_for(lambda z: [spec_zodiac_seq[i] == z for i in range(total_draws)])

    # ---------- 号码级遗漏预警（正码 / 特码） ----------
    num_to_element = {n: num_element[n].most_common(1)[0][0] for n in range(1, 50)}
    num_warn_main = []
    num_warn_special = []
    for n in range(1, 50):
        num_warn_special.append(
            {"num": n, **omission([draws[i]["special"] == n for i in range(total_draws)], draws)})
        num_warn_main.append(
            {"num": n, **omission([n in draws[i]["mains"] for i in range(total_draws)], draws)})
    num_warn_special.sort(key=lambda x: -x["current"])
    num_warn_main.sort(key=lambda x: -x["current"])

    # ---------- 波色遗漏预警（正码 / 特码） ----------
    def _color_warn(get_present):
        items = []
        for c in WAVE_COLORS:
            items.append({"color": c, **omission(get_present(c), draws)})
        items.sort(key=lambda x: -x["current"])
        return items
    color_warn_special = _color_warn(lambda c: [WAVE[draws[i]["special"]] == c for i in range(total_draws)])
    color_warn_main = _color_warn(lambda c: [any(WAVE[m] == c for m in draws[i]["mains"]) for i in range(total_draws)])

    # ---------- 五行遗漏预警（正码 / 特码） ----------
    def _elem_warn(get_present):
        items = []
        for e in ELEMENTS:
            items.append({"element": e, **omission(get_present(e), draws)})
        items.sort(key=lambda x: -x["current"])
        return items
    elem_warn_special = _elem_warn(lambda e: [num_to_element[draws[i]["special"]] == e for i in range(total_draws)])
    elem_warn_main = _elem_warn(lambda e: [any(num_to_element[m] == e for m in draws[i]["mains"]) for i in range(total_draws)])

    # ---------- 奇偶 / 区间 ----------
    parity = {"odd": 0, "even": 0}
    for n, c in freq_total.items():
        parity["odd" if n % 2 else "even"] += c
    range_counter = Counter()
    for label, lo, hi in RANGES:
        range_counter[label] = sum(freq_total[n] for n in range(lo, hi + 1))

    # ---------- 卡方拟合优度 ----------
    obs = [freq_total.get(n, 0) for n in range(1, 50)]
    exp_each = total_slots / 49.0
    chi2 = sum((o - exp_each) ** 2 / exp_each for o in obs)
    df = 48
    z = math.sqrt(2 * chi2) - math.sqrt(2 * df - 1)
    p_val = 0.5 * (1 - math.erf(z / math.sqrt(2)))
    chi_info = {"chi2": round(chi2, 2), "df": df,
                "expected_per_number": round(exp_each, 2),
                "approx_p_value": round(p_val, 4),
                "note": "p值越大越接近均匀随机; p<0.05 可认为存在显著偏离(通常源于抽样波动)"}

    # ---------- 共现 ----------
    co = defaultdict(int)
    for d in draws:
        s = sorted(d["all7"])
        for i in range(len(s)):
            for j in range(i + 1, len(s)):
                co[(s[i], s[j])] += 1
    pair_expected = total_draws * (7 / 49.0) * (6 / 48.0)
    top_pairs = sorted(co.items(), key=lambda x: x[1], reverse=True)[:15]

    # ---------- 逐年趋势 ----------
    yearly = defaultdict(lambda: {"draws": 0, "freq": Counter()})
    for d in draws:
        y = yearly[d["year"]]
        y["draws"] += 1
        for n in d["all7"]:
            y["freq"][n] += 1

    # ---------- 推算模型 ----------
    def norm(vals):
        vs = list(vals.values())
        lo, hi = min(vs), max(vs)
        if hi == lo:
            return {k: 50 for k in vals}
        return {k: 100 * (v - lo) / (hi - lo) for k, v in vals.items()}

    stable = {n: freq_total.get(n, 0) for n in range(1, 50)}
    stable_n = norm(stable)

    def predict(window):
        recent_hits = Counter()
        recent_special = Counter()
        for d in draws[-window:]:
            for n in d["all7"]:
                recent_hits[n] += 1
            recent_special[d["special"]] += 1
        hot_n = norm({n: recent_hits.get(n, 0) for n in range(1, 50)})
        due_n = norm({n: last_seen[n] for n in range(1, 50)})

        main_score = {}
        for n in range(1, 50):
            main_score[n] = round(0.40 * hot_n[n] + 0.35 * stable_n[n] + 0.25 * due_n[n], 2)
        sp_stable = norm({n: freq_special.get(n, 0) for n in range(1, 50)})
        sp_hot = norm({n: recent_special.get(n, 0) for n in range(1, 50)})
        sp_due = norm({n: last_special_seen[n] for n in range(1, 50)})
        special_score = {}
        for n in range(1, 50):
            special_score[n] = round(0.40 * sp_hot[n] + 0.35 * sp_stable[n] + 0.25 * sp_due[n], 2)

        main_rank = sorted(range(1, 50), key=lambda n: main_score[n], reverse=True)
        special_rank = sorted(range(1, 50), key=lambda n: special_score[n], reverse=True)
        return {
            "window": window,
            "main_pool": [{"num": n, "score": main_score[n],
                           "freq": freq_total.get(n, 0),
                           "recent": recent_hits.get(n, 0),
                           "last_seen": last_seen[n]} for n in main_rank[:20]],
            "special_candidates": [{"num": n, "score": special_score[n],
                                    "freq_sp": freq_special.get(n, 0),
                                    "recent_sp": recent_special.get(n, 0),
                                    "last_seen_sp": last_special_seen[n]} for n in special_rank[:12]],
        }

    default_pred = predict(50)

    # ---------- 组装 ----------
    numbers = []
    for n in range(1, 50):
        z = (freq_total.get(n, 0) - exp_total) / math.sqrt(var_total)
        numbers.append({
            "num": n,
            "zodiac": num_zodiac[n].most_common(1)[0][0],
            "element": num_element[n].most_common(1)[0][0],
            "freq_main": freq_main.get(n, 0),
            "freq_special": freq_special.get(n, 0),
            "freq_total": freq_total.get(n, 0),
            "z_score": round(z, 3),
            "last_seen": last_seen[n],
            "last_special_seen": last_special_seen[n],
        })

    compact_draws = [[int(d["year"]), d["issue"], d["mains"], d["special"]] for d in draws]

    out = {
        "meta": {
            "source": source_name,
            "total_draws": total_draws,
            "first_issue": draws[0]["issue"],
            "last_issue": draws[-1]["issue"],
            "total_slots": total_slots,
            "expected_per_number": round(exp_each, 2),
            "expected_main_per_number": round(exp_main, 2),
            "expected_special_per_number": round(exp_special, 2),
            "generated_at": "",
        },
        "numbers": numbers,
        "zodiac": {"labels": ZODIAC_ORDER,
                   "freq": [zodiac_counter[z] for z in ZODIAC_ORDER],
                   "special": [zodiac_special[z] for z in ZODIAC_ORDER]},
        "zodiac_warning": {"main": zodiac_warning_main, "special": zodiac_warning_special},
        "number_warning": {"main": num_warn_main, "special": num_warn_special},
        "color_warning": {"main": color_warn_main, "special": color_warn_special},
        "element_warning": {"main": elem_warn_main, "special": elem_warn_special},
        "element": {"labels": ELEMENTS,
                    "freq": [element_counter[e] for e in ELEMENTS],
                    "special": [element_special[e] for e in ELEMENTS]},
        "parity": parity,
        "ranges": [{"label": l, "freq": range_counter[l]} for l, _, _ in RANGES],
        "chi_square": chi_info,
        "top_pairs": [{"pair": list(k), "count": v,
                       "expected": round(pair_expected, 1)}
                      for k, v in top_pairs],
        "yearly": {y: {"draws": v["draws"], "top": v["freq"].most_common(5)}
                   for y, v in sorted(yearly.items())},
        "prediction_default": default_pred,
        "draws": compact_draws,
    }

    # 控制台摘要
    print(f"\n=== {source_name} 概览 ===")
    print(f"期数:{total_draws}  槽位:{total_slots}  期望每号:{exp_each:.1f}")
    print(f"卡方={chi_info['chi2']}  df=48  近似p={chi_info['approx_p_value']}")
    print(f"正码高频 Top5: " + ", ".join(
        f"{n:02d}{num_zodiac[n].most_common(1)[0][0]}/{num_element[n].most_common(1)[0][0]}({c})"
        for n, c in freq_total.most_common(5)))
    print(f"特码高频 Top5: " + ", ".join(f"{n:02d}({c})" for n, c in freq_special.most_common(5)))
    return out


def main():
    regions = {}
    order = []
    for name, fn in REGIONS:
        path = os.path.join(HERE, fn)
        if not os.path.exists(path):
            print(f"[跳过] 缺少 {fn}", file=sys.stderr)
            continue
        order.append(name)
        regions[name] = analyze(path, name)

    out = {"regions_order": order, "regions": regions}
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n[完成] 已写出 -> {OUT_PATH}  (地区: {order})", file=sys.stderr)


if __name__ == "__main__":
    main()
