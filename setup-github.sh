#!/usr/bin/env bash
# setup-github.sh —— 一键把 laoya_analysis 推到 GitHub 私有仓库 + 启用 Pages
# 用法：
#   bash setup-github.sh <GITHUB_USER> <FINE_GRAINED_PAT>
#
# 前置：用户 GitHub 账号 + fine-grained PAT（repo + workflow 权限）
# Windows Git Bash 兼容：用 sentinel 把 body 和 http_code 都打到 stdout，事后 split

set -euo pipefail

USER_NAME="${1:-}"
PAT="${2:-}"

if [[ -z "$USER_NAME" || -z "$PAT" ]]; then
  echo "用法: bash setup-github.sh <GitHub用户名> <fine-grained-PAT>" >&2
  exit 1
fi

REPO="lottery-pipeline"
API="https://api.github.com"
# curl 必须用 --ssl-no-revoke，Windows schannel 在吊销服务器不可达时会拒绝连接
CURL="curl --ssl-no-revoke -sS"
TMP="$PWD/.setup_tmp"
mkdir -p "$TMP"

# 调用方式：call_curl "METHOD" "URL" [JSON_BODY]
# 把 stdout 分成 body 和 http_code，body 写到 $TMP/body.json，echo http_code
call_curl() {
  local method="$1"
  local url="$2"
  local body="${3:-}"
  local out
  if [[ -n "$body" ]]; then
    out=$($CURL -X "$method" "$url" \
      -H "Authorization: Bearer $PAT" \
      -H "Accept: application/vnd.github+json" \
      -d "$body" \
      -w $'\n___CODE=%{http_code}' 2>/dev/null)
  else
    out=$($CURL -X "$method" "$url" \
      -H "Authorization: Bearer $PAT" \
      -H "Accept: application/vnd.github+json" \
      -w $'\n___CODE=%{http_code}' 2>/dev/null)
  fi
  echo "$out" | grep -v '^___CODE=' > "$TMP/body.json"
  echo "$out" | grep '^___CODE=' | cut -d= -f2
}

echo "==> 1/6 检查 token 权限"
HTTP_CODE=$(call_curl GET "$API/user")
if [[ "$HTTP_CODE" != "200" ]]; then
  echo "  ❌ token 校验失败 HTTP $HTTP_CODE:"; head -c 300 "$TMP/body.json"; echo; exit 1
fi
LOGIN=$(grep '"login"' "$TMP/body.json" | head -1 | cut -d'"' -f4)
echo "  登录账号: $LOGIN (期望: $USER_NAME)"
if [[ -z "$LOGIN" ]]; then
  echo "  ❌ 无法解析登录账号"; head -c 300 "$TMP/body.json"; echo; exit 1
fi

echo "==> 2/6 创建私有仓库 $USER_NAME/$REPO"
HTTP_CODE=$(call_curl POST "$API/user/repos" \
  "{\"name\":\"$REPO\",\"private\":true,\"description\":\"六合每期推算与存档（GitHub Actions + gh-pages）\",\"auto_init\":false}")
case "$HTTP_CODE" in
  201) echo "  ✅ 仓库创建成功" ;;
  422) echo "  ⚠️  仓库已存在（HTTP 422），继续使用" ;;
  *)   echo "  ❌ 创建失败 HTTP $HTTP_CODE:"; head -c 500 "$TMP/body.json"; echo; exit 1 ;;
esac

echo "==> 3/6 git init + commit（如尚未提交）"
if [[ ! -d .git ]]; then
  git init -q
  git config user.name "lottery-bot"
  git config user.email "lottery-bot@users.noreply.github.com"
fi
git add -A
if git diff --cached --quiet; then
  echo "  已有 commit，跳过"
else
  git commit -q -m "init: lottery pipeline + gh-actions workflow"
  echo "  ✅ commit 完成"
fi

echo "==> 4/6 git push 到 main 分支"
BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "main")
git remote remove origin 2>/dev/null || true
git remote add origin "https://x-access-token:${PAT}@github.com/${USER_NAME}/${REPO}.git"
git push -q -u origin "$BRANCH"
echo "  ✅ push 完成"

echo "==> 5/6 启用 GitHub Pages (Source = GitHub Actions)"
HTTP_CODE=$(call_curl POST "$API/repos/$USER_NAME/$REPO/pages" '{"build_type":"workflow"}')
case "$HTTP_CODE" in
  201|204) echo "  ✅ Pages 已启用（workflow 模式）" ;;
  409)     echo "  ⚠️  Pages 已启用过（HTTP 409），跳过" ;;
  *)       echo "  ⚠️  Pages 启用返回 HTTP $HTTP_CODE（内容）:"; head -c 300 "$TMP/body.json"; echo ;;
esac

echo "==> 6/6 触发一次 workflow_dispatch 测试跑"
HTTP_CODE=$(call_curl POST "$API/repos/$USER_NAME/$REPO/actions/workflows/lottery.yml/dispatches" '{"ref":"main"}')
if [[ "$HTTP_CODE" == "204" ]]; then
  echo "  ✅ 已触发，~30 秒后可在 Actions 页面查看运行状态"
else
  echo "  ⚠️  触发返回 HTTP $HTTP_CODE（多半 workflow 还没出现在 main 分支上，先 commit 一下就行）"
fi

echo ""
echo "=================================================================="
echo "🎉 全部完成！"
echo "  仓库:    https://github.com/$USER_NAME/$REPO"
echo "  Actions: https://github.com/$USER_NAME/$REPO/actions"
echo "  Pages:   https://$USER_NAME.github.io/$REPO/  (首次部署后 ~1 分钟可访问)"
echo "=================================================================="