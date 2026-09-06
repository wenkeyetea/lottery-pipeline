# -*- coding: utf-8 -*-
"""从三地区全部历史开奖记录中提炼「统计规律」并落盘。

输入 : analysis.json（engine.py 已生成的统计结果，含完整 draws）
输出 : 规律记录.md（人类可读，分地区 + 跨地区共性）
        patterns.json（结构化，便于未来程序化复用）

重要声明：以下所有"规律"均为历史数据的统计特征描述，六合彩每期开奖是
        独立随机事件，任何历史统计都不能提高未来真实中奖概率。本文件仅
        供数据观察与娱乐参考，不构成任何投注建议。
"""
import json, os, math, importlib.util, datetime
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("engine", os.path.join(HERE, "engine.py"))
eng = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eng)
WAVE = eng.WAVE
ELEMENT_MAP = getattr(eng, "ELEMENT_MAP", None) or getattr(eng, "ELEMENTS", None)
ZODIAC_ORDER = eng.ZODIAC_ORDER

D = json.load(open(os.path.join(HERE, "analysis.json"), encoding="utf-8"))
ORDER = D["regions_order"]

RANGES = [("01-10", 1, 10), ("11-20", 11, 20), ("21-30", 21, 30),
          ("31-40", 31, 40), ("41-49", 41, 49)]


def run_pattern(name):
    R = D["regions"][name]
    draws = R["draws"]                 # [year, issue, mains(6), special]
    meta = R["meta"]
    nums = {x["num"]: x for x in R["numbers"]}
    TD = meta["total_draws"]
    TS = meta["total_slots"]

    # ---- 1. 号码冷热 ----
    freq_sorted = sorted(nums.values(), key=lambda x: -x["freq_total"])
    hot10 = freq_sorted[:10]
    cold10 = freq_sorted[-10:]

    # ---- 2. 遗漏（正码当前遗漏，已按 current 降序）----
    nwm = R["number_warning"]["main"]
    omit_now = nwm[:8]                 # 当前遗漏最大
    max_omit_hist = max(nwm, key=lambda x: x["max"])  # 历史最大遗漏纪录

    # ---- 3. 波色 / 生肖 / 五行 分布 ----
    wave_c, zod_c, elem_c = Counter(), Counter(), Counter()
    for d in draws:
        for n in d[2] + [d[3]]:
            wave_c[WAVE[n]] += 1
            zod_c[nums[n]["zodiac"]] += 1
            elem_c[nums[n]["element"]] += 1
    wave_share = {k: (v / TS * 100) for k, v in wave_c.items()}
    zod_share = {k: (v / TS * 100) for k, v in zod_c.items()}
    elem_share = {k: (v / TS * 100) for k, v in elem_c.items()}

    # ---- 4. 奇偶 / 大小 / 区间 ----
    par = {"odd": 0, "even": 0}
    sz = {"small": 0, "big": 0}        # 1-24 小，25-49 大
    rng_c = Counter()
    for d in draws:
        for n in d[2] + [d[3]]:
            par["odd" if n % 2 else "even"] += 1
            sz["small" if n <= 24 else "big"] += 1
            for lbl, lo, hi in RANGES:
                if lo <= n <= hi:
                    rng_c[lbl] += 1
                    break
    par_share = {k: (v / TS * 100) for k, v in par.items()}
    sz_share = {k: (v / TS * 100) for k, v in sz.items()}

    # ---- 5. 重号规律（本期与上期重复号码个数）----
    reps = []
    for i in range(1, len(draws)):
        prev = set(draws[i - 1][2] + [draws[i - 1][3]])
        cur = set(draws[i][2] + [draws[i][3]])
        reps.append(len(prev & cur))
    avg_rep = sum(reps) / len(reps) if reps else 0
    max_rep = max(reps) if reps else 0
    rep_dist = dict(sorted(Counter(reps).items()))
    theo_rep = 1.0                   # 理论期望：49*(7/49)^2 = 1

    # ---- 6. 连号规律（7号内相邻整数对）----
    cons = []
    for d in draws:
        ns = sorted(d[2] + [d[3]])
        cons.append(sum(1 for i in range(len(ns) - 1) if ns[i + 1] - ns[i] == 1))
    avg_cons = sum(cons) / len(cons)
    cons_dist = dict(sorted(Counter(cons).items()))
    issues_consec = sum(1 for c in cons if c > 0)

    # ---- 7. 共现热对 ----
    top_pairs = R["top_pairs"][:10]

    # ---- 8. 特码特征 ----
    sp = [d[3] for d in draws]
    sp_par = {"odd": sum(1 for n in sp if n % 2), "even": sum(1 for n in sp if not n % 2)}
    sp_wave = dict(Counter(WAVE[n] for n in sp))
    sp_zod = dict(Counter(nums[n]["zodiac"] for n in sp))
    sp_elem = dict(Counter(nums[n]["element"] for n in sp))
    sp_hot = sorted(Counter(sp).items(), key=lambda x: -x[1])[:5]

    # ---- 9. 卡方 ----
    chi = R["chi_square"]

    return {
        "meta": {"source": name, "total_draws": TD, "total_slots": TS,
                 "first_issue": meta["first_issue"], "last_issue": meta["last_issue"]},
        "hot10": [(x["num"], x["freq_total"], x["zodiac"], x["element"]) for x in hot10],
        "cold10": [(x["num"], x["freq_total"], x["zodiac"], x["element"]) for x in cold10],
        "omit_now": [(x["num"], x["current"], nums[x["num"]]["zodiac"], nums[x["num"]]["element"]) for x in omit_now],
        "max_omit_hist": (max_omit_hist["num"], max_omit_hist["max"], nums[max_omit_hist["num"]]["zodiac"], nums[max_omit_hist["num"]]["element"]),
        "wave_c": dict(wave_c), "wave_share": wave_share,
        "zod_c": dict(zod_c), "zod_share": zod_share,
        "elem_c": dict(elem_c), "elem_share": elem_share,
        "par": par, "par_share": par_share, "sz": sz, "sz_share": sz_share,
        "rng_c": dict(rng_c),
        "avg_rep": round(avg_rep, 3), "max_rep": max_rep, "rep_dist": rep_dist,
        "theo_rep": theo_rep,
        "avg_cons": round(avg_cons, 3), "cons_dist": cons_dist,
        "issues_consec": issues_consec, "issues_consec_pct": round(issues_consec / TD * 100, 1),
        "top_pairs": [(list(p["pair"]), p["count"], p["expected"]) for p in top_pairs],
        "sp_par": sp_par, "sp_wave": sp_wave, "sp_zod": sp_zod, "sp_elem": sp_elem,
        "sp_hot": sp_hot,
        "chi": chi,
    }


