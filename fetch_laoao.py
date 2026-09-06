# -*- coding: utf-8 -*-
"""
fetch_laoao.py —— 抓取 55128 老澳(澳门彩 6+1) 历史开奖，追加到本地 CSV。

数据源: https://m.55128.cn/kjh/am6hc-history-120.htm
        (页面标题"澳门彩历史开奖结果"，含每期完整 6+1：
         6 个正码(号码+生肖/五行) + <div class="jiahaos"> + </div> + 1 个特码)

每期结构(2026-08 实测):
  第 <strong>2026239</strong>期
    <div class="kjh-wxs"><span class="kj-blue"> 04 </span><p>兔/金</p></div>  × 6 正码
    <div class="jiahaos"> + </div>
    <div class="kjh-wxs"><span class="kj-green"> 06 </span><p>牛/土</p></div>  特码

CSV 格式: 年份,期号,正码1..6(生肖/五行),特码(生肖/五行)
只追加 CSV 里【没有】的新期号，幂等、不会重复。
"""
import urllib.request
import re
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "老澳_2024-2026完整开奖.csv")
URL = "https://m.55128.cn/kjh/am6hc-history-120.htm"
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
      "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")

# 用户核定五行表(覆盖源站可能错标的五行; 与 engine.py 的 ELEMENT_MAP 一致)
ELEMENT_MAP = {
    6:"土",7:"土",20:"土",21:"土",28:"土",29:"土",36:"土",37:"土",
    2:"火",3:"火",10:"火",11:"火",18:"火",19:"火",32:"火",33:"火",40:"火",41:"火",48:"火",49:"火",
    8:"木",9:"木",16:"木",17:"木",24:"木",25:"木",38:"木",39:"木",46:"木",47:"木",
    4:"金",5:"金",12:"金",13:"金",26:"金",27:"金",34:"金",35:"金",42:"金",43:"金",
    1:"水",14:"水",15:"水",22:"水",23:"水",30:"水",31:"水",44:"水",45:"水",
}
assert len(ELEMENT_MAP) == 49

# 期号：可能被 <strong> 包裹："第 <strong>2026239</strong>期"
ISSUE_RE = re.compile(r'第\s*(?:<strong>)?\s*(\d{7})\s*(?:</strong>)?\s*期')
# 球：<span class="kj-blue"> 04 </span> <p>兔/金</p>
BALL_RE = re.compile(r'<span class="kj-[a-z]+">\s*(\d{1,2})\s*</span>\s*<p>\s*([^<]+?)\s*</p>')


def fetch_html(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://m.55128.cn/"})
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read()
    for enc in ("utf-8", "gb18030", "gbk"):
        try:
            return raw.decode(enc)
        except Exception:
            pass
    return raw.decode("utf-8", "ignore")


def parse_periods(html):
    spans = [(m.group(1), m.start()) for m in ISSUE_RE.finditer(html)]
    spans.append(("END", len(html)))
    out = []
    for i in range(len(spans) - 1):
        issue, start = spans[i]
        block = html[start:spans[i + 1][1]]
        balls = BALL_RE.findall(block)  # [(num, zodiac/element), ...]
        if len(balls) < 7:
            print(f"[warn] 期 {issue}: 仅解析到 {len(balls)} 个球，跳过", file=sys.stderr)
            continue
        nums = [int(b[0]) for b in balls[:7]]
        zes = [b[1] for b in balls[:7]]
        if any(n < 1 or n > 49 for n in nums):
            print(f"[warn] 期 {issue}: 号码越界 {nums}，跳过", file=sys.stderr)
            continue
        main = nums[:6]
        special = nums[6]

        def cell(n, ze):
            z, e = ze.split("/")
            e = ELEMENT_MAP.get(n, e)
            return f"{n}({z}/{e})"

        cells = [cell(main[j], zes[j]) for j in range(6)] + [cell(special, zes[6])]
        out.append((issue, [issue[:4], issue] + cells))
    return out


def main():
    html = fetch_html(URL)
    periods = parse_periods(html)
    if not periods:
        print("未解析到任何期号，可能页面结构变化。未改动 CSV。")
        return
    print(f"页面解析到期数: {len(periods)} (最新 {periods[0][0]} … 最旧 {periods[-1][0]})")

    # 读现有 CSV
    rows = []
    with open(CSV, encoding="gb18030", newline="") as f:
        for r in csv.reader(f):
            rows.append(r)
    header, data = rows[0], rows[1:]
    existing = {r[1] for r in data if len(r) >= 9}

    # 仅追加新期(按 issue 升序)
    new = sorted([p for p in periods if p[0] not in existing], key=lambda x: x[0])
    if not new:
        print("CSV 已是最新，无新期需要追加。")
        return

    for issue, row in new:
        data.append(row)
        print(f"  + 追加 {issue}: 正码 {row[2:8]} 特码 {row[8]}")

    with open(CSV, "w", encoding="gb18030", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(data)
    print(f"完成: 新增 {len(new)} 期，CSV 现有 {len(data)} 期。")


if __name__ == "__main__":
    main()
