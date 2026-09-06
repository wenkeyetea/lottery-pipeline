#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""基于 analysis.json(多地区) 生成 Markdown 研究报告 report.md。"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "analysis.json"), encoding="utf-8"))
ORDER = D["regions_order"]
REGIONS = D["regions"]


def region_section(name, R):
    lines = []
    A = lines.append
    m = R["meta"]
    nums = {n["num"]: n for n in R["numbers"]}
    by_freq = sorted(R["numbers"], key=lambda x: -x["freq_total"])
    by_cold = sorted(R["numbers"], key=lambda x: -x["last_seen"])
    pd = R["prediction_default"]
    chi = R["chi_square"]
    z_max = max(R["numbers"], key=lambda x: x["z_score"])
    z_min = min(R["numbers"], key=lambda x: x["z_score"])

    A(f"## {name}（{m['source']}）\n")
    A(f"> 统计口径：全部 {m['total_draws']} 期（{m['first_issue']} ~ {m['last_issue']}），共 {m['total_slots']} 槽位；理论期望/号 ≈ {m['expected_per_number']}\n")
    A("### 高频号码 Top10\n")
    A("| 排名 | 号码 | 生肖/五行 | 合计 | z |")
    A("| --- | --- | --- | --- | --- |")
    for i, n in enumerate(by_freq[:10], 1):
        A(f"| {i} | {n['num']} | {n['zodiac']}/{n['element']} | {n['freq_total']} | {n['z_score']:+} |")
    A("")
    A(f"> 最高频：**{z_max['num']}（{z_max['zodiac']}/{z_max['element']}）** z={z_max['z_score']:+}；最低频：**{z_min['num']}（{z_min['zodiac']}/{z_min['element']}）** z={z_min['z_score']:+}\n")
    A("### 当前遗漏最大 Top10\n")
    A("| 排名 | 号码 | 生肖/五行 | 遗漏 | 合计 |")
    A("| --- | --- | --- | --- | --- |")
    for i, n in enumerate(by_cold[:10], 1):
        A(f"| {i} | {n['num']} | {n['zodiac']}/{n['element']} | {n['last_seen']} | {n['freq_total']} |")
    A("")
    A("### 生肖 / 五行分布\n")
    zi = R["zodiac"]; el = R["element"]
    A("- 生肖：" + "，".join(f"{z}({c})" for z, c in sorted(zip(zi["labels"], zi["freq"]), key=lambda x: -x[1])))
    A("- 五行：" + "，".join(f"{e}({c})" for e, c in sorted(zip(el["labels"], el["freq"]), key=lambda x: -x[1])))
    A("")
    A("### 随机性检验（关键）\n")
    A(f"- χ² = {chi['chi2']}，df = {chi['df']}，近似 p = {chi['approx_p_value']}。")
    if chi["approx_p_value"] >= 0.05:
        A("- 结论：p ≥ 0.05，未检出显著偏离，**数据符合均匀随机**——不存在被操纵或必出的号码。")
    else:
        A("- 结论：p < 0.05，存在显著偏离，建议核查数据源。")
    A("")
    A("### 共现 Top5\n")
    A("| 组合 | 实际 | 期望 |")
    A("| --- | --- | --- |")
    for p in R["top_pairs"][:5]:
        A(f"| {p['pair'][0]} & {p['pair'][1]} | {p['count']} | {p['expected']} |")
    A("")
    A("### 逐年趋势\n")
    for y, v in R["yearly"].items():
        top = "，".join(f"{num}({c})" for num, c in v["top"])
        A(f"- **{y}**（{v['draws']} 期）Top5：{top}")
    A("")
    A("### 推算候选（默认近50期，热度40/稳定35/遗漏25）\n")
    A("- 正码池 Top10：" + "，".join(str(e['num']) for e in pd["main_pool"][:10]))
    A("- 特码候选 Top8：" + "，".join(str(e['num']) for e in pd["special_candidates"][:8]))
    A("")
    # 🤖 大模式AI算法综合推算（基于 ai_prediction 多维数据）
    pr = R.get("prediction")
    ap = pr.get("ai_prediction") if isinstance(pr, dict) else None
    if ap:
        A(f"### 🤖 大模式AI算法综合推算（第 {ap['next_issue']} 期参考）\n")
        A(f"- **正码推荐下一期（6个）**：" + "，".join(str(n) for n in ap["main_pick"]))
        A(f"- **特码推荐**：{ap['special_pick']}（生肖 {ap['special_zodiac']} · 五行 {ap['special_element']}）")
        A(f"- **特码生肖**：{ap['special_zodiac']}")
        A(f"- **重点3生肖**：" + "，".join(str(z) for z in ap["top3_zodiac"]))
        A(f"- **重点10数字**：" + "，".join(str(n) for n in ap["top10"]))
        A(f"- **五行排名**：" + " ｜ ".join(f"{e['element']}(分{e['score']},占{e['share']}%)" for e in ap["element_rank"]))
        A(f"- **波色排名**：" + " ｜ ".join(f"{w['wave']}(分{w['score']},占{w['share']}%)" for w in ap["wave_rank"]))
        A(f"- **单双推荐**：偏{ap['parity']['recommend']}（历史单 {ap['parity']['odd_share']}% / 双 {ap['parity']['even_share']}%）")
        A(f"- **尾数推荐**：" + "，".join(str(t) for t in ap["top_tails"]) + "（" + " ｜ ".join(f"{t['tail']}尾(分{t['score']})" for t in ap["tail_rank"][:3]) + "）")
        A(f"- **头数推荐**：" + "，".join(str(h) for h in ap["top_heads"]) + "（" + " ｜ ".join(f"{h['head']}头(分{h['score']})" for h in ap["head_rank"][:2]) + "）")
        A(f"- **2中2 · 20组**（每组2正码，2全中）：" + " ｜ ".join(" ".join(str(x) for x in g) for g in ap["pairs_2of2"]))
        A(f"- **3中3 · 20组**（每组3正码，3全中）：" + " ｜ ".join(" ".join(str(x) for x in g) for g in ap["triples_3of3"]))
        A("")
        A("> ⚠️ 推算基于历史统计规律（开奖为独立随机事件），仅供数据观察与娱乐参考，不构成任何中奖预测或投注建议。")
        A("")
    else:
        A("### 🤖 大模式AI算法综合推算\n")
        A("> 尚未生成推算数据（请先运行 predict_next.py）。")
        A("")

    # ===== 命中率记录：大模型命中记录(live_hits) + 回测(hit_records) =====
    A("### 🎯 命中率记录（数据观察，仅供娱乐参考）\n")

    # 1) 大模型真实命中记录（已关单的实际推荐 vs 实际开奖）
    lh = R.get("live_hits_summary")
    if lh:
        A(f"- **大模型真实命中记录**（已关单 {lh['closed_issues']} 期，基于当时真实推荐存档比对）：")
        A(f"  - 特码命中率：**{lh['special_hit']['hit_rate']*100:.2f}%**（{lh['special_hit']['hits']}/{lh['special_hit']['issues']}）")
        def _fmt_play(label, blk):
            # 兼容两种结构：扁平 {hit_rate,hits,groups,issues_with_hit}
            # 与按组数分层 {'20': {...}, '40': {...}, '60': {...}}
            if not isinstance(blk, dict):
                A(f"  - {label}：暂无数据")
                return
            if "hit_rate" in blk:
                A(f"  - {label}：{blk['hit_rate']*100:.2f}%（{blk.get('hits',0)}/{blk.get('groups',0)} 组，{blk.get('issues_with_hit',0)} 期有命中）")
                return
            parts = []
            for gk in sorted(blk.keys(), key=lambda x: int(x) if str(x).isdigit() else 0):
                g = blk.get(gk)
                if not isinstance(g, dict) or not g.get("groups"):
                    continue
                parts.append(f"{gk}组 {g['hit_rate']*100:.2f}%（{g['hits']}/{g['groups']}，{g['issues_with_hit']} 期有命中）")
            A(f"  - {label}：{' ｜ '.join(parts) if parts else '暂无数据'}")

        _fmt_play("2中2", lh.get("2of2"))
        _fmt_play("3中3", lh.get("3of3"))
        _fmt_play("3中2", lh.get("3of2"))
        z = lh["zodiac"]
        A(f"  - 生肖连肖命中率：1连 {z['1xiao']['hit_rate']*100:.1f}% ｜ 2连 {z['2xiao']['hit_rate']*100:.1f}% ｜ 3连 {z['3xiao']['hit_rate']*100:.1f}% ｜ 4连 {z['4xiao']['hit_rate']*100:.1f}% ｜ 5连 {z['5xiao']['hit_rate']*100:.1f}%")
        t = lh["tail"]
        A(f"  - 尾数连尾命中率：0尾 {t['0wei']['hit_rate']*100:.1f}% ｜ 1/9尾 {t['1_9wei']['hit_rate']*100:.1f}% ｜ 2尾 {t['2wei']['hit_rate']*100:.1f}% ｜ 3尾 {t['3wei']['hit_rate']*100:.1f}% ｜ 4尾 {t['4wei']['hit_rate']*100:.1f}% ｜ 5尾 {t['5wei']['hit_rate']*100:.1f}%")
        nh = lh["not_hit"]
        A(f"  - 自选不中中奖率：5不中 {nh['5']['hit_rate']*100:.1f}% ｜ 6不中 {nh['6']['hit_rate']*100:.1f}% ｜ 7不中 {nh['7']['hit_rate']*100:.1f}% ｜ 8不中 {nh['8']['hit_rate']*100:.1f}% ｜ 9不中 {nh['9']['hit_rate']*100:.1f}% ｜ 10不中 {nh['10']['hit_rate']*100:.1f}%")
    else:
        A("- **大模型真实命中记录**：暂无已关单数据（运行 close_issues.py 后生成）。")

    # 2) 回测命中率（模型重建版）
    hr = R.get("hit_records", {}).get("summary")
    if hr:
        s2, s3 = hr["2of2"], hr["3of3"]
        A(f"- **历史回测**（模型重建版，{s2['issues']} 期，每期20组）：")
        A(f"  - 2中2 命中率：**{s2['hit_rate']*100:.2f}%**（{s2['total_hits']}/{s2['total_groups']}，{s2['issues_with_hit']}/{s2['issues']} 期有命中）")
        A(f"  - 3中3 命中率：**{s3['hit_rate']*100:.2f}%**（{s3['total_hits']}/{s3['total_groups']}，{s3['issues_with_hit']}/{s3['issues']} 期有命中）")
    else:
        A("- **历史回测**：暂无数据（运行 backtest.py 后生成）。")

    # 3) 大模式AI综合推算命中记录（逐期存档，开奖后如实比对）
    ah = R.get("ai_live_hits_summary")
    if ah:
        A(f"- **🧠 大模式AI综合推算命中记录**（已关单 {ah['closed_issues']} 期，其中 {ah['rebuilt']} 期为功能上线前历史存档的回溯重建）：")
        m = ah["main"]
        A(f"  - 正码命中率：{m['hit_rate']*100:.2f}%（共 {m['hits']}/{m['total']}，均中 {m['avg_hit']}/6，{m['issues_with_hit']}/{ah['closed_issues']} 期有命中）")
        sp = ah["special_hit"]
        A(f"  - 特码命中率：{sp['hit_rate']*100:.2f}%（{sp['hits']}/{sp['issues']}）")
        zd = ah["zodiac_hit"]
        A(f"  - 3生肖特码命中率：{zd['hit_rate']*100:.2f}%（{zd['hits']}/{zd['issues']}，特码生肖在推荐3生肖内）")
        t10 = ah["top10_hit"]
        A(f"  - 特码10数字命中率：{t10['hit_rate']*100:.2f}%（{t10['hits']}/{t10['issues']}，特码在推荐10数字内）")
        k2 = ah["2of2"]
        A(f"  - 2中2 命中率：{k2['hit_rate']*100:.2f}%（{k2['hits']}/{k2['groups']} 组，{k2['issues_with_hit']}/{ah['closed_issues']} 期有命中）")
        k3 = ah["3of3"]
        A(f"  - 3中3 命中率：{k3['hit_rate']*100:.2f}%（{k3['hits']}/{k3['groups']} 组，{k3['issues_with_hit']}/{ah['closed_issues']} 期有命中）")
    else:
        A("- **🧠 大模式AI综合推算命中记录**：暂无数据（运行 close_issues.py 后生成）。")
    A("")
    return lines


