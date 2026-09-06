# 六合每期推算与存档

三地区（老澳 / 澳门 / 香港）开奖数据采集、统计推算、真实命中率核验、可交互仪表盘一体化项目。

## 流水线（顺序严格串行）

| 步骤 | 脚本 | 说明 |
|---|---|---|
| 1 | `fetch_data.py` | 抓澳门 / 香港开奖（kjresultstatus.com），写 `澳门.csv` / `香港.csv` |
| 2 | `fetch_laoao.py` | 抓老澳开奖（m.55128.cn），追加到 `老澳_2024-2026完整开奖.csv` |
| 3 | `engine.py` | 重算三地区统计（χ² / 频率 / 冷热 / 生肖五行 / 共现），写 `analysis.json` |
| 4 | `backtest.py` | 模型确定性种子重建回测台账（N_DETAIL=10**9 全量保留），写 `analysis.json` |
| 5 | `predict_next.py` | 推算下一期 6 正 + 1 特 + 全玩法 + 大模式 AI，幂等写入 `recommendations_archive.json` |
| 6 | `close_issues.py` | 真实关单：与实际开奖比对写 `live_hits` / `ai_live_hits`；历史真实命中留痕保护（`live_hits_preserved.json`） |
| 7 | `analyze_patterns.py` | 提炼统计规律 → `patterns.json` / `规律记录.md`（失败不阻塞） |
| 8 | `regen_index.py` + `build_report.py` | 刷新 `site/index.html` 仪表盘 + `report.md` / `recommendation.md` |
| 9 | deploy | 把 `site/` 部署上线 |
| 10 | log | 在 `.workbuddy/automations/.../memory.md` 追加当日执行记录 |

## 三种运行方式

### A. 本地跑（最简单）
```bash
cd laoya_analysis
python fetch_data.py
python fetch_laoao.py      # 抓老澳，失败可忽略
python engine.py
python backtest.py
python predict_next.py
python close_issues.py
python analyze_patterns.py
python regen_index.py
python build_report.py
```
依赖：`pip install flask`（其它脚本零依赖）。

### B. WorkBuddy 自动化（当前活跃）
- 自动化 ID `c1db2734-d0b9-4e9d-90b9-73be433b4567`
- 每天 22:00 (Asia/Shanghai) 自动跑全链路 + 部署到 WorkBuddy
- 链接：https://5b7e6b34bcbd4d97aa44f0cab9daa3ae.app.workbuddy.link
- ⚠️ WorkBuddy 自动化跑的是云端 AI 推理，但工具调用落回本机执行 → **电脑关机则采集/推算这一段会失败**，只有 dashboard 仍能访问。

### C. GitHub Actions + gh-pages（推荐，电脑关机也能跑）
把整个 `laoya_analysis/` 推到 GitHub 私有仓库后：

1. 仓库 Settings → Pages → Source 选 "GitHub Actions"
2. workflow `.github/workflows/lottery.yml` 已配置好：
   - 每天 UTC 14:00（=北京时间 22:00）自动触发
   - 也支持 Actions 页面手动 `Run workflow`
   - 跑完把 CSV / analysis.json / site/ 全部 commit 回 main 分支（git 历史即数据备份）
   - `site/` 通过 `actions/deploy-pages` 自动部署到 gh-pages 分支
3. 仪表盘 URL：仓库 Settings → Pages 顶部显示的 `https://<owner>.github.io/<repo>/`

#### 首次推到 GitHub 的步骤
```bash
cd laoya_analysis
git init
git add -A
git commit -m "init: lottery pipeline + gh-actions"
git branch -M main
git remote add origin https://github.com/<your-name>/<repo>.git
git push -u origin main
```
第一次 push 后到 GitHub 仓库 → Actions → 看到 `Lottery Pipeline` workflow → 等它跑完。

#### 老澳抓取在 GitHub Actions 上的差异
- GitHub runner 没有系统代理，可直连 m.55128.cn（无需 WebFetch 备选）
- 如果 kjresultstatus.com / 55128 当天不可达，相关步骤会 `continue-on-error` 跳过，不阻塞整条链路

### D. Render / Fly.io（备选托管）
项目里 `Procfile` + `render.yaml` 已为 Render 准备好，可部署 Flask 服务（仅做仪表盘查询接口），数据由 GitHub Actions 或本机更新。

## 核心约束
- **正码与特码不得重复**；每期必须先完整真实存档（严格串行）后再推下一期
- **命中率只用真实开奖核验**，不做估算；历史真实命中通过 `live_hits_preserved.json` 留痕保护，迁移机器也不丢
- **AI 关单字段**：main_hit / special_hit / zodiac_hit / top10_hit / h2_ai / h3_ai（29 条历史记录已核验规则一致）

## 数据文件
- `老澳_2024-2026完整开奖.csv`（gb18030，约 980 期）
- `澳门.csv`（gb18030，约 961 期）
- `香港.csv`（gb18030，约 361 期）
- `analysis.json`（engine / backtest 输出，供仪表盘消费）
- `recommendations_archive.json`（按期号归档的"针对哪一期"的真实推荐）
- `live_hits_preserved.json`（历史真实命中留痕，跨机器迁移保护用）
- `patterns.json`（统计规律结构化）
- `site/index.html`（仪表盘）

## 重要声明
- 彩票开奖是**独立随机事件**，历史号码不影响未来结果。
- 所有频率、冷热、推算、收益回测**仅供数据观察与娱乐参考**，**不能提高中奖概率**，不构成投注建议。
- 收益回测基于历史命中率，≠ 真实概率；真实赔率已内含庄家优势。请理性购彩，量力而行，**切勿用于赌博投入**。
<!-- trigger 2026-09-06 23:55 -->