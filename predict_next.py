# -*- coding: utf-8 -*-
"""用与仪表盘完全一致的评分模型，推算各地区下一期的【参考组合】，并写回 analysis.json。
   重要：开奖为独立随机事件，本脚本只做统计参考，不具备任何预测效力。

   产出：
   - analysis.json 每个地区新增 regions[name]["prediction"]：
       next_issue / main_pick(正码推荐6个) / special_pick(特码推荐1个)
       pairs_2of2(2中2 20组) / triples_3of3(3中3 20组) / triples_3of2(3中2 20组)
       zodiac_plays(生肖 1-5 连肖) / tail_plays(尾数 0尾/1尾9尾/2-5连尾)
       not_hit(自选不中 5-10 不中)
       main_pool(正码候选池Top15) / special_pool(特码候选池Top10)
   - recommendation.md（人类可读版，含所有玩法 + 赔率说明）
   - recommendations_archive.json（按 next_issue 存档完整数据，幂等覆盖）
"""
import json, random, os, datetime
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "analysis.json"), encoding="utf-8"))
REGIONS = D["regions"]
ORDER = D["regions_order"]
try:
    PATTERNS = json.load(open(os.path.join(HERE, "patterns.json"), encoding="utf-8"))
except Exception:
    PATTERNS = {}
WIN = 50
wHot, wSta, wDue = 0.40, 0.35, 0.25

ZODIAC_ORDER = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]

WAVE_COLORS = ["红波", "蓝波", "绿波"]
WAVE = {}
for _n in [1, 2, 7, 8, 12, 13, 18, 19, 23, 24, 29, 30, 34, 35, 40, 45, 46]:
    WAVE[_n] = "红波"
for _n in [3, 4, 9, 10, 14, 15, 20, 25, 26, 31, 36, 37, 41, 42, 47, 48]:
    WAVE[_n] = "蓝波"
for _n in [5, 6, 11, 16, 17, 21, 22, 27, 28, 32, 33, 38, 39, 43, 44, 49]:
    WAVE[_n] = "绿波"
ELEMENTS = ["金", "木", "水", "火", "土"]


def zod_of(n):
    """号码 n (1-49) 对应生肖（按当前年份口径，与数据一致）。"""
    return ZODIAC_ORDER[(7 - n) % 12]


def tail_of(n):
    return n % 10


def head_of(n):
    """头数：十位（0-4）。1-9→0，10-19→1，20-29→2，30-39→3，40-49→4。"""
    return n // 10


def rng_key(n):
    if n <= 10: return "01-10"
    if n <= 20: return "11-20"
    if n <= 30: return "21-30"
    if n <= 40: return "31-40"
    return "41-49"



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


def gen_unique_groups(rank, score, k, count, seed_base):
    """生成 count 组不重复的 k 元组合（同组内无重复号 + 组间无完全相同组合）。"""
    random.seed(seed_base)
    seen = set()
    groups = []
    max_attempts = count * 20  # 防死循环
    attempts = 0
    while len(groups) < count and attempts < max_attempts:
        attempts += 1
        g = tuple(sorted(weighted_pick(rank, k, score)))
        if g not in seen and len(set(g)) == k:  # 组内无重复 + 组间不重复
            seen.add(g)
            groups.append(list(g))
    # 如果去重后不足 count 组，用剩余候选补齐（极低概率）
    while len(groups) < count:
        filler = tuple(sorted(random.sample(range(1, 50), k)))
        if filler not in seen:
            seen.add(filler)
            groups.append(list(filler))
    return groups


