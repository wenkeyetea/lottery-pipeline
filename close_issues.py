# -*- coding: utf-8 -*-
"""关单脚本：把「真实推荐存档」recommendations_archive.json 中已开奖的期号，
   与实际开奖(6 正码 + 1 特码)比对，计算全部玩法的真实命中，写回 analysis.json
   的 regions[name]['live_hits']。

   意义：
     - 历史命中台账(backtest.hit_records)是「模型重建版」——用当前模型按确定性种子重建每期推荐并比对，
       用于观察整体命中率分布，但不等于当时真实展示/推荐的号码（旧期未存档，无法还原）。
     - live_hits 是「真实存档版」——每次 predict_next.py 推算时，已把实际推荐的号码按
       「针对哪一期(next_issue)」存进 recommendations_archive.json；本脚本待该期开奖后如实比对，
       命中记录 100% 忠实于当时推荐。

   玩法定义（与用户核定一致，来源：玩法规则截图）：
     - 2中2：该组 2 个号码都在当期 6 正码中（赔60倍）。
     - 3中3：该组 3 个号码都在当期 6 正码中（即 3 个全中，赔600倍）。
     - 3中2：该组 3 个号码中至少 2 个在当期 6 正码中（赔19倍）。
     - 生肖连肖(1-5)：所选生肖全部出现在 6 正码 + 1 特码 中（特码也算），赔率 1赔2/4/10/30/90（带马略低）。
     - 尾数连尾(0尾/1尾9尾/2-5连尾)：所选尾数全部出现在 6 正码 + 1 特码 中，赔率 1赔2/1.8/2.5/6/12/34。
     - 自选不中(5-10)：所选号码全部不出现在 6 正码 + 1 特码 中，赔率 1赔1.9/2.3/2.6/3.4/4.1/5。

   幂等：每次运行都基于 archive 重新计算 live_hits（draws 稳定，结果可复现）。
"""
import json, os
from datetime import datetime
import predict_next as pn

HERE = os.path.dirname(os.path.abspath(__file__))

ZODIAC_ORDER = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]


def zod_of(n):
    return ZODIAC_ORDER[(7 - n) % 12]


def tail_of(n):
    return n % 10


def hit_zodiac(zodiacs, mains, special):
    """生肖连肖：所选生肖全部出现在 7 位置（6 正码 + 1 特码）中。"""
    all_zods = set(zod_of(m) for m in mains) | {zod_of(special)}
    return all(z in all_zods for z in zodiacs)


def hit_tail(tails, mains, special):
    """尾数连尾：所选尾数全部出现在 7 位置中。"""
    all_tails = set(tail_of(m) for m in mains) | {tail_of(special)}
    return all(t in all_tails for t in tails)


def hit_not_hit(numbers, mains, special):
    """自选不中：所选号码全部不出现。"""
    all7 = set(mains) | {special}
    return not any(n in all7 for n in numbers)


def hit_3of2(group, mains):
    """3中2：3 选 2 至少命中 2 个。"""
    return sum(1 for n in group if n in set(mains)) >= 2


