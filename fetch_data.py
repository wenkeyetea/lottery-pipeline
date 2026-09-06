# -*- coding: utf-8 -*-
"""
抓取澳门/香港开奖历史，转成与老澳同格式的 CSV。
数据来源：http://kjresultstatus.com/record (POST, status=2澳门/1香港, time=年份)
生肖/五行：统一采用老澳固定对照表(analysis.json)，保证三地区统计口径一致。
"""
import json, csv, urllib.request, urllib.parse, urllib.error

RECORD_URL = "http://kjresultstatus.com/record"
REF = "http://tthx.kjresultstatus.com:12944/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ---- 1. 从 analysis.json 提取 号码->(生肖,五行) 固定对照表 ----
# 多地区统一采用同一份固定对照表(老澳口径)，放在 regions[首地区] 下
A = json.load(open("analysis.json", encoding="utf-8"))
_R0 = A["regions"][A["regions_order"][0]]
MAP = {n["num"]: (n["zodiac"], n["element"]) for n in _R0["numbers"]}
assert len(MAP) == 49, f"对照表异常: {len(MAP)}"

def to_cell(num):
    num = int(num)
    z, e = MAP[num]
    return f"{num}({z}/{e})"

def fetch_history(status, year, retries=4):
    last = None
    for i in range(retries):
        try:
            data = urllib.parse.urlencode({"status": status, "time": year}).encode("utf-8")
            req = urllib.request.Request(RECORD_URL, data=data,
                                          headers={"Referer": REF, "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as ex:
            last = ex
            print(f"  ! {year} 第{i+1}次失败: {ex}，重试...")
    raise last

def write_csv(region, status, years):
    rows = []
    for y in years:
        try:
            j = fetch_history(status, y)
        except Exception as ex:
            print(f"  ! {region} {y} 抓取失败: {ex}")
            continue
        recs = j.get("data") or []
        for rec in recs:
            try:
                issue = f"{rec['year']}{rec['phase']}"   # 如 2026091
                mains = [to_cell(rec[f"num_{k}"]) for k in
                         ["one", "two", "three", "four", "five", "six"]]
                sp = to_cell(rec["num_special"])
                rows.append([rec["year"], issue] + mains + [sp])
            except Exception as ex:
                print(f"  ! 解析单行失败: {ex} | {rec}")
        print(f"  {region} {y}: {len(recs)} 期")
    # 按期号升序
    rows.sort(key=lambda r: r[1])
    # 去重：源站 API 偶发同一期号返回两条不同记录，按"同一期号只保留首次出现"处理
    seen, uniq = set(), []
    for r in rows:
        if r[1] in seen:
            print(f"  ! 跳过重复期号 {r[1]}")
            continue
        seen.add(r[1]); uniq.append(r)
    rows = uniq
    fn = f"{region}.csv"
    with open(fn, "w", encoding="gb18030", newline="") as f:
        w = csv.writer(f)
        w.writerow(["年份", "期号", "正码1", "正码2", "正码3", "正码4", "正码5", "正码6", "特码"])
        w.writerows(rows)
    print(f"=> 写出 {fn}: 共 {len(rows)} 期")
    return len(rows)

if __name__ == "__main__":
    YEARS = [2024, 2025, 2026]
    print("抓取澳门(status=2)...")
    write_csv("澳门", 2, YEARS)
    print("抓取香港(status=1)...")
    write_csv("香港", 1, YEARS)
    print("完成。")