def ai_predict(R, P, next_issue):
    """🧠 大模式AI综合推算：基于最新规律(patterns) + 实时统计(numbers/draws)，
       对下一期做多维度加权综合推算（与既有的"热度/稳定/遗漏"模型不同视角——
       本次额外引入波色/五行/生肖/区间均衡、均值回归与冷号补偿）。
       重要：开奖独立随机，本函数只做统计参考，不具备任何预测效力。"""
    nums = R["numbers"]
    INF = {n["num"]: n for n in nums}
    nums_list = list(range(1, 50))

    # ---- 维度1：长期热度（numbers.freq_total）----
    freq = {n["num"]: n["freq_total"] for n in nums}
    s_freq = nrm({x: freq[x] for x in nums_list})

    # ---- 维度2：当前遗漏（均值回归，越久未出越"该出"）----
    omit = {n["num"]: n["last_seen"] for n in nums}
    s_omit = nrm({x: omit[x] for x in nums_list})

    # ---- 维度3：波色均衡（低于 1/3 的波色提权）----
    wave_share = P.get("wave_share", {}) or {}
    wave_due = {c: max(0.0, 33.333 - wave_share.get(c, 33.333)) for c in WAVE_COLORS}
    s_wave = nrm({x: wave_due[WAVE[x]] for x in nums_list})

    # ---- 维度4：五行均衡 ----
    elem_share = P.get("elem_share", {}) or {}
    exp_elem = 100.0 / len(ELEMENTS)
    elem_due = {e: max(0.0, exp_elem - elem_share.get(e, exp_elem)) for e in ELEMENTS}
    s_elem = nrm({x: elem_due[INF[x]["element"]] for x in nums_list})

    # ---- 维度5：生肖均衡 ----
    zod_share = P.get("zod_share", {}) or {}
    exp_zod = 100.0 / 12
    zod_due = {z: max(0.0, exp_zod - zod_share.get(z, exp_zod)) for z in ZODIAC_ORDER}
    s_zod = nrm({x: zod_due[INF[x]["zodiac"]] for x in nums_list})

    # ---- 维度6：区间(头数/01-10...)均衡 ----
    rng_c = P.get("rng_c", {}) or {}
    tot_rng = sum(rng_c.values()) if rng_c else 1
    rng_due = {k: max(0.0, 20.0 - (rng_c.get(k, 0) / tot_rng * 100)) for k in
               ["01-10", "11-20", "21-30", "31-40", "41-49"]}
    s_rng = nrm({x: rng_due[rng_key(x)] for x in nums_list})

    # ---- 综合分（正码）----
    w = dict(freq=0.26, omit=0.28, wave=0.12, elem=0.10, zod=0.12, rng=0.12)
    comp = {x: w["freq"] * s_freq[x] + w["omit"] * s_omit[x] + w["wave"] * s_wave[x] +
                w["elem"] * s_elem[x] + w["zod"] * s_zod[x] + w["rng"] * s_rng[x] for x in nums_list}
    comp = nrm(comp)

    # ---- 特码综合分（综合分 + 特码频次）----
    sp_freq = {n["num"]: n["freq_special"] for n in nums}
    s_sp = nrm({x: sp_freq[x] for x in nums_list})
    comp_sp = nrm({x: 0.55 * comp[x] + 0.45 * s_sp[x] for x in nums_list})

    # ---- 正码6（带多样性约束：同波色≤3、同生肖≤2）----
    rank = sorted(nums_list, key=lambda k: -comp[k])
    main, waves_seen, zods_seen = [], {}, {}
    for x in rank:
        if len(main) >= 6:
            break
        wc, zc = WAVE[x], INF[x]["zodiac"]
        if waves_seen.get(wc, 0) >= 3 or zods_seen.get(zc, 0) >= 2:
            continue
        main.append(x)
        waves_seen[wc] = waves_seen.get(wc, 0) + 1
        zods_seen[zc] = zods_seen.get(zc, 0) + 1
    for x in rank:  # 极端情况放宽补满
        if len(main) >= 6:
            break
        if x not in main:
            main.append(x)

    main_set = set(main)
    sp_rank = sorted(nums_list, key=lambda k: -comp_sp[k])
    special = next((x for x in sp_rank if x not in main_set), sp_rank[0])

    top10 = rank[:10]

    # ---- 3 生肖（按生肖内综合分均值排序）----
    zod_comp = {}
    for z in ZODIAC_ORDER:
        mem = [x for x in nums_list if INF[x]["zodiac"] == z]
        zod_comp[z] = sum(comp[x] for x in mem) / len(mem)
    zod_rank = sorted(ZODIAC_ORDER, key=lambda z: -zod_comp[z])
    top3_zod = zod_rank[:3]

    # ---- 五行（按元素内综合分均值 + 欠配）----
    elem_comp = {}
    for e in ELEMENTS:
        mem = [x for x in nums_list if INF[x]["element"] == e]
        elem_comp[e] = sum(comp[x] for x in mem) / len(mem)
    elem_rank = sorted(ELEMENTS, key=lambda e: -elem_comp[e])

    # ---- 波色（按波色内综合分均值 + 欠配）----
    wave_comp = {c: sum(comp[x] for x in nums_list if WAVE[x] == c) / 16 for c in WAVE_COLORS}
    wave_rank = sorted(WAVE_COLORS, key=lambda c: -wave_comp[c])

    # ---- 单双（基于历史奇偶占比，推荐偏低一方=均值回归）----
    par_share = P.get("par_share", {}) or {}
    odd_s = par_share.get("odd", 50)
    even_s = par_share.get("even", 50)
    parity_rec = "单" if odd_s < even_s else ("双" if even_s < odd_s else "单双均衡")

    # ---- 尾数（综合分 + 尾数欠配）----
    tail_count = {t: sum(freq[x] for x in nums_list if tail_of(x) == t) for t in range(10)}
    tot_t = sum(tail_count.values()) or 1
    tail_due = {t: max(0.0, 10.0 - tail_count[t] / tot_t * 100) for t in range(10)}
    s_td = nrm(tail_due)
    tail_comp = {t: sum(comp[x] for x in nums_list if tail_of(x) == t) / (tail_count[t] or 1) for t in range(10)}
    tail_score = nrm({t: 0.5 * tail_comp[t] + 0.5 * s_td[t] for t in range(10)})
    tail_rank = sorted(range(10), key=lambda t: -tail_score[t])
    top_tails = tail_rank[:3]

    # ---- 头数（综合分 + 头数欠配）----
    head_count = {h: sum(freq[x] for x in nums_list if head_of(x) == h) for h in range(5)}
    tot_h = sum(head_count.values()) or 1
    head_due = {h: max(0.0, 20.0 - head_count[h] / tot_h * 100) for h in range(5)}
    s_hd = nrm(head_due)
    head_comp = {h: sum(comp[x] for x in nums_list if head_of(x) == h) / (head_count[h] or 1) for h in range(5)}
    head_score = nrm({h: 0.5 * head_comp[h] + 0.5 * s_hd[h] for h in range(5)})
    head_rank = sorted(range(5), key=lambda h: -head_score[h])
    top_heads = head_rank[:2]

    # ---- 正码2中2 / 三中3（AI版，去重）----
    pairs_ai = gen_unique_groups(rank, comp, 2, 20, int(next_issue) * 97 + 31)
    triples_ai = gen_unique_groups(rank, comp, 3, 20, int(next_issue) * 98 + 37)

    zm = lambda n: f'{n}({INF[n]["zodiac"]}/{INF[n]["element"]})'

    # ---- 下一期正码生肖推荐（正码平肖遗漏回补）----
    # 直接基于每期正码 draws 计算生肖级遗漏（最近一次在正码开出的期数），
    # 不依赖 numbers.last_seen，避免引擎侧 last_seen 口径偏差导致脏数据。
    _draws = R.get("draws") or []
    _lastz = {z: -1 for z in ZODIAC_ORDER}
    for _i, _d in enumerate(_draws):
        for _m in _d[2]:
            _lastz[INF[_m]["zodiac"]] = _i
    _N = len(_draws)
    zod_omiss = {z: (_N - 1 - _lastz[z]) for z in ZODIAC_ORDER}
    main_zodiac_rec = max(ZODIAC_ORDER, key=lambda z: zod_omiss[z])
    main_zodiac_members = [x for x in nums_list if INF[x]["zodiac"] == main_zodiac_rec]

    return {
        "next_issue": next_issue,
        "main_pick": main,
        "special_pick": special,
        "special_zodiac": INF[special]["zodiac"],
        "special_element": INF[special]["element"],
        "top10": top10,
        "top10_info": [{"num": x, "zodiac": INF[x]["zodiac"], "element": INF[x]["element"]} for x in top10],
        "top3_zodiac": top3_zod,
        "top3_zodiac_members": {z: [x for x in nums_list if INF[x]["zodiac"] == z] for z in top3_zod},
        "element_rank": [{"element": e, "score": round(elem_comp[e], 1),
                          "share": round(elem_share.get(e, 0), 2), "due": round(elem_due[e], 2)} for e in elem_rank],
        "wave_rank": [{"wave": c, "score": round(wave_comp[c], 1),
                       "share": round(wave_share.get(c, 0), 2), "due": round(wave_due[c], 2)} for c in wave_rank],
        "parity": {"recommend": parity_rec, "odd_share": round(odd_s, 2), "even_share": round(even_s, 2)},
        "top_tails": top_tails,
        "tail_rank": [{"tail": t, "score": round(tail_score[t], 1)} for t in tail_rank],
        "top_heads": top_heads,
        "head_rank": [{"head": h, "score": round(head_score[h], 1)} for h in head_rank],
        "comp_main": {x: round(comp[x], 1) for x in nums_list},
        "comp_special": {x: round(comp_sp[x], 1) for x in nums_list},
        "pairs_2of2": pairs_ai,
        "triples_3of3": triples_ai,
        "main_zodiac": {"zodiac": main_zodiac_rec, "numbers": main_zodiac_members,
                        "omission": zod_omiss[main_zodiac_rec]},
        "weights": w,
    }


