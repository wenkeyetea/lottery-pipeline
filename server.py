#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
开奖分析智能体 · 轻量后端
============================
提供：
  GET  /              仪表盘首页（site/index.html）
  GET  /pick-code     选号工具独立页
  GET  /api/data      返回最新 analysis.json（前端动态加载）
  POST /api/update    一键更新三地区数据（跑完整 pipeline）

pipeline 顺序（与自动化一致）：
  fetch_data.py -> engine.py -> predict_next.py -> regen_index.py -> build_report.py

说明：
  - fetch_data.py 联网刷新澳门/香港；若失败则警告并继续（使用本地快照），不致命。
  - 其余步骤失败则整体报错返回。
  - 更新成功后写入 .last_rows（三地区 CSV 行数合计）。
"""
import os
import sys
import csv
import json
import subprocess

from flask import Flask, send_from_directory, jsonify, request

BASE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(BASE, "site")
# 用当前 Python 解释器，便于在 GitHub Actions / Render / 本机都能跑
PY = sys.executable
DATA_FILE = os.path.join(BASE, "analysis.json")
LAST = os.path.join(BASE, ".last_rows")

PIPELINE = [
    "fetch_data.py",
    "engine.py",
    "predict_next.py",
    "regen_index.py",
    "build_report.py",
]

app = Flask(__name__, static_folder=SITE, static_url_path="")


@app.after_request
def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


@app.route("/")
def index():
    return send_from_directory(SITE, "index.html")


@app.route("/pick-code")
def pick_code():
    return send_from_directory(SITE, "pick-code.html")


@app.route("/api/data")
def api_data():
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception as e:  # noqa
        return jsonify({"error": str(e)}), 500


def count_rows():
    total = 0
    for fn in ["老澳_2024-2026完整开奖.csv", "澳门.csv", "香港.csv"]:
        p = os.path.join(BASE, fn)
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8", errors="ignore", newline="") as fh:
                    total += max(0, sum(1 for _ in csv.reader(fh)) - 1)
            except Exception:
                pass
    return total


@app.route("/api/update", methods=["POST"])
def api_update():
    log = []
    for step in PIPELINE:
        try:
            subprocess.run(
                [PY, os.path.join(BASE, step)],
                cwd=BASE,
                check=True,
                capture_output=True,
                text=True,
            )
            log.append("ok: " + step)
        except subprocess.CalledProcessError as e:
            if step == "fetch_data.py":
                log.append("warn: fetch_data.py 联网抓取失败，使用本地快照继续")
                continue
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": step + " 执行失败",
                        "log": log,
                        "detail": (e.stderr or "")[:600],
                    }
                ),
                500,
            )

    try:
        total = count_rows()
        with open(LAST, "w", encoding="utf-8") as f:
            f.write(str(total))
        log.append("last_rows = " + str(total))
    except Exception as e:  # noqa
        log.append("warn: 写入 .last_rows 失败 " + str(e))

    return jsonify({"status": "ok", "message": "三地区数据已刷新", "log": log, "rows": total})


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    import socket

    def lan_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
        finally:
            s.close()

    port = int(os.environ.get("PORT", "5000"))
    ip = lan_ip()
    print("=" * 56)
    print("开奖分析智能体 · 后端已启动")
    print("  本机访问 :  http://127.0.0.1:%d/" % port)
    print("  手机访问 :  http://%s:%d/  （需与电脑在同一 WiFi）" % (ip, port))
    print("  接口     :  POST /api/update  （一键更新数据）")
    print("=" * 56)
    app.run(host="0.0.0.0", port=port, debug=False)
