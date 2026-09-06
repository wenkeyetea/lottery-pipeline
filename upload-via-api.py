#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""upload-via-api.py —— 用 urllib（不用 schannel）调 GitHub Contents API 上传文件
绕开 curl 的 schannel TLS 终结问题。
"""
import base64, json, os, sys, ssl, urllib.request, urllib.error
from pathlib import Path

USER = sys.argv[1] if len(sys.argv) > 1 else ""
PAT  = sys.argv[2] if len(sys.argv) > 2 else ""
REPO = sys.argv[3] if len(sys.argv) > 3 else "lottery-pipeline"
API  = "https://api.github.com"

# 入仓资产清单（不含生成产物和大数据文件）
INCLUDE = [
    ".github/workflows/lottery.yml",
    ".gitignore",
    "Procfile",
    "README.md",
    "analyze_patterns.py",
    "backtest.py",
    "build_dashboard.py",
    "build_report.py",
    "close_issues.py",
    "engine.py",
    "fetch_data.py",
    "fetch_laoao.py",
    "fetch_xinmacau.py",
    "live_hits_preserved.json",
    "pick-code.html",
    "predict_next.py",
    "recommendations_archive.json",
    "regen_index.py",
    "render.yaml",
    "requirements.txt",
    "run_server.bat",
    "server.py",
    "setup-github.sh",
    "upload-via-api.py",
    "upload-via-api.sh",
    "verify_zodiac_rule.py",
    "\u6fb3\u95e8.csv",
    "\u8001\u6fb3_2024-2026\u5b8c\u6574\u5f00\u5956.csv",
    "\u89c4\u5f8b\u8bb0\u5f55.md",
    "\u9999\u6e2f.csv",
]

SOFT_LIMIT = 1_048_576  # 1MB

# 不再验证吊销（解决 Windows 沙箱里 schannel 的 CRL 不可达问题）
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def call(method, url, body=None):
    data = None
    headers = {
        "Authorization": f"Bearer {PAT}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "lottery-uploader",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60, context=CTX) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {"raw": "<non-json body>"}
        return e.code, payload

print("==> 验证 token")
code, who = call("GET", f"{API}/user")
if code != 200:
    print(f"  \u274c token \u6821\u9a8c\u5931\u8d25 HTTP {code}: {who}"); sys.exit(1)
login = who.get("login", "?")
print(f"  \u767b\u5f55\u8d26\u53f7: {login} (\u671f\u671b: {USER})")

print(f"==> \u4e0a\u4f20 {len(INCLUDE)} \u4e2a\u6587\u4ef6")
ok = skip = fail = 0
for rel in INCLUDE:
    p = Path(rel)
    if not p.is_file():
        print(f"  \u26a0\ufe0f  \u8df3\u8fc7\uff08\u4e0d\u5b58\u5728\uff09: {rel}")
        skip += 1
        continue
    size = p.stat().st_size
    if size > SOFT_LIMIT:
        print(f"  \u26a0\ufe0f  \u8df3\u8fc7\uff08{size}B > 1MB\uff09: {rel}")
        skip += 1
        continue

    # 取现有 sha
    code, info = call("GET", f"{API}/repos/{USER}/{REPO}/contents/{rel}")
    sha = info.get("sha") if (code == 200 and isinstance(info, dict)) else None

    body = {
        "message": f"upload: {rel}",
        "content": base64.b64encode(p.read_bytes()).decode("ascii"),
    }
    if sha:
        body["sha"] = sha

    code, resp = call("PUT", f"{API}/repos/{USER}/{REPO}/contents/{rel}", body)
    if code in (200, 201):
        print(f"  \u2705 {rel} ({size}B)")
        ok += 1
    else:
        print(f"  \u274c {rel} HTTP {code}: {str(resp)[:200]}")
        fail += 1

print()
print("=" * 66)
print(f"\u4e0a\u4f20\u5b8c\u6210\uff1a\u6210\u529f {ok} \u8df3\u8fc7 {skip} \u5931\u8d25 {fail}")
print(f"  \u4ed3\u5e93: https://github.com/{USER}/{REPO}")
print("=" * 66)