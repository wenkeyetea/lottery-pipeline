# -*- coding: utf-8 -*-
"""历史回测：对每一期，用该期【之前】的开奖数据重建推算（与 predict_next.py 同源评分模型），
   生成 20 组 2中2 / 20 组 3中3，再与该期实际开奖(6 正码)比对，记录命中/未命中。
   结果写回 analysis.json 的 regions[name]['hit_records']。

   命中定义（六合彩平码玩法，只统计 6 个正码/平码，特码第7球不参与）：
     - 2中2 命中：该组 2 个号码都出现在当期的 6 个正码中。
     - 3中3 命中：该组 3 个号码都出现在当期的 6 个正码中。

   说明：
     - 用「该期之前」的数据重建，才是诚实的回测；窗口 WIN=50。
     - 组生成使用与 predict_next.py 完全一致的确定性随机种子（seed = issue*2+1 / issue*3+7），
       因此回测的 2中2/3中3 组，就是当时若运行推算会得到的组。
     - 回测从「已有 ≥WIN 期历史」的那一期开始（前 WIN 期数据不足，不计入）。
"""
import json, random, os

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "analysis.json"), encoding="utf-8"))
WIN = 50
wHot, wSta, wDue = 0.40, 0.35, 0.25


def norm(d):
    vs = list(d.values())
    lo, hi = min(vs), max(vs)
    return {k: 50 if hi == lo else 100 * (v - lo) / (hi - lo) for k, v in d.items()}


def nrm(obj):
    vs = list(obj.values())
    lo, hi = min(vs), max(vs)
    return {k: 50 if hi == lo else 100 * (v - lo) / (hi - lo) for k, v in obj.items()}


def weighted_pick(pool, k, score):
    pool = list(pool)
    res = []
    while len(res) < k and pool:
        ws = [max(score[x], 1e-6) for x in pool]
        s = sum(ws)
        r = random.random() * s
        i = 0
        for i, x in enumerate(pool):
            r -= ws[i]
            if r <= 0:
                break
        res.append(pool.pop(min(i, len(pool) - 1)))
    return res


def backtest_region(name):
    R = D["regions"][name]
    draws = R["draws"]
    N = len(draws)
    issues_out = []
    for i in range(WIN, N):
        prefix = draws[:i]
        freq_total = {}
        last_idx = {}
        recent = {}
        for j, d in enumerate(prefix):
            for m in d[2]:
                freq_total[m] = freq_total.get(m, 0) + 1
                last_idx[m] = j
                recent[m] = recent.get(m, 0) + 1
            sp = d[3]
            freq_total[sp] = freq_total.get(sp, 0) + 1
            last_idx[sp] = j
            recent[sp] = recent.get(sp, 0) + 1
        L = len(prefix)
        last_seen = {}
        for n in range(1, 50):
            last_seen[n] = (L - 1 - last_idx[n]) if n in last_idx else L
        hotN = norm({n: recent.get(n, 0) for n in range(1, 50)})
        staN = norm({n: freq_total.get(n, 0) for n in range(1, 50)})
        dueN = norm({n: last_seen[n] for n in range(1, 50)})
        rawMain = {n: wHot * hotN[n] + wSta * staN[n] + wDue * dueN[n] for n in range(1, 50)}
        mainS = nrm(rawMain)
        mainRank = sorted(mainS, key=lambda k: -mainS[k])

        issue = draws[i][1]
        mains_set = set(draws[i][2])

        # 与 predict_next.py 同源的确定性种子
        random.seed(int(issue) * 2 + 1)
        pairs = [sorted(weighted_pick(mainRank, 2, mainS)) for _ in range(20)]
        random.seed(int(issue) * 3 + 7)
        triples = [sorted(weighted_pick(mainRank, 3, mainS)) for _ in range(20)]

        h2 = 0
        for j, g in enumerate(pairs):
            if g[0] in mains_set and g[1] in mains_set:
                h2 |= (1 << j)
        h3 = 0
        for j, g in enumerate(triples):
            if g[0] in mains_set and g[1] in mains_set and g[2] in mains_set:
                h3 |= (1 << j)

        issues_out.append({
            "issue": issue,
            "y2": pairs, "h2": h2,
            "y3": triples, "h3": h3,
        })

    # 体积控制：完整「命中/未命中台账」保留所有期（仅 bitmask，很小）；
    # 具体组号（y2/y3）保留全部期（与线上部署版一致，供台账完整展开查看）。
    N_DETAIL = 10 ** 9
    for idx, it in enumerate(issues_out):
        if idx < len(issues_out) - N_DETAIL:
            it.pop("y2", None)
            it.pop("y3", None)

    def summarize(key_hit):
        total_groups = len(issues_out) * 20
        total_hits = 0
        issues_with = 0
        best = 0
        best_issue = None
        for it in issues_out:
            cnt = bin(it[key_hit]).count("1")
            total_hits += cnt
            if cnt > 0:
                issues_with += 1
            if cnt > best:
                best = cnt
                best_issue = it["issue"]
        return {
            "issues": len(issues_out),
            "total_groups": total_groups,
            "total_hits": total_hits,
            "hit_rate": round(total_hits / total_groups, 4) if total_groups else 0,
            "issues_with_hit": issues_with,
            "best_hits": best,
            "best_issue": best_issue,
        }

    hr = {
        "win": WIN,
        "detail_issues": N_DETAIL,
        "summary": {
            "2of2": summarize("h2"),
            "3of3": summarize("h3"),
        },
        "issues": issues_out,
    }
    D["regions"][name]["hit_records"] = hr
    return hr


if __name__ == "__main__":
    for name in D["regions_order"]:
        hr = backtest_region(name)
        s2 = hr["summary"]["2of2"]
        s3 = hr["summary"]["3of3"]
        print(f"{name}: 回测 {s2['issues']} 期 | "
              f"2中2 命中率 {s2['hit_rate']*100:.2f}% ({s2['total_hits']}/{s2['total_groups']}) "
              f"有命中 {s2['issues_with_hit']}/{s2['issues']} 期 | "
              f"3中3 命中率 {s3['hit_rate']*100:.2f}% ({s3['total_hits']}/{s3['total_groups']}) "
              f"有命中 {s3['issues_with_hit']}/{s3['issues']} 期")
    with open(os.path.join(HERE, "analysis.json"), "w", encoding="utf-8") as f:
        json.dump(D, f, ensure_ascii=False, indent=1)
    print("hit_records 已写入 analysis.json")
