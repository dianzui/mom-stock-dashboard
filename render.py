#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「可自更新」的适老化看板 dashboard.html
- 打开即显示预生成数据（不联网也能看）
- 页面上点「更新数据」，浏览器自己用 JSONP 拉最新数据并重绘
"""
import json, os, datetime, html

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")

def load(name, default=None):
    p = os.path.join(DATA, name)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}

def esc(s):
    return html.escape(str(s if s is not None else ""))

def _f(v):
    try:
        x = float(v)
        return None if x != x else x
    except Exception:
        return None

def pct(v, d=2):
    x = _f(v)
    if x is None: return '<span class="gray">—</span>'
    return '<span class="%s">%+.*f%%</span>' % ("red" if x > 0 else ("green" if x < 0 else "gray"), d, x)

def plain(v, d=2):
    x = _f(v)
    return '<span class="gray">—</span>' if x is None else ('%.*f' % (d, x))

def big_pct(v, d=2):
    x = _f(v)
    if x is None: return '<div class="big-num gray">—</div>'
    c = "red" if x > 0 else ("green" if x < 0 else "gray")
    return '<div class="big-num %s">%+.*f%%</div>' % (c, d, x)

def grade(w):
    np_yoy = _f(w.get("np_yoy")); rev = _f(w.get("rev_yoy"))
    pe = _f(w.get("pe")); np_ = _f(w.get("np"))
    if np_yoy is None: return "unknown"
    if (np_ is not None and np_ < 0) or np_yoy < 0 or (pe is not None and pe < 0):
        return "avoid"
    if np_yoy > 20 and (rev if rev is not None else -1) > 0 and (pe is None or pe < 50):
        return "good"
    return "watch"


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:"Microsoft YaHei","微软雅黑","PingFang SC","Heiti SC",sans-serif;
background:#eef1f6;color:#1a1f2b;font-size:21px;line-height:1.75}
.wrap{max-width:1240px;margin:0 auto;padding:0 20px 70px}
header{background:linear-gradient(135deg,#16233d,#2b4670);color:#fff;padding:30px 0 26px;margin-bottom:16px}
header .wrap{padding-bottom:0}
header h1{font-size:37px;font-weight:800}
.datebar{margin-top:12px;font-size:23px;font-weight:700;background:rgba(255,255,255,.15);
display:inline-block;padding:10px 22px;border-radius:12px}
.datebar b{color:#ffd35c}
.stale{margin-top:12px;background:#b8451f;padding:12px 20px;border-radius:10px;font-size:19px;font-weight:700}
.updbar{background:#fff;border-radius:18px;padding:22px 24px;margin-bottom:16px;
box-shadow:0 3px 14px rgba(20,35,65,.08);display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.updbtn{flex:1;min-width:290px;border:none;background:linear-gradient(135deg,#1e8449,#27ae60);color:#fff;
padding:28px 30px;border-radius:16px;font-size:29px;font-weight:900;cursor:pointer;font-family:inherit;
box-shadow:0 6px 18px rgba(30,132,73,.35)}
.updbtn:hover{transform:translateY(-2px)}
.updbtn:disabled{background:#9aa5b8;box-shadow:none;cursor:default}
.updstat{flex:1.5;min-width:280px;font-size:19px;color:#4a5568;line-height:1.7}
.updstat b{color:#16233d}
.bar{height:14px;background:#e3e9f3;border-radius:8px;overflow:hidden;margin-top:10px}
.bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,#27ae60,#2ecc71);transition:.3s}
.tabs{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap}
.tabs button{flex:1;min-width:190px;border:none;background:#fff;color:#33415c;padding:22px 10px;
border-radius:14px;font-size:23px;font-weight:800;cursor:pointer;font-family:inherit;
box-shadow:0 2px 8px rgba(20,35,65,.10)}
.tabs button.on{background:#2b4670;color:#fff}
section{display:none} section.on{display:block}
.card{background:#fff;border-radius:18px;padding:26px 28px;margin-bottom:20px;box-shadow:0 3px 14px rgba(20,35,65,.07)}
.card h2{font-size:28px;font-weight:800;margin-bottom:14px;color:#16233d}
.card h3{font-size:23px;font-weight:800;margin:26px 0 10px;color:#2b4670}
.verdict{font-size:25px;font-weight:800;padding:18px 24px;border-radius:12px;margin:16px 0}
.upbox{background:#eaf6ee;color:#1e8449;border-left:8px solid #1e8449}
.downbox{background:#fdeceb;color:#c0392b;border-left:8px solid #c0392b}
.flatbox{background:#f3f4f7;color:#556;border-left:8px solid #8892a6}
.advice{font-size:21px;color:#2d3548;background:#f7f9fd;padding:18px 22px;border-radius:12px;line-height:1.8}
.note{font-size:18.5px;color:#525c6e;background:#f7f9fd;border-left:5px solid #a9b6cd;
padding:15px 20px;border-radius:10px;margin:14px 0;line-height:1.8}
.note b{color:#16233d}
.warn{background:#fff6e8;border-left-color:#e08b28;color:#7a4d0f}
.idxrow{display:flex;gap:14px;flex-wrap:wrap}
.idxbox{flex:1;min-width:170px;background:#f6f8fc;border-radius:14px;padding:18px 12px;text-align:center}
.idxname{font-size:19px;color:#66718a;font-weight:700}
.idxprice{font-size:32px;font-weight:800;margin:6px 0 2px}
.idxchg{font-size:23px;font-weight:800}
.breadth{margin-top:22px;font-size:22px;display:flex;gap:30px;flex-wrap:wrap;align-items:center;font-weight:700}
.breadth .n{font-size:30px;font-weight:900}
.pickcard{display:flex;gap:18px;align-items:center;background:#fbfcfe;border:2px solid #e2e8f4;
border-radius:16px;padding:20px 22px;margin-bottom:14px}
.pc-rank{font-size:38px;font-weight:900;color:#c3ccdd;width:50px;text-align:center}
.pc-main{flex:1;min-width:0}
.pc-name{font-size:29px;font-weight:800}
.pc-code{font-size:18px;color:#8d97ab;font-weight:600;margin-left:10px}
.pc-nums{display:flex;align-items:baseline;gap:24px;margin-top:2px;flex-wrap:wrap}
.pc-price{font-size:32px;font-weight:800;color:#16233d}
.big-num{font-size:32px;font-weight:900}
.pc-why{font-size:18.5px;color:#4a5568;margin-top:6px;line-height:1.7}
.pc-side{text-align:right;flex-shrink:0;min-width:150px}
.pc-flow{font-size:18px;color:#4a5568;line-height:1.5}
.pc-flow b{font-size:25px}
.pc-extra{font-size:16.5px;color:#7d8798;margin-top:4px}
table{width:100%;border-collapse:collapse;font-size:19.5px;margin-top:8px}
th{background:#eaf0f9;color:#33415c;font-weight:800;text-align:left;padding:14px 11px;
font-size:18.5px;border-bottom:3px solid #cfd9ea;white-space:nowrap}
td{padding:14px 11px;border-bottom:1px solid #e8edf5}
tbody tr:nth-child(odd) td{background:#fafcff}
.rank{color:#9aa5b8;font-weight:800;width:42px;text-align:center}
.bname{font-weight:800;white-space:nowrap}
.code{display:block;font-size:15.5px;color:#9aa5b8;font-weight:500}
.mono{font-variant-numeric:tabular-nums;font-weight:700}
.c{text-align:center}
.small{font-size:16.5px;color:#5d6779;line-height:1.6}
.seat{font-size:17.5px;line-height:1.5;font-weight:600}
.red{color:#c0392b} .green{color:#1e8449} .gray{color:#8d97ab}
.group{margin-bottom:24px}
.gtitle{font-size:25px;font-weight:900;padding:14px 22px;border-radius:12px;margin-bottom:6px;
display:flex;justify-content:space-between;align-items:center}
.g-good{background:#eaf6ee;color:#126b39}
.g-watch{background:#fff6e8;color:#8a5a10}
.g-avoid{background:#fdeceb;color:#a72c1e}
.gcount{font-size:20px;font-weight:800;opacity:.85}
.emptybox{padding:24px;text-align:center;color:#9aa5b8;font-size:19px}
.footer{text-align:center;color:#8d97ab;font-size:16.5px;margin-top:26px;line-height:2}
@media (max-width:760px){
  body{font-size:19px} header h1{font-size:29px}
  .tabs button{min-width:46%;font-size:20px;padding:18px 8px}
  .card{padding:18px 14px} .pickcard{flex-direction:column;align-items:flex-start}
  .pc-side{text-align:left} .idxbox{min-width:46%}
  .updbtn{font-size:24px;padding:22px 16px}
}
"""