def summarize_live_hits(live):
    """把逐期真实命中(live_hits)汇总成跨期累计命中率。

    返回结构（均为累计口径）：
      - closed_issues: 已关单（已开奖并比对）的期数
      - 2of2 / 3of3 / 3of2: {hit_rate, hits, groups, issues_with_hit}
          组数 = 期数 × 20；hit_rate = hits / groups
      - special_hit: 特码命中率 {hit_rate, hits, issues}
      - zodiac/tail/not_hit: 各玩法 {hit_rate, hits, issues}，hit_rate = hits / closed_issues
    """
    n = len(live)
    if n == 0:
        return None

    def rate_of_group(key):
        total_groups = n * 20
        hits = 0
        issues_with = 0
        for o in live.values():
            c = bin(o.get(key, 0)).count("1")
            hits += c
            if c > 0:
                issues_with += 1
        return {
            "hit_rate": round(hits / total_groups, 4) if total_groups else 0,
            "hits": hits,
            "groups": total_groups,
            "issues_with_hit": issues_with,
        }

    def rate_of_group_arr(key):
        """2中2 的 40/60 组命中（用布尔数组存储，避开 31 位 bitmask 上限）。"""
        total_groups = 0
        hits = 0
        issues_with = 0
        for o in live.values():
            arr = o.get(key, []) or []
            c = sum(arr)
            hits += c
            total_groups += len(arr)
            if c > 0:
                issues_with += 1
        return {
            "hit_rate": round(hits / total_groups, 4) if total_groups else 0,
            "hits": hits,
            "groups": total_groups,
            "issues_with_hit": issues_with,
        }

    def rate_of_play(field, sub):
        hits = 0
        for o in live.values():
            hits += o.get(field, {}).get(sub, 0)
        return {
            "hit_rate": round(hits / n, 4) if n else 0,
            "hits": hits,
            "issues": n,
        }

    sp_hits = sum(1 for o in live.values() if o.get("special_pick") == o.get("actual_special"))
    return {
        "closed_issues": n,
        "2of2": {
            "20": rate_of_group("h2"),
            "40": rate_of_group_arr("h2_40"),
            "60": rate_of_group_arr("h2_60"),
        },
        "3of3": rate_of_group("h3"),
        "3of2": rate_of_group("h3of2"),
        "special_hit": {"hit_rate": round(sp_hits / n, 4) if n else 0,
                        "hits": sp_hits, "issues": n},
        "zodiac": {k: rate_of_play("zodiac_hits", k)
                   for k in ["1xiao", "2xiao", "3xiao", "4xiao", "5xiao"]},
        "tail": {k: rate_of_play("tail_hits", k)
                 for k in ["0wei", "1_9wei", "2wei", "3wei", "4wei", "5wei"]},
        "not_hit": {k: rate_of_play("not_hit_wins", k)
                    for k in ["5", "6", "7", "8", "9", "10"]},
    }


def summarize_ai_live_hits(ai_live):
    """大模式AI综合推算逐期命中汇总（与 summarize_live_hits 平行）。
    维度：正码命中数(0-6)、特码命中、3生肖特码命中、特码10数字命中、2中2组数、3中3组数。
    """
    n = len(ai_live)
    if n == 0:
        return None
    pct = lambda h, t: round(h / t, 4) if t else 0
    total_main = n * 6
    main_hits = sum(o["main_hit"] for o in ai_live.values())
    issues_main = sum(1 for o in ai_live.values() if o["main_hit"] > 0)
    sp_hits = sum(o["special_hit"] for o in ai_live.values())
    zod_hits = sum(o["zodiac_hit"] for o in ai_live.values())
    t10_hits = sum(o["top10_hit"] for o in ai_live.values())
    t2 = n * 20
    h2c = sum(o["h2_ai"] for o in ai_live.values())
    with2 = sum(1 for o in ai_live.values() if o["h2_ai"] > 0)
    t3 = n * 20
    h3c = sum(o["h3_ai"] for o in ai_live.values())
    with3 = sum(1 for o in ai_live.values() if o["h3_ai"] > 0)
    return {
        "closed_issues": n,
        "rebuilt": sum(1 for o in ai_live.values() if o.get("rebuilt")),
        "main": {
            "hit_rate": pct(main_hits, total_main),
            "avg_hit": round(main_hits / n, 2),
            "hits": main_hits, "total": total_main,
            "issues_with_hit": issues_main,
        },
        "special_hit": {"hit_rate": pct(sp_hits, n), "hits": sp_hits, "issues": n},
        "zodiac_hit": {"hit_rate": pct(zod_hits, n), "hits": zod_hits, "issues": n},
        "top10_hit": {"hit_rate": pct(t10_hits, n), "hits": t10_hits, "issues": n},
        "2of2": {"hit_rate": pct(h2c, t2), "hits": h2c, "groups": t2, "issues_with_hit": with2},
        "3of3": {"hit_rate": pct(h3c, t3), "hits": h3c, "groups": t3, "issues_with_hit": with3},
    }