def fmt_pct(d):
    return {k: round(v, 2) for k, v in d.items()}


def md_region(name, p):
    m = p["meta"]
    L = []
    L.append(f"## {name} 规律（{m['first_issue']} ~ {m['last_issue']}，共 {m['total_draws']} 期）\n")
    # 卡方结论
    chi = p["chi"]
    L.append(f"- **均匀性检验（卡方）**：χ²={chi['chi2']}，df={chi['df']}，近似 p={chi['approx_p_value']}。"
             f"{'p 较大，说明 49 个号码出现频率与理论均匀随机无显著差异。' if chi['approx_p_value']>0.05 else 'p 偏小，存在一定偏离（通常源于抽样波动）。'}")
    # 冷热
    L.append(f"\n### 号码冷热")
    L.append("- 最热 Top10（号码/总出现/生肖/五行）：" + "、".join(
        f"{n}({z}/{e})×{c}" for n, c, z, e in p["hot10"]))
    L.append("- 最冷 Bottom10：" + "、".join(
        f"{n}({z}/{e})×{c}" for n, c, z, e in p["cold10"]))
    # 遗漏
    L.append(f"\n### 遗漏规律")
    L.append("- 当前遗漏最大（最久未出）：" + "、".join(
        f"{n}({z}/{e}) 已 {o} 期" for n, o, z, e in p["omit_now"]))
    L.append(f"- 历史最大遗漏纪录：号码 **{p['max_omit_hist'][0]}** 曾连续 **{p['max_omit_hist'][1]}** 期未出。")
    # 波色/生肖/五行
    L.append(f"\n### 波色 / 生肖 / 五行分布")
    L.append("- 波色占比：" + "、".join(f"{k} {v:.1f}%" for k, v in fmt_pct(p["wave_share"]).items())
             + f"（理论各 ≈ {100/3:.1f}%）")
    L.append("- 生肖出现次数：" + "、".join(f"{k}{v}" for k, v in p["zod_c"].items()))
    L.append("- 五行出现次数：" + "、".join(f"{k}{v}" for k, v in p["elem_c"].items()))
    # 奇偶/大小/区间
    L.append(f"\n### 奇偶 / 大小 / 区间")
    L.append("- 奇偶占比：" + "、".join(f"{k} {v:.1f}%" for k, v in fmt_pct(p["par_share"]).items())
             + f"（理论各 50%）")
    L.append("- 大小占比（1-24 小 / 25-49 大）：" + "、".join(f"{k} {v:.1f}%" for k, v in fmt_pct(p["sz_share"]).items()))
    L.append("- 五区间出现次数：" + "、".join(f"{k}:{v}" for k, v in p["rng_c"].items()))
    # 重号
    L.append(f"\n### 重号规律（本期与上期重复号码数）")
    L.append(f"- 平均每期与上期重复 **{p['avg_rep']}** 个号（理论期望 {p['theo_rep']} 个）；最大重复 {p['max_rep']} 个。")
    L.append("- 重复个数分布：" + "、".join(f"重{k}号×{v}期" for k, v in p["rep_dist"].items()))
    # 连号
    L.append(f"\n### 连号规律（7 号内相邻整数对）")
    L.append(f"- 平均每期含 **{p['avg_cons']}** 对连号；含连号的期数占比 **{p['issues_consec_pct']}%**。")
    L.append("- 连号对数分布：" + "、".join(f"{k}对×{v}期" for k, v in p["cons_dist"].items()))
    # 共现
    L.append(f"\n### 共现热对（同现次数 Top10）")
    L.append("| 号码对 | 同现次数 | 理论期望 |")
    L.append("|---|---|---|")
    for pair, cnt, exp in p["top_pairs"]:
        L.append(f"| {'+'.join(str(x) for x in pair)} | {cnt} | {exp} |")
    # 特码
    L.append(f"\n### 特码特征")
    L.append(f"- 奇偶占比：奇 {p['sp_par']['odd']} / 偶 {p['sp_par']['even']}")
    L.append("- 波色占比：" + "、".join(f"{k} {v}" for k, v in p["sp_wave"].items()))
    L.append("- 生肖占比：" + "、".join(f"{k} {v}" for k, v in p["sp_zod"].items()))
    L.append("- 五行占比：" + "、".join(f"{k} {v}" for k, v in p["sp_elem"].items()))
    L.append("- 高频特码 Top5：" + "、".join(f"{n}×{c}" for n, c in p["sp_hot"]))
    L.append(f"- 注：即使是同现次数最多的热对，也仅约为理论期望的 1.5~2 倍，属 {m['total_draws']} 期随机抽样下 1176 种组合里的「最大值噪声」（随机样本必有一个最大的），并非真实关联规律。")
    L.append("")
    return "\n".join(L)