JS = """
var DATA = __INIT__;
var _seq = 0;
function jsonp(url, timeout){
  return new Promise(function(resolve, reject){
    var cb = 'jp' + (++_seq) + '_' + Date.now();
    var s = document.createElement('script');
    var timer = setTimeout(function(){ done(); reject(new Error('超时')); }, timeout || 15000);
    function done(){ clearTimeout(timer); if(s.parentNode) s.parentNode.removeChild(s); try{delete window[cb];}catch(e){} }
    window[cb] = function(d){ done(); resolve(d); };
    s.onerror = function(){ done(); reject(new Error('加载失败')); };
    s.src = url.replace('__CB__', cb);
    document.head.appendChild(s);
  });
}
var EM = 'https://push2.eastmoney.com/api/qt/';
var DC = 'https://datacenter-web.eastmoney.com/api/data/v1/get';
function num(v){ var x = parseFloat(v); return isNaN(x) ? null : x; }
function f2(v,d){ var x = num(v); return x===null?'—':x.toFixed(d===undefined?2:d); }
function pctHtml(v,d){
  var x = num(v); if(x===null) return '<span class="gray">—</span>';
  var c = x>0?'red':(x<0?'green':'gray');
  return '<span class="'+c+'">'+(x>0?'+':'')+x.toFixed(d===undefined?2:d)+'%</span>';
}
function bigPct(v){
  var x = num(v); if(x===null) return '<div class="big-num gray">—</div>';
  var c = x>0?'red':(x<0?'green':'gray');
  return '<div class="big-num '+c+'">'+(x>0?'+':'')+x.toFixed(2)+'%</div>';
}
function setBar(p){ document.getElementById('barFill').style.width = Math.max(0,Math.min(100,p))+'%'; }
function msg(a,b){
  document.getElementById('updMsg').innerHTML = a;
  if(b!==undefined) document.getElementById('updSub').textContent = b;
}

async function doUpdate(){
  var btn = document.getElementById('btnUpdate');
  btn.disabled = true; btn.textContent = '正在更新，请稍等…';
  setBar(3);
  try{
    msg('① 正在获取大盘指数…');
    var m = await jsonp(EM+'ulist.np/get?cb=__CB__&fltt=2&invt=2&fields=f2,f3,f12,f14&secids=1.000001,0.399001,0.399006,1.000688,1.000300');
    var idxs = (m.data&&m.data.diff)||[];
    var html = '';
    idxs.forEach(function(x){
      var c = num(x.f3), cl = c>0?'red':(c<0?'green':'gray');
      html += '<div class="idxbox"><div class="idxname">'+x.f14+'</div><div class="idxprice '+cl+'">'
            + f2(x.f2)+'</div><div class="idxchg '+cl+'">'+(c>0?'+':'')+f2(c)+'%</div></div>';
    });
    if(html) document.getElementById('idxRow').innerHTML = html;
    setBar(14);

    var all = [];
    for(var p=1;p<=5;p++){
      msg('② 正在扫描全市场股票（第 '+p+'/5 页）…');
      var u = EM+'clist/get?cb=__CB__&pn='+p+'&pz=100&po=0&np=1&fltt=2&invt=2&fid=f109'
            + '&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23'
            + '&fields=f12,f14,f2,f3,f109,f62,f184,f8,f10,f6';
      var d = await jsonp(u);
      var rows = (d.data&&d.data.diff)||[];
      if(!rows.length) break;
      all = all.concat(rows);
      setBar(14+p*9);
      if(rows.length < 100) break;
    }
    var cand = all.filter(function(x){
      var r5 = num(x.f109), net = num(x.f62), vr = num(x.f10), amt = num(x.f6);
      var nm = x.f14||'';
      if(r5===null || r5 > -8) return false;
      if(net===null || net <= 0) return false;
      if(nm.indexOf('ST')>=0 || nm.indexOf('退')>=0) return false;
      if(amt!==null && amt < 1e8) return false;
      return true;
    });
    cand.sort(function(a,b){ return num(b.f62)-num(a.f62); });
    setBar(64);
    msg('③ 正在读取龙虎榜席位…');

    var seatArr = null;
    try{
      var lb = await jsonp(DC+'?callback=__CB__&reportName=RPT_BILLBOARD_DAILYDETAILSBUY'
        + '&columns=SECURITY_CODE,TRADE_DATE,OPERATEDEPT_NAME,BUY'
        + '&pageNumber=1&pageSize=500&sortColumns=TRADE_DATE&sortTypes=-1&source=WEB&client=WEB');
      if(lb && lb.result && lb.result.data){
        var agg = {};
        lb.result.data.forEach(function(s){
          var n = s.OPERATEDEPT_NAME; if(!n) return;
          var a = agg[n] || (agg[n]={seat:n,times:0,buy:0});
          a.times++; a.buy += num(s.BUY)||0;
        });
        seatArr = Object.keys(agg).map(function(k){ return agg[k]; });
        seatArr.sort(function(a,b){ return b.times-a.times; });
        seatArr = seatArr.slice(0,12);
      }
    }catch(e){}
    setBar(82);
    msg('④ 正在刷新 24 只自选股价格…');

    var secids = DATA.watch.map(function(w){ return (w.code[0]==='6'?'1.':'0.')+w.code; }).join(',');
    var q = await jsonp(EM+'ulist.np/get?cb=__CB__&fltt=2&invt=2&fields=f2,f3,f12&secids='+secids);
    var qmap = {};
    ((q.data&&q.data.diff)||[]).forEach(function(x){ qmap[x.f12]=x; });
    DATA.watch.forEach(function(w){
      if(qmap[w.code]){ w.price = qmap[w.code].f2; w.chg = qmap[w.code].f3; }
    });
    setBar(94);

    DATA.picks = cand.slice(0,15).map(function(x){
      return {code:x.f12, name:x.f14, close:x.f2, r5:x.f109,
              net3: num(x.f62)/1e8, vol_ratio:x.f10, turn:x.f8};
    });
    if(seatArr){
      DATA.seats = seatArr.map(function(a){
        return {seat:a.seat, times:a.times, buy:a.buy/1e8, win5:null, avg5:null};
      });
    }
    redrawAll();
    var now = new Date();
    document.getElementById('dateTxt').textContent =
      now.getFullYear()+'年'+(now.getMonth()+1)+'月'+now.getDate()+'日（刚刚更新）';
    document.getElementById('staleBox').innerHTML = '';
    document.getElementById('updSub').textContent = '最后更新：' + now.toLocaleTimeString('zh-CN');
    setBar(100);
    msg('✅ 更新完成！下面的内容已经是最新的。');
  }catch(e){
    setBar(0);
    msg('⚠ 更新失败：'+e.message+'<br>可能是网络不好。下面的内容还是上次的，可以先看，过一会儿再试。');
  }finally{
    btn.disabled = false; btn.textContent = '🔄 更新数据';
  }
}

function redrawAll(){
  var cards='', rest='';
  DATA.picks.slice(0,5).forEach(function(x,i){
    var net = num(x.net3)||0;
    var reason = '最近 5 天跌了 '+Math.abs(num(x.r5)||0).toFixed(1)+'%，但今天主力资金净流入 '
               + net.toFixed(2)+' 亿，成交量也在放大——跌的时候有人接货。';
    cards += '<div class="pickcard"><div class="pc-rank">'+(i+1)+'</div><div class="pc-main">'
      + '<div class="pc-name">'+x.name+'<span class="pc-code">'+x.code+'</span></div>'
      + '<div class="pc-nums"><span class="pc-price">'+f2(x.close)+'</span>'+bigPct(x.r5)+'</div>'
      + '<div class="pc-why">'+reason+'</div></div>'
      + '<div class="pc-side"><div class="pc-flow">今日主力<br><b class="'+(net>0?'red':'green')+'">'
      + (net>0?'+':'')+net.toFixed(2)+' 亿</b></div>'
      + '<div class="pc-extra">量比 '+f2(x.vol_ratio)+'　换手 '+f2(x.turn)+'%</div></div></div>';
  });
  DATA.picks.slice(5).forEach(function(x,i){
    var net = num(x.net3)||0;
    rest += '<tr><td class="rank">'+(i+6)+'</td><td class="bname">'+x.name
      + '<span class="code">'+x.code+'</span></td><td class="mono">'+f2(x.close)+'</td><td>'
      + pctHtml(x.r5)+'</td><td class="mono '+(net>0?'red':'green')+'">'+net.toFixed(2)
      + ' 亿</td><td>'+f2(x.vol_ratio)+'</td></tr>';
  });
  if(cards) document.getElementById('pickCards').innerHTML = cards;
  if(rest) document.getElementById('pickRest').innerHTML = rest;

  var st='';
  DATA.seats.forEach(function(s){
    st += '<tr><td class="seat">'+s.seat+'</td><td class="c">'+s.times+'</td><td class="c">'
      + f2(s.buy)+' 亿</td><td class="c gray">'+(s.win5===null?'—':f2(s.win5,1)+'%')
      + '</td><td class="c">'+(s.avg5===null?'—':pctHtml(s.avg5))+'</td></tr>';
  });
  if(st) document.getElementById('seatBody').innerHTML = st;

  var g = {good:[], watch:[], avoid:[]};
  DATA.watch.forEach(function(w){
    var npy=num(w.np_yoy), pe=num(w.pe), npv=num(w.np), k='watch';
    if(npy===null) k='watch';
    else if((npv!==null&&npv<0)||npy<0||(pe!==null&&pe<0)) k='avoid';
    else if(npy>20 && (num(w.rev_yoy)||0)>0 && (pe===null||pe<50)) k='good';
    g[k].push(w);
  });
  Object.keys(g).forEach(function(k){
    var tb = document.getElementById('tb-'+k); if(!tb) return;
    var h='';
    g[k].forEach(function(w){
      h += '<tr><td class="bname">'+w.name+'<span class="code">'+w.code+'</span></td>'
        + '<td class="mono">'+f2(w.price)+'</td><td>'+pctHtml(w.chg)+'</td><td>'
        + pctHtml(w.np_yoy,1)+'</td><td>'+pctHtml(w.rev_yoy,1)+'</td><td class="mono">'
        + f2(w.pe,1)+'</td><td class="small">'+(w.risk||'')+'</td></tr>';
    });
    tb.innerHTML = h || '<tr><td colspan="7" class="emptybox">这一档暂时没有</td></tr>';
  });
}

document.querySelectorAll('.tabs button').forEach(function(b){
  b.onclick=function(){
    document.querySelectorAll('.tabs button').forEach(function(x){x.classList.remove('on')});
    document.querySelectorAll('section').forEach(function(x){x.classList.remove('on')});
    b.classList.add('on');
    document.getElementById(b.dataset.t).classList.add('on');
    window.scrollTo(0,0);
  };
});
"""