def record_hit_rates(D):
    """把「大模型命中记录 + 回测」两类命中率，按运行时间追加到 hit_rates.json，
    形成可长期追踪的留痕记录（保留最近 200 条快照）。"""
    snap = {"saved_at": datetime.now().isoformat(timespec="seconds"), "regions": {}}
    for name in D["regions_order"]:
        R = D["regions"][name]
        snap["regions"][name] = {
            "live_hits": R.get("live_hits_summary"),
            "ai_live_hits": R.get("ai_live_hits_summary"),
            "backtest": R.get("hit_records", {}).get("summary"),
        }
    path = os.path.join(HERE, "hit_rates.json")
    try:
        hist = json.load(open(path, encoding="utf-8"))
    except Exception:
        hist = {"snapshots": []}
    hist.setdefault("snapshots", []).append(snap)
    hist["snapshots"] = hist["snapshots"][-200:]
    json.dump(hist, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"命中率留痕已写入 hit_rates.json（共 {len(hist['snapshots'])} 条快照）")


def main():
    D = json.load(open(os.path.join(HERE, "analysis.json"), encoding="utf-8"))
    arch_path = os.path.join(HERE, "recommendations_archive.json")
    try:
        arch = json.load(open(arch_path, encoding="utf-8"))
    except Exception:
        print("无推荐存档文件 recommendations_archive.json，跳过关单。")
        return

    # 历史真实命中留痕（跨机器迁移恢复用）：已关单期号的原样记录，不参与重算
    pres_path = os.path.join(HERE, "live_hits_preserved.json")
    try:
        PRES = json.load(open(pres_path, encoding="utf-8"))
    except Exception:
        PRES = {}

    for name in D["regions_order"]:
        R = D["regions"][name]
        draws = R["draws"]
        # issue -> (mains_list, special)
        draw_map = {d[1]: (d[2], d[3]) for d in draws}
        recs = arch.get(name, {})
        pres = PRES.get(name) or {}
        live = dict(pres.get("live_hits") or {})
        ai_live = dict(pres.get("ai_live_hits") or {})
        for issue, rec in recs.items():
            if issue not in draw_map:
                continue  # 该期尚未开奖，跳过
            if issue in live:
                continue  # 历史真实存档已留痕，保持原样不重算
            mains, special = draw_map[issue]
            mains_set = set(mains)

            # 2中2 / 3中3 / 3中2
            h2 = 0
            for j, g in enumerate(rec.get("pairs_2of2", []) or []):
                if g[0] in mains_set and g[1] in mains_set:
                    h2 |= (1 << j)
            h3 = 0
            for j, g in enumerate(rec.get("triples_3of3", []) or []):
                if g[0] in mains_set and g[1] in mains_set and g[2] in mains_set:
                    h3 |= (1 << j)
            h3of2 = 0
            for j, g in enumerate(rec.get("triples_3of2", []) or []):
                if hit_3of2(g, mains):
                    h3of2 |= (1 << j)

            # 生肖连肖（5 个玩法，命中记 1）
            zod = rec.get("zodiac_plays", {}) or {}
            zod_hits = {}
            for key, plist in [("1xiao", zod.get("1xiao")),
                               ("2xiao", zod.get("2xiao")),
                               ("3xiao", zod.get("3xiao")),
                               ("4xiao", zod.get("4xiao")),
                               ("5xiao", zod.get("5xiao"))]:
                zod_hits[key] = 1 if plist and hit_zodiac(plist, mains, special) else 0

            # 尾数连尾（6 个玩法）
            tail = rec.get("tail_plays", {}) or {}
            tail_hits = {}
            for key, tlist in [("0wei", tail.get("0wei")),
                               ("1_9wei", tail.get("1_9wei")),
                               ("2wei", tail.get("2wei")),
                               ("3wei", tail.get("3wei")),
                               ("4wei", tail.get("4wei")),
                               ("5wei", tail.get("5wei"))]:
                tail_hits[key] = 1 if tlist and hit_tail(tlist, mains, special) else 0

            # 自选不中（6 个玩法）
            nh = rec.get("not_hit", {}) or {}
            nh_hits = {}
            for k in ["5", "6", "7", "8", "9", "10"]:
                nlist = nh.get(k)
                nh_hits[k] = 1 if nlist and hit_not_hit(nlist, mains, special) else 0

            live[issue] = {
                "main_pick": rec.get("main_pick"),
                "special_pick": rec.get("special_pick"),
                "actual_mains": mains,
                "actual_special": special,
                "pairs_2of2": rec.get("pairs_2of2"),
                "pairs_2of2_40": rec.get("pairs_2of2_40"),
                "pairs_2of2_60": rec.get("pairs_2of2_60"),
                "triples_3of3": rec.get("triples_3of3"),
                "triples_3of2": rec.get("triples_3of2"),
                "h2": h2,
                "h2_40": [1 if (g[0] in mains_set and g[1] in mains_set) else 0
                          for g in (rec.get("pairs_2of2_40") or [])],
                "h2_60": [1 if (g[0] in mains_set and g[1] in mains_set) else 0
                          for g in (rec.get("pairs_2of2_60") or [])],
                "h3": h3,
                "h3of2": h3of2,
                "zodiac_hits": zod_hits,
                "tail_hits": tail_hits,
                "not_hit_wins": nh_hits,
            }

            # 大模式AI综合推算的真实命中（规则已对照历史记录核验）
            ai = rec.get("ai_prediction") or {}
            if ai.get("main_pick") or ai.get("top10"):
                ai_ms = set(mains)
                ai_live[issue] = {
                    "main_pick": ai.get("main_pick"),
                    "special_pick": ai.get("special_pick"),
                    "top3_zodiac": ai.get("top3_zodiac"),
                    "top10": ai.get("top10"),
                    "pairs_2of2": ai.get("pairs_2of2"),
                    "triples_3of3": ai.get("triples_3of3"),
                    "actual_mains": mains,
                    "actual_special": special,
                    "main_hit": sum(1 for n in (ai.get("main_pick") or []) if n in ai_ms),
                    "special_hit": 1 if ai.get("special_pick") == special else 0,
                    "zodiac_hit": 1 if zod_of(special) in (ai.get("top3_zodiac") or []) else 0,
                    "top10_hit": 1 if special in (ai.get("top10") or []) else 0,
                    "h2_ai": sum(1 for g in (ai.get("pairs_2of2") or [])
                                 if g[0] in ai_ms and g[1] in ai_ms),
                    "h3_ai": sum(1 for g in (ai.get("triples_3of3") or [])
                                 if all(x in ai_ms for x in g)),
                    "rebuilt": 0,
                }
        D["regions"][name]["live_hits"] = live
        D["regions"][name]["live_hits_summary"] = summarize_live_hits(live)
        print(f"{name}: 真实存档关单 {len(live)} 期")
        D["regions"][name]["ai_live_hits"] = ai_live
        D["regions"][name]["ai_live_hits_summary"] = summarize_ai_live_hits(ai_live)
        print(f"{name}: 大模式AI命中 {len(ai_live)} 期")
        # 新关单结果并入留痕文件，保证 engine 重算 analysis.json 后历史不丢
        PRES[name] = {"live_hits": live, "ai_live_hits": ai_live}

    try:
        json.dump(PRES, open(pres_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception as e:
        print("⚠️ 写入 live_hits_preserved.json 失败:", e)

    json.dump(D, open(os.path.join(HERE, "analysis.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("live_hits 已写入 analysis.json")
    record_hit_rates(D)


if __name__ == "__main__":
    main()