def gen_region(name):
    R = REGIONS[name]
    draws = R["draws"]
    nums = R["numbers"]
    last_issue = R["meta"]["last_issue"]
    next_issue = str(int(last_issue) + 1)

    recent, recentSp = {}, {}
    for d in draws[-WIN:]:
        for m in d[2]:
            recent[m] = recent.get(m, 0) + 1
        recent[d[3]] = recent.get(d[3], 0) + 1
        recentSp[d[3]] = recentSp.get(d[3], 0) + 1

    hotN = norm({n["num"]: recent.get(n["num"], 0) for n in nums})
    staN = norm({n["num"]: n["freq_total"] for n in nums})
    dueN = norm({n["num"]: n["last_seen"] for n in nums})
    spHot = norm({n["num"]: recentSp.get(n["num"], 0) for n in nums})
    spSta = norm({n["num"]: n["freq_special"] for n in nums})
    spDue = norm({n["num"]: n["last_special_seen"] for n in nums})

    rawMain = {n["num"]: wHot * hotN[n["num"]] + wSta * staN[n["num"]] + wDue * dueN[n["num"]] for n in nums}
    rawSp = {n["num"]: wHot * spHot[n["num"]] + wSta * spSta[n["num"]] + wDue * spDue[n["num"]] for n in nums}
    mainS = nrm(rawMain)
    spS = nrm(rawSp)

    INF = {n["num"]: n for n in nums}
    mainRank = sorted(mainS, key=lambda k: -mainS[k])
    spRank = sorted(spS, key=lambda k: -spS[k])
    main_pick = mainRank[:6]
    main_set = set(main_pick)
    sp_pick = next((n for n in spRank if n not in main_set), spRank[0])

    def score_with(w_h, w_s, w_d):
        raw = {n["num"]: w_h * hotN[n["num"]] + w_s * staN[n["num"]] + w_d * dueN[n["num"]] for n in nums}
        rm = nrm(raw)
        return sorted(rm, key=lambda k: -rm[k])

    hot_rank = score_with(0.70, 0.20, 0.10)
    due_rank = score_with(0.10, 0.20, 0.70)
    zm = lambda n: f'{n}({INF[n]["zodiac"]}/{INF[n]["element"]})'

    # ---- 2中2 三档（每组2个正码，2个全中，赔60倍）----
    pairs_2of2 = gen_unique_groups(mainRank, mainS, 2, 20, int(next_issue) * 2 + 1)
    pairs_2of2_40 = gen_unique_groups(mainRank, mainS, 2, 40, int(next_issue) * 21 + 1)
    pairs_2of2_60 = gen_unique_groups(mainRank, mainS, 2, 60, int(next_issue) * 61 + 1)

    # ---- 3中3 20组（每组3个正码，3个全中，赔600倍）----
    triples_3of3 = gen_unique_groups(mainRank, mainS, 3, 20, int(next_issue) * 3 + 7)

    # ---- 3中2 20组（每组3个正码，至少2个在6正码，赔19倍）----
    triples_3of2 = gen_unique_groups(mainRank, mainS, 3, 20, int(next_issue) * 4 + 3)

    # ---- 生肖（十二肖）评分与连肖组合 ----
    zod_recent = Counter()
    zod_stable = Counter()
    for d in draws[-WIN:]:
        for m in d[2]:
            zod_recent[zod_of(m)] += 1
        zod_recent[zod_of(d[3])] += 1
    for d in draws:
        for m in d[2]:
            zod_stable[zod_of(m)] += 1
        zod_stable[zod_of(d[3])] += 1
    zod_omission = {z: 0 for z in ZODIAC_ORDER}
    for z in ZODIAC_ORDER:
        cur = 0
        for d in reversed(draws):
            all_zods = set(zod_of(m) for m in d[2]) | {zod_of(d[3])}
            if z in all_zods:
                break
            cur += 1
        zod_omission[z] = cur
    zod_hot_n = norm({z: zod_recent[z] for z in ZODIAC_ORDER})
    zod_sta_n = norm({z: zod_stable[z] for z in ZODIAC_ORDER})
    zod_due_n = norm({z: zod_omission[z] for z in ZODIAC_ORDER})
    zod_score = {z: wHot * zod_hot_n[z] + wSta * zod_sta_n[z] + wDue * zod_due_n[z] for z in ZODIAC_ORDER}
    zod_rank = sorted(ZODIAC_ORDER, key=lambda z: -zod_score[z])
    zod_top_score = {z: round(zod_score[z], 1) for z in ZODIAC_ORDER}

    random.seed(int(next_issue) * 5 + 11)
    zodiac_1xiao = [zod_rank[0]]
    zodiac_2xiao = sorted(weighted_pick(zod_rank, 2, zod_score), key=lambda z: ZODIAC_ORDER.index(z))
    zodiac_3xiao = sorted(weighted_pick(zod_rank, 3, zod_score), key=lambda z: ZODIAC_ORDER.index(z))
    zodiac_4xiao = sorted(weighted_pick(zod_rank, 4, zod_score), key=lambda z: ZODIAC_ORDER.index(z))
    zodiac_5xiao = sorted(weighted_pick(zod_rank, 5, zod_score), key=lambda z: ZODIAC_ORDER.index(z))
    zodiac_plays = {
        "1xiao": zodiac_1xiao, "2xiao": zodiac_2xiao, "3xiao": zodiac_3xiao,
        "4xiao": zodiac_4xiao, "5xiao": zodiac_5xiao,
        "scores": zod_top_score, "omission": zod_omission,
    }

    # ---- 尾数（0-9）评分与连尾组合 ----
    tail_recent = Counter()
    tail_stable = Counter()
    for d in draws[-WIN:]:
        for m in d[2]:
            tail_recent[tail_of(m)] += 1
        tail_recent[tail_of(d[3])] += 1
    for d in draws:
        for m in d[2]:
            tail_stable[tail_of(m)] += 1
        tail_stable[tail_of(d[3])] += 1
    tail_omission = {t: 0 for t in range(10)}
    for t in range(10):
        cur = 0
        for d in reversed(draws):
            all_tails = set(tail_of(m) for m in d[2]) | {tail_of(d[3])}
            if t in all_tails:
                break
            cur += 1
        tail_omission[t] = cur
    tail_hot_n = norm({t: tail_recent[t] for t in range(10)})
    tail_sta_n = norm({t: tail_stable[t] for t in range(10)})
    tail_due_n = norm({t: tail_omission[t] for t in range(10)})
    tail_score = {t: wHot * tail_hot_n[t] + wSta * tail_sta_n[t] + wDue * tail_due_n[t] for t in range(10)}
    tail_rank = sorted(range(10), key=lambda t: -tail_score[t])

    random.seed(int(next_issue) * 6 + 13)
    tail_0wei = [0]                          # 0尾（固定 0 尾号）
    tail_1_9wei = [1, 9]                     # 1尾 + 9尾（固定组合）
    tail_2wei = sorted(weighted_pick(tail_rank, 2, tail_score))
    tail_3wei = sorted(weighted_pick(tail_rank, 3, tail_score))
    tail_4wei = sorted(weighted_pick(tail_rank, 4, tail_score))
    tail_5wei = sorted(weighted_pick(tail_rank, 5, tail_score))
    tail_plays = {
        "0wei": tail_0wei, "1_9wei": tail_1_9wei,
        "2wei": tail_2wei, "3wei": tail_3wei, "4wei": tail_4wei, "5wei": tail_5wei,
        "scores": {str(t): round(tail_score[t], 1) for t in range(10)},
        "omission": {str(t): tail_omission[t] for t in range(10)},
    }

    # ---- 自选不中（Not Hit）反选评分最低号码 ----
    # 取 mainS 反向（数值越大越"不中"），用与主推荐同源加权抽样
    reverse_score = {n: max(1e-6, 101.0 - mainS[n]) for n in range(1, 50)}
    reverse_rank = sorted(range(1, 50), key=lambda n: -reverse_score[n])  # "最不中"→前
    random.seed(int(next_issue) * 7 + 17)
    not_hit_5 = sorted(weighted_pick(reverse_rank, 5, reverse_score))
    not_hit_6 = sorted(weighted_pick(reverse_rank, 6, reverse_score))
    not_hit_7 = sorted(weighted_pick(reverse_rank, 7, reverse_score))
    not_hit_8 = sorted(weighted_pick(reverse_rank, 8, reverse_score))
    not_hit_9 = sorted(weighted_pick(reverse_rank, 9, reverse_score))
    not_hit_10 = sorted(weighted_pick(reverse_rank, 10, reverse_score))
    not_hit = {
        "5": not_hit_5, "6": not_hit_6, "7": not_hit_7,
        "8": not_hit_8, "9": not_hit_9, "10": not_hit_10,
    }

    # ---- 候选池 ----
    main_pool = [{
        "num": n, "score": round(mainS[n], 1),
        "freq": INF[n]["freq_total"], "recent": recent.get(n, 0),
        "last_seen": INF[n]["last_seen"]
    } for n in mainRank[:15]]
    special_pool = [{
        "num": n, "score": round(spS[n], 1),
        "freq_sp": INF[n]["freq_special"], "recent_sp": recentSp.get(n, 0),
        "last_seen_sp": INF[n]["last_special_seen"]
    } for n in [x for x in spRank if x not in main_set][:10]]

    # 写回 analysis.json
    pred = {
        "next_issue": next_issue,
        "main_pick": main_pick,
        "special_pick": sp_pick,
        "pairs_2of2": pairs_2of2,
        "triples_3of3": triples_3of3,
        "triples_3of2": triples_3of2,
        "zodiac_plays": zodiac_plays,
        "tail_plays": tail_plays,
        "not_hit": not_hit,
        "main_pool": main_pool,
        "special_pool": special_pool,
        "pairs_2of2_40": pairs_2of2_40,
        "pairs_2of2_60": pairs_2of2_60,
    }

    # ---- 大模式AI综合推算（基于最新规律 patterns）----
    ai_pred = ai_predict(R, PATTERNS.get(name, {}), next_issue)
    pred["ai_prediction"] = ai_pred

    D["regions"][name]["prediction"] = pred

    # ---- 真实推荐存档：把本期「针对哪一期(next_issue)」的推荐号码持久化，
    #      供该期开奖后由 close_issues.py 如实比对命中（避免只能用模型重建台账）。
    _arch_path = os.path.join(HERE, "recommendations_archive.json")
    try:
        _arch = json.load(open(_arch_path, encoding="utf-8"))
    except Exception:
        _arch = {}
    _arch.setdefault(name, {})[next_issue] = {
        "saved_at": datetime.date.today().isoformat(),
        "main_pick": main_pick,
        "special_pick": sp_pick,
        "pairs_2of2": pairs_2of2,
        "triples_3of3": triples_3of3,
        "triples_3of2": triples_3of2,
        "zodiac_plays": zodiac_plays,
        "tail_plays": tail_plays,
        "not_hit": not_hit,
        "pairs_2of2_40": pairs_2of2_40,
        "pairs_2of2_60": pairs_2of2_60,
        "ai_prediction": ai_pred,
    }
    json.dump(_arch, open(_arch_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # ---- 人类可读 markdown ----
    out = []
    out.append(f"## {name} · 推算第 {next_issue} 期\n")
    out.append(f"- **正码推荐下一期（6个）**：`{' '.join(str(x) for x in main_pick)}`  →  {', '.join(zm(x) for x in main_pick)}")
    out.append(f"- **特码推荐（1个，特码类 1赔47）**：`{sp_pick}`  →  {zm(sp_pick)}")
    out.append("")
    out.append(f"### {name} · 正码候选池 Top15（综合分 = 热度40% + 稳定35% + 遗漏25%）\n")
    out.append("| 排名 | 号码 | 生肖/五行 | 综合分 | 历史总频 | 近50期 | 遗漏 |")
    out.append("|---|---|---|---|---|---|---|")
    for i, n in enumerate(main_pool, 1):
        inf = INF[n["num"]]
        out.append(f"| {i} | **{n['num']}** | {inf['zodiac']}/{inf['element']} | {n['score']:.1f} | {n['freq']} | {n['recent']} | {n['last_seen']} |")
    out.append("")
    out.append(f"### {name} · 特码候选池 Top10\n")
    out.append("| 排名 | 号码 | 生肖/五行 | 综合分 | 特码频 | 近50期特码 | 特码遗漏 |")
    out.append("|---|---|---|---|---|---|---|")
    for i, n in enumerate(special_pool, 1):
        inf = INF[n["num"]]
        out.append(f"| {i} | **{n['num']}** | {inf['zodiac']}/{inf['element']} | {n['score']:.1f} | {n['freq_sp']} | {n['recent_sp']} | {n['last_seen_sp']} |")
    out.append("")

    # 平码类（特码不算）
    out.append(f"### {name} · 平码类（特码不算）\n")
    out.append(f"- **平码（任选1个正码，1赔6.5）**：候选 Top6  `{ ' '.join(str(x) for x in mainRank[:6]) }`")
    out.append("")
    out.append(f"### {name} · 2中2 · 20组（每组2个正码，2个全中 赔60倍）\n")
    for s in range(20):
        a, b = pairs_2of2[s]
        out.append(f"- 组{s+1:02d}：`{a} {b}`  →  {zm(a)} · {zm(b)}")
    out.append("")
    out.append(f"### {name} · 2中2 · 40组（每组2个正码，2个全中 赔60倍）\n")
    for s in range(40):
        a, b = pairs_2of2_40[s]
        out.append(f"- 组{s+1:02d}：`{a} {b}`  →  {zm(a)} · {zm(b)}")
    out.append("")
    out.append(f"### {name} · 2中2 · 60组（每组2个正码，2个全中 赔60倍）\n")
    for s in range(60):
        a, b = pairs_2of2_60[s]
        out.append(f"- 组{s+1:02d}：`{a} {b}`  →  {zm(a)} · {zm(b)}")
    out.append("")
    out.append(f"### {name} · 3中3 · 20组（每组3个正码，3个全中 赔600倍）\n")
    for s in range(20):
        t = triples_3of3[s]
        out.append(f"- 组{s+1:02d}：`{' '.join(str(x) for x in t)}`  →  {' · '.join(zm(x) for x in t)}")
    out.append("")
    out.append(f"### {name} · 3中2 · 20组（每组3个正码，至少2个在6正码 赔19倍）\n")
    for s in range(20):
        t = triples_3of2[s]
        out.append(f"- 组{s+1:02d}：`{' '.join(str(x) for x in t)}`  →  {' · '.join(zm(x) for x in t)}")
    out.append("")

    # 生肖连肖
    out.append(f"### {name} · 生肖连肖（特码也算，命中即赢）\n")
    out.append("| 玩法 | 赔率 | 推荐 |")
    out.append("|---|---|---|")
    out.append(f"| 平特一肖 | 1赔2（马1赔1.8） | `{' · '.join(zodiac_1xiao)}` |")
    out.append(f"| 两连肖 | 1赔4（带马1赔3.5） | `{' · '.join(zodiac_2xiao)}` |")
    out.append(f"| 三连肖 | 1赔10（带马1赔8.5） | `{' · '.join(zodiac_3xiao)}` |")
    out.append(f"| 四连肖 | 1赔30（带马1赔25） | `{' · '.join(zodiac_4xiao)}` |")
    out.append(f"| 五连肖 | 1赔90（带马1赔80） | `{' · '.join(zodiac_5xiao)}` |")
    out.append("")
    out.append("> 生肖综合分 = 热度40% + 稳定35% + 遗漏25%（窗口50期，特码计入）。")
    out.append("")
    out.append("| 生肖 | 鼠 | 牛 | 虎 | 兔 | 龙 | 蛇 | 马 | 羊 | 猴 | 鸡 | 狗 | 猪 |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    out.append(f"| 综合分 | " + " | ".join(f"{zod_top_score[z]}" for z in ZODIAC_ORDER) + " |")
    out.append(f"| 遗漏   | " + " | ".join(f"{zod_omission[z]}" for z in ZODIAC_ORDER) + " |")
    out.append("")

    # 尾数连尾
    out.append(f"### {name} · 尾数连尾（特码也算）\n")
    out.append("| 玩法 | 赔率 | 推荐 |")
    out.append("|---|---|---|")
    out.append(f"| 0尾 | 1赔2 | `{' '.join(str(t) for t in tail_0wei)}尾` |")
    out.append(f"| 1尾/9尾 | 1赔1.8 | `{' · '.join(str(t)+'尾' for t in tail_1_9wei)}` |")
    out.append(f"| 两连尾 | 1赔2.5 | `{' · '.join(str(t)+'尾' for t in tail_2wei)}` |")
    out.append(f"| 三连尾 | 1赔6 | `{' · '.join(str(t)+'尾' for t in tail_3wei)}` |")
    out.append(f"| 四连尾 | 1赔12 | `{' · '.join(str(t)+'尾' for t in tail_4wei)}` |")
    out.append(f"| 五连尾 | 1赔34 | `{' · '.join(str(t)+'尾' for t in tail_5wei)}` |")
    out.append("")
    out.append("> 尾数综合分 = 热度40% + 稳定35% + 遗漏25%（窗口50期，特码计入）。")
    out.append("")
    out.append("| 尾数 | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|")
    out.append(f"| 综合分 | " + " | ".join(f"{tail_score[t]:.1f}" for t in range(10)) + " |")
    out.append(f"| 遗漏   | " + " | ".join(f"{tail_omission[t]}" for t in range(10)) + " |")
    out.append("")

    # 自选不中
    out.append(f"### {name} · 自选不中（特位也算，全部不中即赢）\n")
    out.append("| 玩法 | 赔率 | 推荐号码 |")
    out.append("|---|---|---|")
    for k, nums_ in [("5", not_hit_5), ("6", not_hit_6), ("7", not_hit_7),
                     ("8", not_hit_8), ("9", not_hit_9), ("10", not_hit_10)]:
        payout = {"5": "1.9", "6": "2.3", "7": "2.6", "8": "3.4", "9": "4.1", "10": "5"}[k]
        out.append(f"| {k}不中 | 1赔{payout} | `{' '.join(str(x) for x in nums_)}` |")
    out.append("")
    out.append("> 策略：取与主推荐反向的综合分（热度+稳定+遗漏最低的号码），加权抽样。")
    out.append("")

    # 大模式AI综合推算
    out.append(f"### {name} · 🧠 大模式AI综合推算（下一期 {next_issue}）\n")
    out.append("> 综合分 = 长期热度26% + 当前遗漏28% + 波色均衡12% + 五行均衡10% + 生肖均衡12% + 区间均衡12%。"
               "在最新规律(patterns)基础上引入波色/五行/生肖/区间的均值回归与冷号补偿，是与上方「热度/稳定/遗漏」模型互补的另一直观视角。")
    out.append("")
    out.append(f"- **正码推荐（6个）**：`{' '.join(str(x) for x in ai_pred['main_pick'])}`  →  {' · '.join(zm(x) for x in ai_pred['main_pick'])}")
    out.append(f"- **特码推荐（1个）**：`{ai_pred['special_pick']}`（{ai_pred['special_zodiac']}/{ai_pred['special_element']}）")
    out.append(f"- **3个推荐生肖**：`{' · '.join(ai_pred['top3_zodiac'])}`")
    out.append(f"- **10个数字**：`{' '.join(str(x) for x in ai_pred['top10'])}`")
    out.append(f"- **下一期正码生肖（回补·1个）**：`{ai_pred['main_zodiac']['zodiac']}`"
               f"（号码 {' '.join(str(x) for x in ai_pred['main_zodiac']['numbers'])}，正码遗漏 {ai_pred['main_zodiac']['omission']} 期）")
    out.append(f"- **五行（按综合分排序）**：" + "、".join(f"{e}({d['score']})" for e, d in [(x['element'], x) for x in ai_pred['element_rank']]))
    out.append(f"- **波色（按综合分排序）**：" + "、".join(f"{c['wave']}({c['score']})" for c in ai_pred['wave_rank']))
    out.append(f"- **单双推荐**：`{ai_pred['parity']['recommend']}`（历史单 {ai_pred['parity']['odd_share']}% / 双 {ai_pred['parity']['even_share']}%）")
    out.append(f"- **尾数推荐（Top3）**：`{' '.join(str(t)+'尾' for t in ai_pred['top_tails'])}`")
    out.append(f"- **头数推荐（Top2）**：`{' '.join(str(h)+'头' for h in ai_pred['top_heads'])}`")
    out.append("")
    out.append(f"### {name} · 🧠 大模式AI · 正码2中2 · 20组（每组2个正码，2个全中 赔60倍）\n")
    for s in range(20):
        a, b = ai_pred['pairs_2of2'][s]
        out.append(f"- 组{s+1:02d}：`{a} {b}`  →  {zm(a)} · {zm(b)}")
    out.append("")
    out.append(f"### {name} · 🧠 大模式AI · 三中3 · 20组（每组3个正码，3个全中 赔600倍）\n")
    for s in range(20):
        t = ai_pred['triples_3of3'][s]
        out.append(f"- 组{s+1:02d}：`{' '.join(str(x) for x in t)}`  →  {' · '.join(zm(x) for x in t)}")
    out.append("")

    # 其他视角
    out.append(f"### {name} · 其他视角参考\n")
    out.append(f"- **热度偏置**（重近期）：正码 `{' '.join(str(x) for x in hot_rank[:6])}` ｜ 特码 `{sp_pick}`")
    out.append(f"- **遗漏偏置**（重冷号）：正码 `{' '.join(str(x) for x in due_rank[:6])}` ｜ 特码 `{sp_pick}`")
    out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    out = []
    out.append("# 下一期参考组合推算（老澳 / 澳门 / 香港）\n")
    out.append("> ⚠️ **免责声明**：每期开奖是**独立随机事件**，历史数据**不能预测**未来结果。\n"
               "> 以下所有组合均来自同一套历史统计评分模型（窗口50期，权重 热度40%/稳定35%/遗漏25%），\n"
               "> 所谓「大数据大模型智能推算」即此多因子统计模型的可视化呈现，**仅供数据观察与娱乐参考，不代表任何中奖预测，切勿用于投注。**\n")
    for name in ORDER:
        out.append(gen_region(name))
        out.append("---")
    out.append("**说明**：所谓“推算”只是把历史统计（热度/稳定性/遗漏）加权打分后取高分号，\n"
               "理论上每个号每期出现概率相同（χ²检验 p 均 > 0.05，符合均匀随机）。\n"
               "不同视角给出的组合差异很大，正说明模型无法锁定结果。请理性看待。")
    open(os.path.join(HERE, "recommendation.md"), "w", encoding="utf-8").write("\n".join(out))

    # 写回 analysis.json（含各地区 prediction）
    with open(os.path.join(HERE, "analysis.json"), "w", encoding="utf-8") as f:
        json.dump(D, f, ensure_ascii=False, indent=1)
    print("recommendation.md 已生成，且 analysis.json 已写入 prediction，地区：", ORDER)