lines = []
A = lines.append
A("# 开奖数据 · 统计研究与推算报告（老澳 / 澳门 / 香港）\n")
A("> 本报告由 analysis.json 自动生成。三地区均使用统一的「号码→生肖/五行」对照表（以老澳为准），统计口径一致。\n")
A("---\n")
A("## 研究方法\n")
A("1. **频率统计**：每号出现次数 + z 分数衡量偏离。2. **随机性检验**：卡方拟合优度（原假设每号等概率）。3. **遗漏分析**：距上次出现的期数。4. **共现分析**：两两同现 vs 理论期望。5. **推算模型**：热度/稳定/遗漏加权打分（权重与窗口可在仪表盘调）。\n")
A("---\n")
for name in ORDER:
    lines += region_section(name, REGIONS[name])
A("## 智能体使用方式\n")
A("```text\nlaoya_analysis/\n├── engine.py        # 统计引擎：CSV → analysis.json（支持三地区）\n├── fetch_data.py    # 抓取澳门/香港历史并转CSV\n├── build_dashboard.py / build_report.py / predict_next.py\n├── 老澳_2024-2026完整开奖.csv / 澳门.csv / 香港.csv（新澳门.csv 已弃用，与澳门重复）\n├── analysis.json / index.html / report.md / recommendation.md\n```\n")
A("## 免责声明\n")
A("- 彩票每期开奖为**独立随机事件**，过去号码不影响未来结果。")
A("- 所有频率、冷热、推算**仅供数据观察与娱乐参考**，不构成投注建议。")
A("- 请理性购彩，量力而行，**切勿用于赌博投入**。")
A("")

open(os.path.join(HERE, "report.md"), "w", encoding="utf-8").write("\n".join(lines))
print("已生成 -> report.md，覆盖地区：", ORDER)
