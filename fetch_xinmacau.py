#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""抓取 新澳门彩(55128.cn) 2026 全年 001-233 期完整 6+1 数据，写出 新澳门.csv
   数据来源：
     - history-120 页 => 114-233 期 (6正码+特码)
     - 单期 kjjg 详情页 => 001-113 期 (补齐)
   生肖/五行沿用老澳固定对照（统一口径），见 zodiac_map 由 analysis.json 提供。
"""
import re, csv, os, sys, json, time
import urllib.request

BASE = "https://m.55128.cn"
HIST120 = BASE + "/kjh/newam6hc-history-120.htm"
KJJG = BASE + "/kjh/newam6hc-kjjg-{issue}.htm"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# 老澳固定生肖/五行对照（号码 1-49）
A = json.load(open("analysis.json", encoding="utf-8"))
FIRST = A["regions_order"][0]
MAP = {n["num"]: (n["zodiac"], n["element"]) for n in A["regions"][FIRST]["numbers"]}

def http_get(url, retries=4):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE + "/"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception as e:
            last = e
            time.sleep(0.6 * (i + 1))
    print("  [warn] 抓取失败 %s : %s" % (url, last))
    return ""

def parse_item_block(block):
    nums = re.findall(r'kjh-wxs[^>]*>\s*<span[^>]*>\s*(\d{1,2})\s*</span>', block)
    if len(nums) == 7:
        return [int(x) for x in nums]
    return None

# ---- 1. 从 history-120 拿 114-233 ----
print("抓取 history-120 ...")
html = http_get(HIST120)
draws = {}  # issue -> [m1..m6, sp]
if html:
    parts = html.split('class="item"')
    for p in parts[1:]:
        m = re.search(r'<strong>(\d+)</strong>期', p)
        nums = parse_item_block(p)
        if m and nums:
            draws[m.group(1)] = nums
print("  history-120 得到 %d 期" % len(draws))

# ---- 2. 补齐 001-113 ----
need = ["2026" + str(i).zfill(3) for i in range(1, 114)]
missing = [iss for iss in need if iss not in draws]
print("需补齐 %d 期 (001-113) ..." % len(missing))
ok = 0
for iss in missing:
    url = KJJG.format(issue=iss)
    h = http_get(url)
    if not h:
        continue
    nums = parse_item_block(h)
    if nums:
        draws[iss] = nums
        ok += 1
    else:
        # 尝试从整页提取
        nums2 = re.findall(r'kjh-wxs[^>]*>\s*<span[^>]*>\s*(\d{1,2})\s*</span>', h)
        if len(nums2) >= 7:
            draws[iss] = [int(x) for x in nums2[:7]]
            ok += 1
    time.sleep(0.15)
print("  补齐成功 %d 期" % ok)

# ---- 3. 写 CSV ----
issues = sorted(draws.keys())
rows = []
for iss in issues:
    nums = draws[iss]
    year = iss[:4]
    cells = []
    for n in nums:
        z, e = MAP.get(n, ("?", "?"))
        cells.append("%d(%s/%s)" % (n, z, e))
    rows.append([year, iss] + cells)

fn = "新澳门.csv"
with open(fn, "w", encoding="gb18030", newline="") as f:
    w = csv.writer(f)
    w.writerow(["年份", "期号", "正码1", "正码2", "正码3", "正码4", "正码5", "正码6", "特码"])
    w.writerows(rows)
print("写出 %s : %d 期 (范围 %s ~ %s)" % (fn, len(rows), issues[0], issues[-1]))
