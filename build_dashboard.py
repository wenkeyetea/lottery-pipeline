#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 analysis.json, 生成自包含交互式仪表盘 index.html (零外部依赖)。"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "analysis.json"), encoding="utf-8") as f:
    data = json.load(f)

DATA_JS = json.dumps(data, ensure_ascii=False)

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>老澳开奖 · 统计研究与推算智能体</title>
<style>
  :root{
    --bg:#f5f6f8; --panel:#ffffff; --ink:#1f2430; --sub:#6b7280;
    --line:#e5e7eb; --brand:#c0392b; --brand2:#2c7be5; --good:#16a34a;
    --warn:#d97706; --chip:#eef2f7;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
       font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;line-height:1.5}
  .wrap{max-width:1080px;margin:0 auto;padding:20px 16px 60px}
  header h1{margin:0 0 4px;font-size:24px;letter-spacing:.5px}
  header .sub{color:var(--sub);font-size:14px}
  .warnbar{background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;
           padding:10px 14px;border-radius:10px;font-size:13px;margin:14px 0}
  .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:16px 0}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
  .card .k{font-size:12px;color:var(--sub)}
  .card .v{font-size:22px;font-weight:700;margin-top:4px}
  .panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;
         padding:16px 18px;margin:16px 0}
  .panel h2{font-size:17px;margin:0 0 10px;display:flex;align-items:center;gap:8px}
  .panel h2 .dot{width:8px;height:8px;border-radius:50%;background:var(--brand)}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  @media(max-width:760px){.grid2{grid-template-columns:1fr}}
  canvas{max-width:100%}
  table{width:100%;border-collapse:collapse;font-size:13px}
  th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:center}
  th{color:var(--sub);font-weight:600;background:#fafbfc}
  .tag{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11px;background:var(--chip);margin:1px}
  .hot{color:var(--brand);font-weight:700}
  .cold{color:var(--brand2);font-weight:700}
  .controls{display:flex;flex-wrap:wrap;gap:18px;align-items:center;margin-bottom:12px}
  .controls label{font-size:13px;color:var(--sub);display:flex;flex-direction:column;gap:4px}
  input[type=range]{width:160px}
  button{background:var(--brand);color:#fff;border:0;border-radius:9px;
         padding:9px 16px;font-size:14px;cursor:pointer}
  button.ghost{background:var(--chip);color:var(--ink)}
  .pool{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
  .ball{width:40px;height:40px;border-radius:50%;display:flex;align-items:center;
        justify-content:center;font-weight:700;color:#fff;font-size:15px;position:relative}
  .legend{font-size:12px;color:var(--sub);margin-top:6px}
  .sets{display:flex;flex-wrap:wrap;gap:10px;margin-top:10px}
  .set{background:var(--chip);border-radius:10px;padding:8px 12px;font-size:13px}
  .set b{color:var(--brand)}
  .note{font-size:12px;color:var(--sub);margin-top:8px}
  details{margin-top:8px}
  summary{cursor:pointer;color:var(--brand2);font-size:13px}
  .filterbox{display:flex;flex-wrap:wrap;gap:14px;margin:4px 0 12px;align-items:center}
  .filterbox .grp{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
  .chk{display:inline-flex;align-items:center;gap:4px;font-size:12px;background:var(--chip);
       padding:3px 9px;border-radius:999px;cursor:pointer;user-select:none}
  .chk input{accent-color:var(--brand);margin:0}
  .pickgrid{display:grid;grid-template-columns:repeat(10,1fr);gap:6px;margin:8px 0}
  .pickbtn{height:34px;border:1px solid var(--line);border-radius:8px;background:#fff;
           cursor:pointer;font-size:13px;font-weight:600;color:var(--ink)}
  .pickbtn.on{background:var(--brand);color:#fff;border-color:var(--brand)}
  .oddsrow{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:6px}
  .oddsrow label{font-size:12px;color:var(--sub);display:flex;gap:4px;align-items:center}
  .oddsrow input{width:56px;padding:3px 5px;border:1px solid var(--line);border-radius:6px}
  .pairset{background:var(--chip);border-radius:10px;padding:8px 12px;font-size:13px;min-width:118px}
  .pairset b{color:var(--brand);font-size:16px;letter-spacing:1px}
  .pairset span{color:var(--sub);font-size:12px;margin-left:4px}
  .hist-ctrl{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:4px 0 12px}
  .hist-ctrl input[type=text]{padding:6px 10px;border:1px solid var(--line);border-radius:8px;font-size:13px;width:160px}
  .hist-ctrl select{padding:6px 10px;border:1px solid var(--line);border-radius:8px;font-size:13px;background:#fff}
  .hist-ctrl .hint{font-size:12px;color:var(--sub)}
  .hist-wrap{max-height:520px;overflow:auto;border:1px solid var(--line);border-radius:10px}
  table.hist{width:100%;border-collapse:collapse;font-size:13px}
  table.hist th,table.hist td{padding:7px 8px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
  table.hist th{position:sticky;top:0;background:#f0f2f5;z-index:1;color:var(--sub);font-weight:600}
  table.hist tr:hover td{background:#f7f9ff}
  .mball{display:inline-flex;flex-direction:column;align-items:center;justify-content:center;
    width:30px;height:34px;border-radius:7px;color:#fff;font-weight:700;font-size:13px;margin:1px;vertical-align:middle}
  .mball small{font-size:9px;font-weight:400;opacity:.9;line-height:1}
  .mball.sp{box-shadow:0 0 0 2px var(--brand);outline:2px solid #fff}
  .mball.dim{opacity:.32}
  .region-tabs{display:flex;gap:8px;margin:8px 0 2px;flex-wrap:wrap}
  .rtab{padding:7px 20px;border:1px solid var(--line);border-radius:999px;background:#fff;
    font-size:14px;font-weight:600;cursor:pointer;color:var(--sub)}
  .rtab.on{background:var(--brand);color:#fff;border-color:var(--brand)}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>🎯 开奖统计研究与推算智能体</h1>
    <div class="region-tabs" id="regionTabs"></div>
    <div class="sub" id="subline"></div>
  </header>

  <div class="warnbar">
    ⚠️ <b>理性提醒</b>：本工具仅做<b>历史数据统计</b>与<b>多因子参考打分</b>。彩票每期开奖为<b>独立随机事件</b>，
    任何模型都<b>无法提高真实中奖概率</b>（下方卡方检验也证实数据符合均匀随机）。
    本页所有"推算"仅供娱乐与数据观察，<b>切勿作为投注依据</b>。
  </div>

  <div class="cards" id="cards"></div>

  <div class="panel">
    <h2><span class="dot"></span>① 号码频率总览（全部 __TOTAL__ 期 · 1–49）</h2>
    <canvas id="freqChart" height="300"></canvas>
    <div class="legend">柱高=出现总次数；<span style="color:#c0392b">红</span>=高于期望，<span style="color:#2c7be5">蓝</span>=低于期望（按 z 值着色）。虚线=理论期望每号 __EXP__ 次。</div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2><span class="dot"></span>② 生肖分布</h2>
      <canvas id="zodiacChart" height="260"></canvas>
      <div class="legend">按号码归属生肖统计出现次数。</div>
    </div>
    <div class="panel">
      <h2><span class="dot"></span>③ 五行分布</h2>
      <canvas id="elementChart" height="260"></canvas>
      <div class="legend">金 / 木 / 水 / 火 / 土 出现次数。</div>
    </div>
  </div>

  <div class="grid2">
    <div class="panel">
      <h2><span class="dot"></span>④ 奇偶 & 区间</h2>
      <canvas id="parityChart" height="220"></canvas>
      <div class="legend" id="rangeLegend"></div>
    </div>
    <div class="panel">
      <h2><span class="dot"></span>⑤ 随机性检验（卡方拟合优度）</h2>
      <div id="chiBox" style="font-size:14px"></div>
      <div class="note">方法：对 49 个号码的全部 __SLOTS__ 个槽位做卡方检验，原假设"每个号码等概率出现"。</div>
    </div>
  </div>

  <div class="panel">
    <h2><span class="dot"></span>⑥ 冷热榜单 & 当前遗漏</h2>
    <div class="grid2">
      <div><b style="font-size:14px">🔥 高频（历史 Top10）</b>
        <table id="hotTable"></table></div>
      <div><b style="font-size:14px">❄️ 当前最冷（遗漏最大 Top10）</b>
        <table id="coldTable"></table></div>
    </div>
  </div>

  <div class="panel">
    <h2><span class="dot"></span>⑦ 共现 Top15（同期同现最频繁的两两组合）</h2>
    <table id="pairTable"></table>
    <div class="legend">"期望"=随机模型下两号同期的理论平均次数（__PAIR_EXP__）。</div>
  </div>

  <div class="panel">
    <h2><span class="dot"></span>🤖 ⑧ 推算智能体（可调参数，实时重算）</h2>
    <div class="controls">
      <label>统计窗口（近 N 期）
        <input type="range" id="win" min="10" max="200" value="50" step="5">
        <span id="winVal">50 期</span>
      </label>
      <label>权重·热度(Hot)
        <input type="range" id="wHot" min="0" max="100" value="40">
        <span id="wHotVal">40%</span></label>
      <label>权重·稳定(Stable)
        <input type="range" id="wSta" min="0" max="100" value="35">
        <span id="wStaVal">35%</span></label>
      <label>权重·遗漏(Due)
        <input type="range" id="wDue" min="0" max="100" value="25">
        <span id="wDueVal">25%</span></label>
      <button id="recompute">重新推算</button>
      <button id="genSets" class="ghost">生成参考组合</button>
    </div>
    <div class="filterbox" id="filterBox">
      <div class="grp" id="zodiacChks"><b style="font-size:13px">生肖：</b></div>
      <div class="grp" id="elementChks"><b style="font-size:13px">五行：</b></div>
      <button class="ghost" id="filterAll" style="padding:4px 10px">全选</button>
      <button class="ghost" id="filterClear" style="padding:4px 10px">清空筛选</button>
      <span class="note" id="filterNote"></span>
    </div>
    <div class="grid2">
      <div>
        <b style="font-size:14px">正码候选池 Top20 <span class="tag" id="mainFilterTag"></span></b>
        <div class="pool" id="mainPool"></div>
      </div>
      <div>
        <b style="font-size:14px">特码候选 Top12</b>
        <div class="pool" id="spPool"></div>
      </div>
    </div>
    <div class="sets" id="setsBox"></div>
    <div class="note">打分逻辑：热度=窗口内出现次数；稳定=历史总频次；遗漏=距上次出现的期数。三者归一化后按权重加权。仅供参考，不构成建议。</div>
    <details><summary>查看明细数据表</summary>
      <table id="predTable"></table></div>
    </details>
  </div>

  <div class="panel">
    <h2><span class="dot"></span>⑨ 逐年趋势（每年出现 Top5 号码）</h2>
    <div id="yearlyBox" style="font-size:13px"></div>
  </  div>
</div>

<script>
const DATA = __DATA__;
let currentRegion = DATA.regions_order[0];
let cur = DATA.regions[currentRegion];
const ZODIAC_COLORS = {"鼠":"#7f8c8d","牛":"#8d6e63","虎":"#e67e22","兔":"#ec407a",
  "龙":"#2980b9","蛇":"#16a34a","马":"#c0392b","羊":"#f1c40f","猴":"#d35400",
  "鸡":"#95a5a6","狗":"#34495e","猪":"#9b59b6"};
const NUMMAP = {};
DATA.numbers.forEach(n=>NUMMAP[n.num]=n);

let zodiacFilter = new Set();
let elementFilter = new Set();

function color(num){
  const z = NUMMAP[num].z_score;
  if(z>=0.5) return "#c0392b";
  if(z<=-0.5) return "#2c7be5";
  return "#95a5a6";
}
function zodiacOf(num){return NUMMAP[num].zodiac;}
function elementOf(num){return NUMMAP[num].element;}

/* ---------- 通用柱状图 ---------- */
function barChart(canvasId, labels, values, opts={}){
  const cv = document.getElementById(canvasId);
  const dpr = window.devicePixelRatio||1;
  const W = cv.clientWidth || 600, H = cv.height;
  cv.width = W*dpr; cv.height = H*dpr;
  const ctx = cv.getContext("2d"); ctx.scale(dpr,dpr);
  ctx.clearRect(0,0,W,H);
  const padL=38, padR=10, padT=14, padB=46;
  const plotW=W-padL-padR, plotH=H-padT-padB;
  const maxV = Math.max(...values)*1.05 || 1;
  // grid + y labels
  ctx.strokeStyle="#eee"; ctx.fillStyle="#9aa0a6"; ctx.font="11px sans-serif";
  for(let i=0;i<=4;i++){
    const y=padT+plotH*i/4; const v=maxV*(1-i/4);
    ctx.beginPath();ctx.moveTo(padL,y);ctx.lineTo(W-padR,y);ctx.stroke();
    ctx.fillText(v.toFixed(0),4,y+3);
  }
  const n=labels.length, bw=plotW/n;
  for(let i=0;i<n;i++){
    const v=values[i]; const bh=plotH*v/maxV;
    const x=padL+bw*i+bw*0.15, y=padT+plotH-bh, w=bw*0.7;
    ctx.fillStyle = opts.colorFn?opts.colorFn(labels[i],v):"#c0392b";
    ctx.fillRect(x,y,w,bh);
    if(opts.showLabels && (i%opts.labelStep===0 || opts.labelStep==1)){
      ctx.fillStyle="#6b7280";ctx.font="9px sans-serif";
      ctx.save();ctx.translate(x+w/2,y-2);ctx.rotate(-Math.PI/2);
      ctx.fillText(labels[i],-2,0);ctx.restore();
    }
  }
  // x caption
  ctx.fillStyle="#9aa0a6";ctx.font="11px sans-serif";
  ctx.fillText(opts.xCaption||"",padL,H-6);
  // optional expected line
  if(opts.expected){
    const y=padT+plotH-plotH*opts.expected/maxV;
    ctx.strokeStyle="#888";ctx.setLineDash([5,4]);
    ctx.beginPath();ctx.moveTo(padL,y);ctx.lineTo(W-padR,y);ctx.stroke();ctx.setLineDash([]);
  }
}

function drawFreqChart(){
  barChart("freqChart", DATA.numbers.map(n=>n.num), DATA.numbers.map(n=>n.freq_total),
    {colorFn:(l)=>{
        if(zodiacFilter.size===0 && elementFilter.size===0) return color(l);
        const n=NUMMAP[l];
        const okZ = zodiacFilter.size===0 || zodiacFilter.has(n.zodiac);
        const okE = elementFilter.size===0 || elementFilter.has(n.element);
        return (okZ&&okE)?color(l):"#e5e7eb";
      }, expected:DATA.meta.expected_per_number, showLabels:true, labelStep:1, xCaption:"号码 1–49"});
}

function renderAll(){
/* ---------- 渲染静态部分 ---------- */
document.getElementById("subline").textContent =
  `数据来源 ${DATA.meta.source} · 共 ${DATA.meta.total_draws} 期（${DATA.meta.first_issue} ~ ${DATA.meta.last_issue}）`;

const cards = [
  ["总期数", DATA.meta.total_draws],
  ["号码槽位", DATA.meta.total_slots],
  ["理论期望/号", DATA.meta.expected_per_number],
  ["卡方 p 值", DATA.chi_square.approx_p_value],
  ["最热号码", (()=>{const t=DATA.numbers.slice().sort((a,b)=>b.freq_total-a.freq_total)[0];return t.num+" ("+t.zodiac+")";})()],
  ["当前最冷", (()=>{const t=DATA.numbers.slice().sort((a,b)=>b.last_seen-a.last_seen)[0];return t.num+" 遗漏"+t.last_seen;})()],
];
const cardsBox=document.getElementById("cards");
cards.forEach(([k,v])=>{const d=document.createElement("div");d.className="card";
  d.innerHTML=`<div class="k">${k}</div><div class="v">${v}</div>`;cardsBox.appendChild(d);});

// ① 频率
drawFreqChart();

// ② 生肖
barChart("zodiacChart", DATA.zodiac.labels, DATA.zodiac.freq,
  {colorFn:(l)=>ZODIAC_COLORS[l]||"#999", showLabels:true,labelStep:1,xCaption:"生肖"});

// ③ 五行
barChart("elementChart", DATA.element.labels, DATA.element.freq,
  {colorFn:()=>"#16a34a", showLabels:true,labelStep:1,xCaption:"五行"});

// ④ 奇偶 & 区间
const pData=[DATA.parity.odd, DATA.parity.even];
barChart("parityChart", ["奇数","偶数"], pData,
  {colorFn:(l)=>l==="奇数"?"#c0392b":"#2c7be5", showLabels:true,labelStep:1,xCaption:"奇偶出现次数"});
document.getElementById("rangeLegend").innerHTML =
  "区间分布：" + DATA.ranges.map(r=>`${r.label}: <b>${r.freq}</b>`).join(" ｜ ");

// ⑤ 卡方
const chi=DATA.chi_square;
document.getElementById("chiBox").innerHTML =
  `χ² = <b>${chi.chi2}</b>，自由度 = ${chi.df}<br>`+
  `近似 p 值 = <b>${chi.approx_p_value}</b><br>`+
  `<span style="color:${chi.approx_p_value<0.05?'#c0392b':'#16a34a'}">`+
  `${chi.approx_p_value<0.05?'存在显著偏离':'未检出显著偏离 → 数据符合均匀随机'}
  </span><br><span class="note">${chi.note}</span>`;

// ⑥ 冷热
function tbl(rows, cols){
  let h="<tr>"+cols.map(c=>`<th>${c}</th>`).join("")+"</tr>";
  rows.forEach(r=>{h+="<tr>"+r.map((c,i)=>`<td>${c}</td>`).join("")+"</tr>";});
  return h;
}
const hot = DATA.numbers.slice().sort((a,b)=>b.freq_total-a.freq_total).slice(0,10);
document.getElementById("hotTable").innerHTML = tbl(
  hot.map(n=>[`<b>${n.num}</b>`,`${n.zodiac}/${n.element}`,n.freq_total,`z=${n.z_score}`]),
  ["号码","生肖/五行","总频次","z"]);
const cold = DATA.numbers.slice().sort((a,b)=>b.last_seen-a.last_seen).slice(0,10);
document.getElementById("coldTable").innerHTML = tbl(
  cold.map(n=>[`<b>${n.num}</b>`,`${n.zodiac}/${n.element}`,n.last_seen+"期",n.freq_total]),
  ["号码","生肖/五行","遗漏","总频次"]);

// ⑦ 共现
document.getElementById("pairTable").innerHTML = tbl(
  DATA.top_pairs.map(p=>[`${p.pair[0]} & ${p.pair[1]}`, p.count, p.expected]),
  ["组合","实际同现","理论期望"]);

// ⑨ 逐年
let yb="";
Object.keys(DATA.yearly).forEach(y=>{
  const arr=DATA.yearly[y].top.map(([num,c])=>`${num}(${c})`).join("，");
  yb+=`<div><b>${y}</b>（${DATA.yearly[y].draws}期）：${arr}</div>`;
});
document.getElementById("yearlyBox").innerHTML=yb;
  recompute();
  renderHistory();
}

/* ---------- ⑧ 推算智能体（可重算） ---------- */
function recompute(){
  const win=+document.getElementById("win").value;
  document.getElementById("winVal").textContent=win+" 期";
  const wHot=+document.getElementById("wHot").value/100;
  const wSta=+document.getElementById("wSta").value/100;
  const wDue=+document.getElementById("wDue").value/100;
  document.getElementById("wHotVal").textContent=Math.round(wHot*100)+"%";
  document.getElementById("wStaVal").textContent=Math.round(wSta*100)+"%";
  document.getElementById("wDueVal").textContent=Math.round(wDue*100)+"%";

  // 窗口内计数
  const recent={}, recentSp={};
  DATA.draws.slice(-win).forEach(d=>{
    d[2].forEach(m=>recent[m]=(recent[m]||0)+1);     // mains
    d[2].forEach(m=>{});                             // ignore
    recent[d[3]]=(recent[d[3]]||0)+1;                // include special in all7
    recentSp[d[3]]=(recentSp[d[3]]||0)+1;
  });
  const nums=DATA.numbers;
  const norm=(arr)=>{const vs=Object.values(arr);const lo=Math.min(...vs),hi=Math.max(...vs);
    const o={};for(const k in arr)o[k]=hi===lo?50:100*(arr[k]-lo)/(hi-lo);return o;};
  const hotN=norm(Object.fromEntries(nums.map(n=>[n.num,recent[n.num]||0])));
  const staN=norm(Object.fromEntries(nums.map(n=>[n.num,n.freq_total])));
  const dueN=norm(Object.fromEntries(nums.map(n=>[n.num,n.last_seen])));
  const spSta=norm(Object.fromEntries(nums.map(n=>[n.num,n.freq_special])));
  const spHot=norm(Object.fromEntries(nums.map(n=>[n.num,recentSp[n.num]||0])));
  const spDue=norm(Object.fromEntries(nums.map(n=>[n.num,n.last_special_seen])));

  // 按权重线性组合后, 再归一化到 0-100
  const rawMain={}, rawSp={};
  nums.forEach(n=>{
    rawMain[n.num]=wHot*hotN[n.num]+wSta*staN[n.num]+wDue*dueN[n.num];
    rawSp[n.num] =wHot*spHot[n.num]+wSta*spSta[n.num]+wDue*spDue[n.num];
  });
  const nrm=(obj)=>{const vs=Object.values(obj);const lo=Math.min(...vs),hi=Math.max(...vs);
    const o={};for(const k in obj)o[k]=hi===lo?50:100*(obj[k]-lo)/(hi-lo);return o;};
  const mainS=nrm(rawMain), spS=nrm(rawSp);

  const mainRank=nums.map(n=>n.num).sort((a,b)=>mainS[b]-mainS[a]).slice(0,20);
  const spRank=nums.map(n=>n.num).sort((a,b)=>spS[b]-spS[a]).slice(0,12);

  // 生肖/五行筛选
  const passes=n=>{const z=NUMMAP[n];return (zodiacFilter.size===0||zodiacFilter.has(z.zodiac))&&(elementFilter.size===0||elementFilter.has(z.element));};
  const mR=mainRank.filter(passes), sR=spRank.filter(passes);
  const ftag=(zodiacFilter.size||elementFilter.size)?("已筛选"):"";
  document.getElementById("mainFilterTag").textContent=ftag;

  const pool=document.getElementById("mainPool"); pool.innerHTML="";
  mR.forEach(num=>{
    const d=document.createElement("div");d.className="ball";
    d.style.background=color(num);
    d.title=`${num} ${zodiacOf(num)}/${elementOf(num)}｜总分${mainS[num].toFixed(1)}｜历史${NUMMAP[num].freq_total}｜近${win}期${recent[num]||0}｜遗漏${NUMMAP[num].last_seen}`;
    d.textContent=num;pool.appendChild(d);
  });
  const sp=document.getElementById("spPool"); sp.innerHTML="";
  sR.forEach(num=>{
    const d=document.createElement("div");d.className="ball";
    d.style.background="#8e44ad";
    d.title=`${num}｜特码分${spS[num].toFixed(1)}｜特码历史${NUMMAP[num].freq_special}｜近${win}期特${recentSp[num]||0}`;
    d.textContent=num;sp.appendChild(d);
  });

  // 明细表
  const pt=document.getElementById("predTable");
  let h="<tr><th>正码排名</th><th>号码</th><th>生肖/五行</th><th>综合分</th><th>历史</th>"+
        "<th>近"+win+"期</th><th>遗漏</th></tr>";
  mR.forEach((num,i)=>{
    const n=NUMMAP[num];
    h+=`<tr><td>${i+1}</td><td><b>${num}</b></td><td>${n.zodiac}/${n.element}</td>`+
       `<td>${mainS[num].toFixed(1)}</td><td>${n.freq_total}</td><td>${recent[num]||0}</td><td>${n.last_seen}</td></tr>`;
  });
  pt.innerHTML=h;
  window.__spRank=sR; window.__mainRank=mR;
  window.__mainS=mainS; window.__spS=spS;
}

/* 生成参考组合：从正码池按分数加权随机抽6，特码池抽1 */
function genSets(){
  const main=window.__mainRank||[];
  const box=document.getElementById("setsBox"); box.innerHTML="";
  if(!main.length){recompute();}
  for(let s=0;s<6;s++){
    const pickMain=weightedPick(window.__mainRank, 6, window.__mainS);
    const pickSp=weightedPick(window.__spRank, 1, window.__spS)[0];
    const div=document.createElement("div");div.className="set";
    div.innerHTML=`组合${s+1}：正码 <b>${pickMain.join(" ")}</b> ｜ 特码 <b>${pickSp}</b>`;
    box.appendChild(div);
  }
  box.insertAdjacentHTML("beforeend",
    `<div class="note">⚠️ 以上为按分数加权的随机抽样，仅用于演示"如何组合"，<b>不代表任何中奖预测</b>。</div>`);
}
function weightedPick(pool, k, scoreMap){
  const arr=[...pool]; const res=[];
  while(res.length<k && arr.length){
    const ws=arr.map(n=>Math.max(1,scoreMap[n]||1)); const sum=ws.reduce((a,b)=>a+b,0);
    let r=Math.random()*sum, idx=0;
    for(;idx<arr.length;idx++){r-=ws[idx]; if(r<=0)break;}
    res.push(arr.splice(idx,1)[0]);
  }
  return res;
}

["win","wHot","wSta","wDue"].forEach(id=>
  document.getElementById(id).addEventListener("input",recompute));
document.getElementById("recompute").addEventListener("click",recompute);
document.getElementById("genSets").addEventListener("click",genSets);
document.getElementById("genPairs").addEventListener("click",genPairs);
document.getElementById("genTriples").addEventListener("click",genTriples);
function genTriples(){
  const main=window.__mainRank||[];
  const box=document.getElementById("triplesBox"); box.innerHTML="";
  if(!main.length){recompute();}
  for(let s=0;s<20;s++){
    const t=weightedPick(window.__mainRank, 3, window.__mainS).sort((a,b)=>a-b);
    const div=document.createElement("div");div.className="pairset";
    const zs=t.map(n=>zodiacOf(n)+"/"+elementOf(n)).join(" · ");
    div.innerHTML=`组${s+1}：<b>${t[0]} ${t[1]} ${t[2]}</b><span>${zs}</span>`;
    box.appendChild(div);
  }
  box.insertAdjacentHTML("beforeend",
    `<div class="note" style="flex-basis:100%">⚠️ 以上为按综合分加权的随机抽样，仅用于演示"如何选三码"，<b>不代表任何中奖预测</b>。建议配合 ⑩ 模块做历史回测。</div>`);
}
function genPairs(){
  const main=window.__mainRank||[];
  const box=document.getElementById("pairsBox"); box.innerHTML="";
  if(!main.length){recompute();}
  for(let s=0;s<10;s++){
    const pair=weightedPick(window.__mainRank, 2, window.__mainS).sort((a,b)=>a-b);
    const div=document.createElement("div");div.className="pairset";
    const z0=zodiacOf(pair[0])+"/"+elementOf(pair[0]);
    const z1=zodiacOf(pair[1])+"/"+elementOf(pair[1]);
    div.innerHTML=`组${s+1}：<b>${pair[0]} ${pair[1]}</b><span>${z0} · ${z1}</span>`;
    box.appendChild(div);
  }
  box.insertAdjacentHTML("beforeend",
    `<div class="note" style="flex-basis:100%">⚠️ 以上为按综合分加权的随机抽样，仅用于演示"如何选二码"，<b>不代表任何中奖预测</b>。建议配合 ⑩ 模块对不同选号做历史回测。</div>`);
}

// ---------- 地区切换 ----------
const tabsBox=document.getElementById("regionTabs");
function switchRegion(r){
  currentRegion=r; cur=DATA.regions[r]; rebuildNUM();
  zodiacFilter.clear(); elementFilter.clear();
  document.querySelectorAll("#zodiacChks input,#elementChks input").forEach(c=>c.checked=false);
  document.getElementById("filterNote").textContent="";
  renderAll();
}
DATA.regions_order.forEach(r=>{
  const b=document.createElement("button");
  b.className="rtab"+(r===currentRegion?" on":""); b.textContent=r;
  b.onclick=()=>{ document.querySelectorAll(".rtab").forEach(x=>x.classList.remove("on"));
    b.classList.add("on"); switchRegion(r); };
  tabsBox.appendChild(b);
});
renderAll();
window.addEventListener("resize",()=>{
  drawFreqChart();
  barChart("zodiacChart", DATA.zodiac.labels, DATA.zodiac.freq,{colorFn:l=>ZODIAC_COLORS[l]||"#999",showLabels:true,labelStep:1,xCaption:"生肖"});
  barChart("elementChart", DATA.element.labels, DATA.element.freq,{colorFn:()=>"#16a34a",showLabels:true,labelStep:1,xCaption:"五行"});
  barChart("parityChart",["奇数","偶数"],pData,{colorFn:l=>l==="奇数"?"#c0392b":"#2c7be5",showLabels:true,labelStep:1,xCaption:"奇偶"});
});

/* ---------- 生肖/五行筛选 ---------- */
function buildFilterChecks(){
  const zc=document.getElementById("zodiacChks");
  DATA.zodiac.labels.forEach(z=>{
    const lab=document.createElement("label"); lab.className="chk";
    lab.innerHTML=`<input type="checkbox" value="${z}">${z}`;
    lab.querySelector("input").onchange=e=>{if(e.target.checked)zodiacFilter.add(z);else zodiacFilter.delete(z);onFilterChange();};
    zc.appendChild(lab);
  });
  const ec=document.getElementById("elementChks");
  DATA.element.labels.forEach(e2=>{
    const lab=document.createElement("label"); lab.className="chk";
    lab.innerHTML=`<input type="checkbox" value="${e2}">${e2}`;
    lab.querySelector("input").onchange=ev=>{if(ev.target.checked)elementFilter.add(e2);else elementFilter.delete(e2);onFilterChange();};
    ec.appendChild(lab);
  });
}
function onFilterChange(){
  drawFreqChart(); recompute(); renderHistory();
  const parts=[];
  if(zodiacFilter.size)parts.push("生肖 "+[...zodiacFilter].join(","));
  if(elementFilter.size)parts.push("五行 "+[...elementFilter].join(","));
  document.getElementById("filterNote").textContent = parts.length?("已筛选："+parts.join(" ｜ ")):"";
}
document.getElementById("filterAll").onclick=()=>{
  document.querySelectorAll("#zodiacChks input,#elementChks input").forEach(c=>{c.checked=true;});
  zodiacFilter=new Set(DATA.zodiac.labels); elementFilter=new Set(DATA.element.labels); onFilterChange();
};
document.getElementById("filterClear").onclick=()=>{
  document.querySelectorAll("#zodiacChks input,#elementChks input").forEach(c=>{c.checked=false;});
  zodiacFilter.clear(); elementFilter.clear(); onFilterChange();
};

/* ---------- 历史开奖记录 ---------- */
function numCell(num, isSpecial){
  const n=NUMMAP[num];
  let cls="mball"+(isSpecial?" sp":"");
  // 生肖/五行筛选：命中保留彩色，否则置灰
  if((zodiacFilter.size||elementFilter.size)){
    const okZ=zodiacFilter.size===0||zodiacFilter.has(n.zodiac);
    const okE=elementFilter.size===0||elementFilter.has(n.element);
    if(!(okZ&&okE)) cls+=" dim";
  }
  return `<span class="${cls}" style="background:${color(num)}" title="${num} ${n.zodiac}/${n.element}">${num}<small>${n.zodiac}</small></span>`;
}
function renderHistory(){
  const q=(document.getElementById("histSearch").value||"").trim();
  const lim=parseInt(document.getElementById("histLimit").value,10)||0;
  const tbody=document.getElementById("histBody"); tbody.innerHTML="";
  // 倒序（最新在上）
  const rows=[...DATA.draws].reverse();
  const shown = lim>0 ? rows.slice(0,lim) : rows;
  let cnt=0;
  shown.forEach(r=>{
    const year=r[0], issue=r[1], mains=r[2], sp=r[3];
    // 搜索过滤：期号包含 或 任意号码包含
    if(q){
      const hitIssue=String(issue).includes(q);
      const hitNum=mains.some(m=>String(m).includes(q)) || String(sp).includes(q);
      if(!hitIssue && !hitNum) return;
    }
    const tr=document.createElement("tr");
    tr.innerHTML=`<td><b>${issue}</b></td><td>${year}</td>`+
      `<td>${mains.map(m=>numCell(m,false)).join("")}</td>`+
      `<td>${numCell(sp,true)}</td>`;
    tbody.appendChild(tr);
    cnt++;
  });
  document.getElementById("histCount").textContent=cnt;
}
document.getElementById("histSearch").addEventListener("input",renderHistory);
document.getElementById("histLimit").addEventListener("change",renderHistory);

/* ---------- 选号收益回测 ---------- */
let myPicks=new Set();
function buildPickGrid(){
  const g=document.getElementById("pickGrid"); g.innerHTML="";
  for(let i=1;i<=49;i++){
    const b=document.createElement("button"); b.className="pickbtn"; b.textContent=i;
    b.title=`${i} ${NUMMAP[i].zodiac}/${NUMMAP[i].element}`;
    b.onclick=()=>{ if(myPicks.has(i)){myPicks.delete(i);b.classList.remove("on");}else{myPicks.add(i);b.classList.add("on");} updatePickCount(); };
    g.appendChild(b);
  }
}
function updatePickCount(){document.getElementById("pickCount").textContent=`已选 ${myPicks.size} 个号码`; }
function syncPickGrid(){document.querySelectorAll("#pickGrid .pickbtn").forEach(b=>{const n=+b.textContent;b.classList.toggle("on",myPicks.has(n));});}
document.getElementById("pickFromFilter").onclick=()=>{
  const sel=new Set();
  DATA.numbers.forEach(n=>{const okZ=zodiacFilter.size===0||zodiacFilter.has(n.zodiac);const okE=elementFilter.size===0||elementFilter.has(n.element);if(okZ&&okE)sel.add(n.num);});
  myPicks=sel; syncPickGrid(); updatePickCount();
};
document.getElementById("pickClear").onclick=()=>{myPicks=new Set();syncPickGrid();updatePickCount();};
function buildOdds(){
  const row=document.getElementById("oddsRow"); row.innerHTML="<b style='font-size:13px'>赔率(倍)：</b>";
  const def={0:0,1:0,2:65,3:650,4:0,5:0,6:0};
  for(let k=0;k<=6;k++){
    const lbl=document.createElement("label"); lbl.textContent=`中${k}`;
    const inp=document.createElement("input"); inp.type="number"; inp.value=def[k]; inp.id="odds"+k; inp.min="0";
    lbl.appendChild(inp); row.appendChild(lbl);
  }
}
document.getElementById("calcEV").onclick=()=>{
  if(myPicks.size===0){document.getElementById("evBox").innerHTML="<span class='cold'>请先选择号码</span>";return;}
  const odds=[]; for(let k=0;k<=6;k++) odds[k]=+(document.getElementById("odds"+k).value||0);
  const tally=new Array(7).fill(0);
  DATA.draws.forEach(d=>{ let hit=0; d[2].forEach(m=>{if(myPicks.has(m))hit++;}); if(hit>6)hit=6; tally[hit]++; });
  const total=DATA.draws.length;
  let ev=0;
  let rows="<tr><th>命中个数</th>"+[0,1,2,3,4,5,6].map(k=>`<th>中${k}</th>`).join("")+"</tr>";
  rows+="<tr><td>历史次数</td>"+tally.map(t=>`<td>${t}</td>`).join("")+"</tr>";
  rows+="<tr><td>命中率</td>"+tally.map(t=>`<td>${(t/total*100).toFixed(2)}%</td>`).join("")+"</tr>";
  rows+="<tr><td>赔率(倍)</td>"+odds.map(o=>`<td>${o}</td>`).join("")+"</tr>";
  tally.forEach((t,k)=>{ev+=(t/total)*odds[k];});
  document.getElementById("evBox").innerHTML=
    `<table style="margin-bottom:8px">${rows}</table>`+
    `选号：[${[...myPicks].sort((a,b)=>a-b).join(" ")}]（共 ${myPicks.size} 个，仅统计 6 平码）<br>`+
    `历史期望回收 = <b>${ev.toFixed(3)}</b> 倍本金 ｜ 净期望 = <b>${(ev-1).toFixed(3)}</b> 倍`+
    `<div class="note">⚠️ 这是基于历史命中率的回测，并非真实概率；真实赔率内含庄家优势，且每期独立随机，请勿据此投注。</div>`;
};

buildFilterChecks();
buildPickGrid();
buildOdds();
updatePickCount();
</script>
</body>
</html>
"""

html = HTML.replace("__DATA__", DATA_JS)
# 顶层 meta 已移至 regions[地区]；占位符在模板中未实际使用，这里用首地区安全取值以防 KeyError
first_region = data["regions"][data["regions_order"][0]]
html = html.replace("__TOTAL__", str(first_region["meta"]["total_draws"]))
html = html.replace("__EXP__", str(first_region["meta"]["expected_per_number"]))
html = html.replace("__SLOTS__", str(first_region["meta"]["total_slots"]))
html = html.replace("__PAIR_EXP__", str(round(first_region["top_pairs"][0]["expected"], 1)) if first_region["top_pairs"] else "—")

out = os.path.join(HERE, "index.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("已生成 ->", out, "大小", len(html), "字节")