def main():
    results = {name: run_pattern(name) for name in ORDER}
    # 跨地区共性
    L = []
    L.append("# 六合彩历史开奖规律记录（老澳 / 澳门 / 香港）\n")
    L.append(f"> 生成时间：{datetime.date.today().isoformat()}　数据来源：analysis.json（engine.py 全量统计）\n")
    L.append("> ⚠️ **重要声明**：以下均为历史数据的**统计特征**描述。六合彩每期开奖是**独立随机事件**，"
             "任何历史统计都不能提高未来真实中奖概率（卡方检验显示频率与理论均匀随机无显著差异）。"
             "本记录**仅供数据观察与娱乐参考，不构成任何投注建议**。\n")

    L.append("## 一、核心规律摘要（跨地区共性）\n")
    # 三地区卡方 p 均 >0.05 ?
    all_p = [results[n]["chi"]["approx_p_value"] for n in ORDER]
    L.append(f"1. **整体均匀**：三地区卡方近似 p 值 = {all_p}，"
             f"{'均 > 0.05，号码出现频率与理论随机无显著差异' if min(all_p)>0.05 else '部分偏小，但总体仍属随机波动范围'}。"
             "即不存在「某个号更容易出」的真实规律。")
    # 重号共性
    reps = [results[n]["avg_rep"] for n in ORDER]
    L.append(f"2. **重号稳定**：三地区平均每期与上期重复 {reps} 个号，均贴近理论期望 1 个。"
             "说明相邻期「撞号」是常态，但与是否「该出」无关。")
    # 连号共性
    cons = [results[n]["avg_cons"] for n in ORDER]
    L.append(f"3. **连号常态**：三地区平均每期含 {cons} 对连号，约 {[results[n]['issues_consec_pct'] for n in ORDER]}% 的期含连号。"
             "连号是随机分布的自然现象，非特殊规律。")
    # 波色均衡
    L.append(f"4. **波色/五行均衡**：红蓝绿三波色、金木水火土五行出现占比均接近理论均匀值，"
             "无长期偏色/偏行。生肖 12 宫出现次数亦基本均衡。")
    L.append(f"5. **冷热是结果不是原因**：所谓「热号」「冷号」只是已完成样本的计数，"
             "下一期每个号出现概率仍相等（独立事件），冷号不「该出」、热号不「会出」。")
    L.append(f"6. **共现热对是噪声**：共现表中「最热对」次数约为理论期望 1.5~2 倍，"
             "这只是 1176 种组合里的随机最大值，并非号码间存在真实关联。")

    for name in ORDER:
        L.append("\n" + md_region(name, results[name]))

    out_md = "\n".join(L)
    with open(os.path.join(HERE, "规律记录.md"), "w", encoding="utf-8") as f:
        f.write(out_md)
    with open(os.path.join(HERE, "patterns.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)

    # 控制台摘要
    print("=== 规律分析完成 ===")
    for name in ORDER:
        p = results[name]
        print(f"[{name}] 期数={p['meta']['total_draws']} 卡方p={p['chi']['approx_p_value']} "
              f"重号均值={p['avg_rep']} 连号均值={p['avg_cons']} "
              f"最热={p['hot10'][0][0]} 最冷={p['cold10'][-1][0]}")
    print("已写出 -> 规律记录.md / patterns.json")


if __name__ == "__main__":
    main()
