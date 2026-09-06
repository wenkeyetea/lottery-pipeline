#!/usr/bin/env bash
# upload-via-api.sh —— Git push 卡死时的备选：直接用 Contents API 上传所有文件
# 用法：bash upload-via-api.sh <USER> <PAT>

set -euo pipefail

USER_NAME="${1:-}"
PAT="${2:-}"
REPO="${3:-lottery-pipeline}"
API="https://api.github.com"

CURL="curl --ssl-no-revoke -sS"
TMP="$PWD/.setup_tmp"; mkdir -p "$TMP"

# 待上传的文件/目录清单（git 入仓的核心资产，不含生成产物和大数据）
INCLUDE=(
  ".github/workflows/lottery.yml"
  ".gitignore"
  "Procfile"
  "README.md"
  "analyze_patterns.py"
  "backtest.py"
  "build_dashboard.py"
  "build_report.py"
  "close_issues.py"
  "engine.py"
  "fetch_data.py"
  "fetch_laoao.py"
  "fetch_xinmacau.py"
  "live_hits_preserved.json"
  "pick-code.html"
  "predict_next.py"
  "recommendations_archive.json"
  "regen_index.py"
  "render.yaml"
  "requirements.txt"
  "run_server.bat"
  "server.py"
  "setup-github.sh"
  "verify_zodiac_rule.py"
  "澳门.csv"
  "老澳_2024-2026完整开奖.csv"
  "规律记录.md"
  "香港.csv"
)

# 单文件大小软限制（字节）。超过则用 git LFS 或分块方案
SOFT_LIMIT=1048576   # 1 MB

upload_one() {
  local path="$1"
  local abs="$PWD/$path"
  if [[ ! -f "$abs" ]]; then
    echo "  ⚠️  跳过（不存在）: $path"
    return 0
  fi
  local size=$(stat -c %s "$abs" 2>/dev/null || stat -f %z "$abs")
  if [[ "$size" -gt "$SOFT_LIMIT" ]]; then
    echo "  ⚠️  跳过（${size}B > 1MB，建议走 git LFS）: $path"
    return 0
  fi

  # 现有 sha（如果文件已存在，PUT 需要 sha）
  local sha=""
  local get_resp=$(mktemp)
  $CURL -H "Authorization: Bearer $PAT" -H "Accept: application/vnd.github+json" \
    "$API/repos/$USER_NAME/$REPO/contents/$path" > "$get_resp"
  if grep -q '"sha"' "$get_resp" 2>/dev/null; then
    sha=$(grep '"sha"' "$get_resp" | head -1 | cut -d'"' -f4)
  fi
  rm -f "$get_resp"

  # base64 编码（去除换行，API 要求单行 base64）
  local b64=$(base64 -w 0 "$abs" 2>/dev/null || base64 "$abs" | tr -d '\n')

  # 构造 JSON payload（用 python -c 避免 jq 依赖）
  local payload
  payload=$(python -c "
import json, sys
sha = sys.argv[1] if sys.argv[1] else None
print(json.dumps({
  'message': 'upload: ' + sys.argv[2],
  'content': sys.argv[3],
  **({'sha': sha} if sha else {})
}, ensure_ascii=False))
" "$sha" "$path" "$b64")

  local resp_code
  resp_code=$($CURL -o "$TMP/upload_resp.json" -w "%{http_code}" \
    -X PUT "$API/repos/$USER_NAME/$REPO/contents/$path" \
    -H "Authorization: Bearer $PAT" \
    -H "Accept: application/vnd.github+json" \
    -d "$payload")

  case "$resp_code" in
    200|201) echo "  ✅ $path" ;;
    *)       echo "  ❌ $path HTTP $resp_code:"; head -c 300 "$TMP/upload_resp.json"; echo ;;
  esac
}

# python 必须用绝对路径（Git Bash 默认没有 python）
PY_BIN="C:/Users/86138/.workbuddy/binaries/python/versions/3.13.12/python.exe"
if ! command -v python >/dev/null 2>&1; then
  alias python="$PY_BIN"
fi

echo "==> 验证 token"
HTTP_CODE=$($CURL -o "$TMP/whoami.json" -w "%{http_code}" \
  -H "Authorization: Bearer $PAT" -H "Accept: application/vnd.github+json" \
  "$API/user")
LOGIN=$(grep '"login"' "$TMP/whoami.json" | head -1 | cut -d'"' -f4)
echo "  登录账号: $LOGIN (期望: $USER_NAME)"

echo "==> 上传 ${#INCLUDE[@]} 个文件"
for f in "${INCLUDE[@]}"; do
  upload_one "$f"
done

echo ""
echo "=================================================================="
echo "📦 上传完成！"
echo "  仓库: https://github.com/$USER_NAME/$REPO"
echo "=================================================================="