def render():
    snap = load("snapshot.json")
    fund = load("fundamentals.json", {"rows": []})
    market = snap.get("market", {})
    picks = snap.get("picks", [])
    seats = snap.get("seats", [])
    base = snap.get("trade_date", "")
    breadth = market.get("_breadth", {})
    watch = fund.get("rows", [])

    try:
        bd = datetime.datetime.strptime(base, "%Y-%m-%d")
        wd = "一二三四五六日"[bd.weekday()]
        date_txt = "%d 年 %d 月 %d 日（周%s）" % (bd.year, bd.month, bd.day, wd)
        stale = (datetime.datetime.now() - bd).days
    except Exception:
        date_txt = base or "未知"; stale = 0

    init = {"base": base, "market": {}, "breadth": breadth,
            "picks": [], "seats": [], "watch": watch}
    for k, v in market.items():
        if not k.startswith("_"):
            init["market"][k] = {"price": v.get("price"), "chg": v.get("chg")}
    init["picks"] = [{"code": x.get("code"), "name": x.get("name"), "close": x.get("close"),
                      "r5": x.get("r5"), "net3": x.get("net3"), "vol_ratio": x.get("vol_ratio"),
                      "turn": x.get("turn")} for x in picks[:15]]
    init["seats"] = [{"seat": s.get("seat"), "times": s.get("times"), "buy": s.get("buy"),
                      "win5": s.get("win5"), "avg5": s.get("avg5")} for s in seats[:12]]

    idx_html = ""
    for name, v in market.items():
        if name.startswith("_"): continue
        chg = _f(v.get("chg"))
        c = "red" if (chg or 0) > 0 else ("green" if (chg or 0) < 0 else "gray")
        idx_html += ('<div class="idxbox"><div class="idxname">%s</div>'
                     '<div class="idxprice %s">%s</div><div class="idxchg %s">%s%%</div></div>'
                     % (esc(name), c, plain(v.get("price")), c, plain(chg, 2)))
    up = breadth.get("up", 0); down = breadth.get("down", 0); total = breadth.get("total", 0)
    ratio = (up / total * 100) if total else 0
    if ratio < 25:
        verdict, vcls, advice = ("全市场普跌，超跌特征明显", "downbox",
                                 "跌得越狠，后面反弹空间越大。但先别急着买，等企稳信号。")
    elif ratio < 45:
        verdict, vcls, advice = ("跌多涨少，市场偏弱", "downbox",
                                 "还没跌透。想买可以小仓位试，别一次买满。")
    elif ratio < 60:
        verdict, vcls, advice = ("涨跌参半，市场中性", "flatbox",
                                 "没有明显方向。这种时候挑个股比看大盘重要。")
    else:
        verdict, vcls, advice = ("涨多跌少，市场偏暖", "upbox",
                                 "情绪在修复。超跌股反弹的概率变大了。")

    cards = ""
    for i, x in enumerate(picks[:5], 1):
        net3 = _f(x.get("net3")) or 0
        r5 = _f(x.get("r5")) or 0
        reason = ("最近 5 天跌了 %.1f%%，但今天主力资金净流入 %.2f 亿，成交量也在放大——跌的时候有人接货。"
                  % (abs(r5), net3))
        cards += ('<div class="pickcard"><div class="pc-rank">%d</div><div class="pc-main">'
                  '<div class="pc-name">%s<span class="pc-code">%s</span></div>'
                  '<div class="pc-nums"><span class="pc-price">%s</span>%s</div>'
                  '<div class="pc-why">%s</div></div>'
                  '<div class="pc-side"><div class="pc-flow">今日主力<br><b class="%s">%+.2f 亿</b></div>'
                  '<div class="pc-extra">量比 %s　换手 %s%%</div></div></div>'
                  % (i, esc(x.get("name")), esc(x.get("code")), plain(x.get("close")),
                     big_pct(r5), esc(reason), "red" if net3 > 0 else "green", net3,
                     plain(x.get("vol_ratio")), plain(x.get("turn"))))
    rest = ""
    for i, x in enumerate(picks[5:15], 6):
        net3 = _f(x.get("net3")) or 0
        rest += ('<tr><td class="rank">%d</td><td class="bname">%s<span class="code">%s</span></td>'
                 '<td class="mono">%s</td><td>%s</td><td class="mono %s">%+.2f 亿</td><td>%s</td></tr>'
                 % (i, esc(x.get("name")), esc(x.get("code")), plain(x.get("close")),
                    pct(x.get("r5")), "red" if net3 > 0 else "green", net3,
                    plain(x.get("vol_ratio"))))
    seat_html = ""
    for s in seats[:12]:
        win = _f(s.get("win5"))
        seat_html += ('<tr><td class="seat">%s</td><td class="c">%s</td><td class="c">%s 亿</td>'
                      '<td class="c %s"><b>%s%%</b></td><td class="c">%s</td></tr>'
                      % (esc(s.get("seat")), s.get("times"), plain(s.get("buy")),
                         "red" if (win or 0) >= 30 else "gray", plain(win, 1), pct(s.get("avg5"))))

    groups = {"good": [], "watch": [], "avoid": [], "unknown": []}
    for w in watch:
        groups[grade(w)].append(w)

    def rows_of(items, gid):
        if not items:
            return '<div class="emptybox">这一档暂时没有</div>'
        h = ""
        for w in items:
            h += ('<tr><td class="bname">%s<span class="code">%s</span></td><td class="mono">%s</td>'
                  '<td>%s</td><td>%s</td><td>%s</td><td class="mono">%s</td><td class="small">%s</td></tr>'
                  % (esc(w.get("name")), esc(w.get("code")), plain(w.get("price")),
                     pct(w.get("chg")), pct(w.get("np_yoy"), 1), pct(w.get("rev_yoy"), 1),
                     plain(w.get("pe"), 1), esc(w.get("risk", ""))))
        return ('<table><thead><tr><th>股票</th><th>现价</th><th>今日</th><th>利润增速</th>'
                '<th>营收增速</th><th>市盈率</th><th>主要风险</th></tr></thead>'
                '<tbody id="tb-%s">%s</tbody></table>' % (gid, h))

    page = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>妈妈的股票看板</title>
