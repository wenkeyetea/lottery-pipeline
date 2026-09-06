#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""upload-via-api.py —— 用 urllib（不用 schannel）调 GitHub Contents API 上传文件
绕开 curl 的 schannel TLS 终结问题。
"""
import base64, json, os, sys, ssl, urllib.request, urllib.error, urllib.parse
from pathlib import Path

USER = sys.argv[1] if len(sys.argv) > 1 else ""
PAT  = sys.argv[2] if len(sys.argv) > 2 else ""
REPO = sys.argv[3] if len(sys.argv) > 3 else "lottery-pipeline"
API  = "https://api.github.com"

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
    "澳门.csv",
    "老澳_2024-2026完整开奖.csv",
    "规律记录.md",
    "香港.csv",
]

SOFT_LIMIT = 1_048_576  # 1MB

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
    parsed = urllib.parse.urlsplit(url)
    encoded_path = urllib.parse.quote(parsed.path, safe="/")
    safe_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, encoded_path, parsed.query, parsed.fragment))
    req = urllib.request.Request(safe_url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120, context=CTX) as r:
            raw = r.read()
            try:
                return r.status, json.loads(raw.decode("utf-8"))
            except Exception:
                return r.status, {"raw": raw[:300].decode("utf-8", errors="replace")}
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read().decode("utf-8"))
        except Exception:
            payload = {"raw": "<non-json>"}
        return e.code, payload


print("==> 验证 token")
code, who = call("GET", f"{API}/user")
if code != 200:
    print(f"  token 校验失败 HTTP {code}: {who}"); sys.exit(1)
login = who.get("login", "?")
print(f"  登录账号: {login} (期望: {USER})")

print(f"==> 上传 {len(INCLUDE)} 个文件")
ok = skip = fail = 0
for rel in INCLUDE:
    p = Path(rel)
    if not p.is_file():
        print(f"  跳过（不存在）: {rel}")
        skip += 1
        continue
    size = p.stat().st_size
    if size > SOFT_LIMIT:
        print(f"  跳过（{size}B > 1MB）: {rel}")
        skip += 1
        continue

    base_body = {
        "message": f"upload: {rel}",
        "content": base64.b64encode(p.read_bytes()).decode("ascii"),
    }
    code, resp = call("PUT", f"{API}/repos/{USER}/{REPO}/contents/{rel}", base_body)
    if code in (200, 201):
        print(f"  OK {rel} ({size}B)")
        ok += 1
        continue

    # 已存在则取 sha 重试
    if code in (409, 422):
        sha = None
        for attempt in range(3):
            try:
                code2, info = call("GET", f"{API}/repos/{USER}/{REPO}/contents/{rel}")
                if code2 == 200 and isinstance(info, dict):
                    sha = info.get("sha")
                    break
            except Exception as e:
                print(f"  GET sha 重试 {attempt+1}/3: {type(e).__name__}: {str(e)[:80]}")
                continue
        if not sha:
            print(f"  FAIL {rel} 取 sha 失败")
            fail += 1
            continue
        base_body["sha"] = sha
        code, resp = call("PUT", f"{API}/repos/{USER}/{REPO}/contents/{rel}", base_body)
        if code in (200, 201):
            print(f"  OK {rel} ({size}B, updated)")
            ok += 1
        else:
            print(f"  FAIL {rel} HTTP {code}: {str(resp)[:200]}")
            fail += 1
    else:
        print(f"  FAIL {rel} HTTP {code}: {str(resp)[:200]}")
        fail += 1

print()
print("=" * 66)
print(f"上传完成：成功 {ok}  跳过 {skip}  失败 {fail}")
print(f"  仓库: https://github.com/{USER}/{REPO}")
print("=" * 66)