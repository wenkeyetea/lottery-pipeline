#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把最新 analysis.json 注入 index.html 的 __DATA__ 占位符，并同步到 site/。
   不改动任何 HTML/CSS/JS 结构（保持手写的「三/四地区独立面板」设计），
   只刷新数据。供自动化定时重跑使用。
"""
import json, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "analysis.json"), encoding="utf-8") as f:
    data = json.load(f)

# 合并历史规律统计（analyze_patterns.py 生成），供「规律图谱」面板渲染
_pat = os.path.join(HERE, "patterns.json")
if os.path.exists(_pat):
    try:
        with open(_pat, encoding="utf-8") as pf:
            data["patterns"] = json.load(pf)
    except Exception as e:
        print("⚠️ patterns.json 读取失败，跳过:", e)

DATA_JS = json.dumps(data, ensure_ascii=False)

html = open(os.path.join(HERE, "index.html"), encoding="utf-8").read()

# 若已注入（无占位符），先把内联 DATA 还原为占位符，保证可重复注入
# 兼容 const / let 两种声明（前端已改为 let 以支持动态刷新）
if "__DATA__" not in html:
    html = re.sub(r'(?:const|let) DATA = .*?\};\n', 'let DATA = __DATA__;\n', html, count=1, flags=re.S)

if "__DATA__" not in html:
    raise SystemExit("ERROR: 未能定位 __DATA__ 占位符，index.html 结构异常")

html = html.replace("__DATA__", DATA_JS)
out = os.path.join(HERE, "index.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

# 同步到干净部署目录
os.makedirs(os.path.join(HERE, "site"), exist_ok=True)
shutil.copy(out, os.path.join(HERE, "site", "index.html"))

print("✅ regen_index 完成，地区：", data["regions_order"])