<style>__CSS__</style></head><body>
<header><div class="wrap">
<h1>妈妈的股票看板</h1>
<div class="datebar">数据日期：<b id="dateTxt">__DATE__</b></div>
<div id="staleBox">__STALE__</div>
</div></header>
<div class="wrap">

<div class="updbar">
  <div class="updstat" style="font-size:20px;flex:1">
    <div>📅 <b>生成时间：__NOW__</b></div>
    <div class="small" style="margin-top:6px">大盘指数与 24 只自选股价格 ＝ 最新收盘价；超跌选股榜基于 __DATE__ 收盘数据（数据源有延迟）。</div>
  </div>
</div>

<div class="tabs">
<button class="on" data-t="market">① 今天大盘</button>
<button data-t="picks">② 超跌选股</button>
<button data-t="seats">③ 机构动向</button>
<button data-t="watch">④ 我的 24 只</button>
</div>

<section id="market" class="on">
<div class="card">
<h2>今天大盘怎么样</h2>
<div class="idxrow" id="idxRow">__IDX__</div>
<div class="breadth" id="breadthBox">
<div>上涨 <span class="n red">__UP__</span> 家</div>
<div>下跌 <span class="n green">__DOWN__</span> 家</div>
<div>平盘 __FLAT__ 家</div>
<div>上涨占比 <span class="n">__RATIO__%</span></div>
</div>
<div class="verdict __VCLS__">__VERDICT__</div>
<div class="advice">__ADVICE__</div>
<div class="note"><b>为什么先看大盘：</b>超跌选股是建立在「大盘超跌」这个前提上的。大盘还在跌的时候去买超跌股，很容易抄在半山腰；大盘稳住了，超跌反弹才有空间。</div>
</div>
</section>

<section id="picks">
<div class="card">
<h2>超跌 + 主力资金进场 · 前 5 只</h2>
<div class="note"><b>怎么选出来的：</b>全市场 5000 多只逐只算一遍，三条同时满足才入选——
<b>① 最近 5 个交易日跌超过 8%</b>；<b>② 今天主力资金是净流入的</b>；<b>③ 今天成交量比平时放大（量比 &gt; 1）</b>。再按今天资金流入金额排前 5。</div>
<div class="note warn"><b>要注意：</b>这几只常常集中在同一个行业（比如半导体设备），相当于买一个板块，不是分散买几只。别把它当成「分散风险」。</div>
<div id="pickCards">__CARDS__</div>
<h3>第 6–15 名（备选）</h3>
<table><thead><tr><th>#</th><th>股票</th><th>收盘价</th><th>近5日涨跌</th><th>主力资金</th><th>量比</th></tr></thead>
<tbody id="pickRest">__REST__</tbody></table>
</div>
</section>

<section id="seats">
<div class="card">
<h2>机构 / 大席位 最近在买什么</h2>
<div class="note"><b>先说清楚：</b>交易所只公布「哪个营业部买的」，<b>不公布是不是私募</b>。所以这张表是按席位统计：它最近一个月上榜几次、买了多少钱。<br>这测的是「跟着这个席位买赚不赚钱」，<b>不等于「这家私募 80% 的票赚钱」</b>——后者任何公开数据都算不出来。</div>
<div class="note warn"><b>重要背景：</b>最近一个月大盘在跌，所以几乎所有席位的「买入后 5 天上涨比例」都只有 15%~30%，<b>没有一家到 80%</b>。这是行情差，不是席位不行。看这张表要横向比。</div>
<table><thead><tr><th>席位名称</th><th>上榜次数</th><th>买入金额</th><th>买后5天上涨比例</th><th>5天平均涨跌</th></tr></thead>
<tbody id="seatBody">__SEATS__</tbody></table>
<div class="note">点「更新数据」后，「买后上涨比例」会显示为「—」——因为每次只拉最近一页龙虎榜，算不出历史涨幅。要看完整统计，看原始那版。</div>
</div>
</section>

<section id="watch">
<div class="card">
<h2>妈妈自选的 24 只 · 分三档</h2>
<div class="note"><b>分档规则（透明）：</b><br>
🟢 <b>可以看看</b> ＝ 利润增长 &gt; 20%，营收也在增长，市盈率 &lt; 50<br>
🟡 <b>再观察</b> ＝ 利润在涨但不够快，或者增速好但估值偏高<br>
🔴 <b>建议回避</b> ＝ 利润负增长、或者还在亏损</div>
<div class="group">
<div class="gtitle g-good"><span>🟢 可以看看</span><span class="gcount">__NG__ 只</span></div>
__GOOD__
</div>
<div class="group">
<div class="gtitle g-watch"><span>🟡 再观察</span><span class="gcount">__NW__ 只</span></div>
__WATCH__
</div>
<div class="group">
<div class="gtitle g-avoid"><span>🔴 建议回避</span><span class="gcount">__NA__ 只</span></div>
__AVOID__
</div>
<div class="note">财务数据用最新已披露报告（三季报优先），不会每天变；价格点「更新数据」就会刷新。</div>
</div>
</section>

<div class="footer">
数据来源：新浪财经 · 腾讯财经 · 东方财富（均为公开数据）<br>
本页只做数据整理，不构成买卖建议。投资有风险，决定要慎重。
</div>
</div>
<script>__JS__</script>
</body></html>"""

    repl = {
        "__CSS__": CSS,
        "__JS__": JS.replace("__INIT__", json.dumps(init, ensure_ascii=False)),
        "__NOW__": datetime.datetime.now().strftime("%Y 年 %m 月 %d 日 %H:%M"),
        "__DATE__": esc(date_txt),
        "__STALE__": ('<div class="stale">⚠ 这份数据已经 %d 天没更新，点下面的绿色按钮更新一下</div>' % stale) if stale > 2 else "",
        "__GEN__": esc(snap.get("generated", "")),
        "__IDX__": idx_html,
        "__UP__": str(up), "__DOWN__": str(down), "__FLAT__": str(breadth.get("flat", 0)),
        "__RATIO__": "%.1f" % ratio,
        "__VCLS__": vcls, "__VERDICT__": esc(verdict), "__ADVICE__": esc(advice),
        "__CARDS__": cards, "__REST__": rest, "__SEATS__": seat_html,
        "__NG__": str(len(groups["good"])), "__NW__": str(len(groups["watch"])),
        "__NA__": str(len(groups["avoid"])),
        "__GOOD__": rows_of(groups["good"], "good"),
        "__WATCH__": rows_of(groups["watch"], "watch"),
        "__AVOID__": rows_of(groups["avoid"], "avoid"),
    }
    for k, v in repl.items():
        page = page.replace(k, v)

    out = os.path.join(BASE, "dashboard.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print("已生成", out, len(page), "字节")
    print("分档：可以看看", len(groups["good"]), "/ 观察", len(groups["watch"]),
          "/ 回避", len(groups["avoid"]))

if __name__ == "__main__":
    render()
