#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
母亲股票看板 —— 数据采集 + 网页生成
每天收盘后双击「更新数据.command」即可刷新 dashboard.html

数据源：
  新浪财经  实时行情 / 日K / 资金流趋势
  腾讯财经  日K（前复权）
  东方财富  龙虎榜明细 / 席位明细 / 批量财务
"""
import json, os, sys, time, datetime, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

def fetch(url, timeout=12, ref=None):
    h = dict(UA)
    if ref:
        h["Referer"] = ref
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")

def fetch_gbk(url, timeout=12):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("gbk", "ignore")

def log(msg):
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", flush=True)


# ---------------------------------------------------------------- 大盘
def get_market():
    idx = {"sh000001": "上证指数", "sz399001": "深证成指", "sz399006": "创业板指",
           "sh000688": "科创50", "sh000300": "沪深300"}
    out = {}
    codes = ",".join(idx.keys())
    try:
        s = fetch_gbk(f"https://qt.gtimg.cn/q={codes}")
        for line in s.split(";"):
            if "~" not in line:
                continue
            f = line.split("~")
            if len(f) < 33:
                continue
            name = f[1]
            out[name] = {"price": float(f[3] or 0), "chg": float(f[32] or 0),
                         "amt": float(f[37] or 0) / 1e4 if len(f) > 37 else 0}
    except Exception as e:
        log(f"大盘获取失败 {e}")
    # 全市场涨跌家数
    up = down = flat = 0
    try:
        rows = []
        def page(p):
            u = ("https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                 f"Market_Center.getHQNodeData?page={p}&num=100&sort=symbol&asc=1&node=hs_a")
            try:
                return json.loads(fetch(u, ref="https://finance.sina.com.cn"))
            except Exception:
                return []
        with ThreadPoolExecutor(max_workers=6) as ex:
            for arr in ex.map(page, range(1, 66)):
                if arr:
                    rows += arr
        for x in rows:
            if x["symbol"].startswith("bj"):
                continue
            c = float(x.get("changepercent") or 0)
            if c > 0: up += 1
            elif c < 0: down += 1
            else: flat += 1
        out["_breadth"] = {"up": up, "down": down, "flat": flat, "total": up + down + flat}
    except Exception as e:
        log(f"涨跌家数失败 {e}")
    return out


# ---------------------------------------------------------------- 全市场扫描
def get_universe():
    rows = []
    def page(p):
        u = ("https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/"
             f"Market_Center.getHQNodeData?page={p}&num=100&sort=symbol&asc=1&node=hs_a")
        try:
            return json.loads(fetch(u, ref="https://finance.sina.com.cn"))
        except Exception:
            return []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for arr in ex.map(page, range(1, 66)):
            if arr:
                rows += arr
    uni = {}
    for x in rows:
        if x["symbol"].startswith("bj"):
            continue
        if "ST" in x["name"] or "退" in x["name"]:
            continue
        try:
            uni[x["code"]] = dict(code=x["code"], sym=x["symbol"], name=x["name"],
                                  close=float(x["trade"]), chg=float(x["changepercent"]),
                                  amt=float(x.get("amount") or 0) / 1e8,
                                  turn=float(x.get("turnoverratio") or 0),
                                  mktcap=float(x.get("mktcap") or 0) / 1e4)
        except Exception:
            pass
    return uni


def get_klines(universe, workers=8):
    """腾讯日K（前复权，收盘后约 15:05 即更新当天）"""
    def one(c):
        for attempt in (1, 2):
            try:
                s = fetch(f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={c['sym']},day,,,25,qfq", timeout=10)
                d = json.loads(s)["data"][c["sym"]]
                ks = d.get("qfqday") or d.get("day") or []
                if len(ks) < 21:
                    return None
                return (c["code"], {"dates": [k[0] for k in ks],
                                    "closes": [float(k[2]) for k in ks],
                                    "vols": [float(k[5]) for k in ks]})
            except Exception:
                if attempt == 1:
                    time.sleep(0.4)
    out = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(one, list(universe.values())):
            if res:
                out[res[0]] = res[1]
    return out


def get_flows(codes, universe, workers=8):
    def one(code):
        try:
            sym = universe[code]["sym"]
            s = fetch("http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                      f"MoneyFlow.ssl_qsfx_zjlrqs?page=1&num=8&sort=opendate&asc=0&daima={sym}",
                      ref="https://finance.sina.com.cn")
            arr = json.loads(s)
            if not arr:
                return None
            arr = sorted(arr, key=lambda x: x["opendate"])
            return (code, [dict(d=x["opendate"], net=float(x["netamount"]),
                                r0=float(x["r0_net"]), chg=float(x["changeratio"]) * 100)
                           for x in arr])
        except Exception:
            return None
    out = {}
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(one, codes):
            if res:
                out[res[0]] = res[1]
    return out


# ---------------------------------------------------------------- 选股①超跌+资金
def screen_oversold(universe, klines, flows, topn=5):
    last_full = None
    rows = []
    for code, kl in klines.items():
        if code not in universe or code not in flows:
            continue
        cl, dt, vo = kl["closes"], kl["dates"], kl["vols"]
        if len(cl) < 8:
            continue
        # 以最近一个「资金流也有数据」的交易日为基准
        fl = sorted(flows[code], key=lambda x: x["d"])
        base_date = fl[-1]["d"]
        if base_date not in dt:
            continue
        i = dt.index(base_date)
        if i < 6:
            continue
        last_full = base_date
        r5 = (cl[i] / cl[i - 5] - 1) * 100
        if r5 > -8:
            continue
        last3 = [x for x in fl if x["d"] <= base_date][-3:]
        if len(last3) < 3:
            continue
        nets = [x["net"] for x in last3]
        improving = (nets[2] > nets[1] > nets[0]) or (nets[2] > 0 and nets[1] > 0)
        if not improving:
            continue
        vol5 = sum(vo[max(0, i - 5):i]) / max(1, len(vo[max(0, i - 5):i]))
        vol_ratio = vo[i] / vol5 if vol5 else 0
        u = universe[code]
        rows.append(dict(code=code, name=u["name"], r5=round(r5, 2), close=round(cl[i], 2),
                         nets=[round(n / 1e8, 2) for n in nets],
                         net3=round(sum(nets) / 1e8, 2),
                         vol_ratio=round(vol_ratio, 2), turn=round(u["turn"], 2),
                         amt=round(u["amt"], 2), mktcap=round(u["mktcap"], 1),
                         chg_now=round(u["chg"], 2),
                         spark=[round(x, 2) for x in cl[max(0, i - 19):i + 1]],
                         base_date=base_date))
    rows.sort(key=lambda x: (-x["net3"], x["r5"]))
    return rows, last_full


# ---------------------------------------------------------------- 选股②席位跟踪
def get_seats(start_date):
    """近一月龙虎榜买方席位（该报表不支持日期筛选，按日期倒序翻页直到越过起点）"""
    recs = []
    page = 1
    while page <= 30:
        u = ("https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_BILLBOARD_DAILYDETAILSBUY"
             "&columns=SECURITY_CODE,TRADE_DATE,OPERATEDEPT_NAME,BUY,SELL,NET,CHANGE_RATE,"
             "RISE_PROBABILITY_3DAY,TOTAL_BUYER_SALESTIMES_3DAY,TOTAL_BUYRIO"
             f"&pageNumber={page}&pageSize=500&sortColumns=TRADE_DATE&sortTypes=-1&source=WEB&client=WEB")
        try:
            d = json.loads(fetch(u, timeout=25, ref="https://data.eastmoney.com/"))
            r = d.get("result") or {}
            data = r.get("data") or []
            if not data:
                break
            recs += data
            oldest = min((x.get("TRADE_DATE") or "")[:10] for x in data)
            if oldest < start_date:
                recs = [x for x in recs if (x.get("TRADE_DATE") or "")[:10] >= start_date]
                break
            if page >= (r.get("pages") or 1):
                break
            page += 1
        except Exception as e:
            log(f"席位第{page}页失败 {e}")
            break
    return recs


def get_aftermove(start_date):
    """龙虎榜个股上榜后 1/2/5/10 日涨跌幅"""
    recs = []
    page = 1
    while page <= 25:
        u = ("https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_DAILYBILLBOARD_DETAILSNEW"
             "&columns=SECURITY_CODE,SECURITY_NAME_ABBR,TRADE_DATE,CLOSE_PRICE,CHANGE_RATE,TURNOVERRATE,"
             "D1_CLOSE_ADJCHRATE,D2_CLOSE_ADJCHRATE,D5_CLOSE_ADJCHRATE,D10_CLOSE_ADJCHRATE,"
             "BILLBOARD_BUY_AMT,BILLBOARD_SELL_AMT,BILLBOARD_NET_AMT,EXPLANATION"
             f"&filter=(TRADE_DATE%3E%3D%27{start_date}%27)"
             f"&pageNumber={page}&pageSize=500&sortColumns=TRADE_DATE&sortTypes=-1&source=WEB&client=WEB")
        try:
            d = json.loads(fetch(u, timeout=20, ref="https://data.eastmoney.com/"))
            r = d.get("result") or {}
            data = r.get("data") or []
            if not data:
                break
            recs += data
            if page >= (r.get("pages") or 1):
                break
            page += 1
        except Exception as e:
            log(f"龙虎榜第{page}页失败 {e}")
            break
    return recs


def build_seat_board(seat_recs, after_recs):
    """按席位聚合：上榜次数、操作股票数、买入额、买入后5/10日表现"""
    after = {}
    name_of = {}
    for x in after_recs:
        k = (x["SECURITY_CODE"], (x.get("TRADE_DATE") or "")[:10])
        after[k] = x
        if x.get("SECURITY_NAME_ABBR"):
            name_of[x["SECURITY_CODE"]] = x["SECURITY_NAME_ABBR"]
    agg = {}
    for s in seat_recs:
        name = s.get("OPERATEDEPT_NAME") or ""
        if not name:
            continue
        key = name
        a = agg.setdefault(key, {"seat": name, "times": 0, "stocks": set(),
                                 "buy": 0.0, "d5": [], "d10": [], "details": []})
        a["times"] += 1
        nm = name_of.get(s.get("SECURITY_CODE"))
        if nm:
            a["stocks"].add(nm)
        try:
            a["buy"] += float(s.get("BUY") or 0)
        except Exception:
            pass
        k = (s.get("SECURITY_CODE"), (s.get("TRADE_DATE") or "")[:10])
        af = after.get(k)
        if af:
            for fld, tgt in (("D5_CLOSE_ADJCHRATE", "d5"), ("D10_CLOSE_ADJCHRATE", "d10")):
                v = af.get(fld)
                if v is not None:
                    a[tgt].append(float(v))
            a["details"].append(dict(stock=af.get("SECURITY_NAME_ABBR"), date=(af.get("TRADE_DATE") or "")[:10],
                                     chg=round(float(af.get("CHANGE_RATE") or 0), 2),
                                     d5=round(float(af["D5_CLOSE_ADJCHRATE"]), 2) if af.get("D5_CLOSE_ADJCHRATE") is not None else None,
                                     d10=round(float(af["D10_CLOSE_ADJCHRATE"]), 2) if af.get("D10_CLOSE_ADJCHRATE") is not None else None))
    out = []
    for a in agg.values():
        d5 = a["d5"]; d10 = a["d10"]
        win5 = (sum(1 for x in d5 if x > 0) / len(d5) * 100) if d5 else None
        avg5 = (sum(d5) / len(d5)) if d5 else None
        win10 = (sum(1 for x in d10 if x > 0) / len(d10) * 100) if d10 else None
        avg10 = (sum(d10) / len(d10)) if d10 else None
        big15 = (sum(1 for x in d5 if x >= 15) / len(d5) * 100) if d5 else None
        out.append(dict(seat=a["seat"], times=a["times"], nstocks=len(a["stocks"]),
                        buy=round(a["buy"] / 1e8, 2), win5=round(win5, 1) if win5 is not None else None,
                        avg5=round(avg5, 2) if avg5 is not None else None,
                        win10=round(win10, 1) if win10 is not None else None,
                        avg10=round(avg10, 2) if avg10 is not None else None,
                        big15=round(big15, 1) if big15 is not None else None,
                        sample=len(d5), stocks=sorted([x for x in a["stocks"] if x])[:8],
                        details=sorted(a["details"], key=lambda x: x["date"], reverse=True)[:10]))
    return out


# ---------------------------------------------------------------- 24 只自选股
def get_fin_bulk(report_date):
    """全市场某报告期财务（一次拿全）"""
    out = {}
    page = 1
    while page <= 260:
        u = ("https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LICO_FN_CPD"
             "&columns=SECURITY_CODE,SECURITY_NAME_ABBR,REPORTDATE,NOTICE_DATE,TOTAL_OPERATE_INCOME,"
             "PARENT_NETPROFIT,XSMLL,BASIC_EPS,WEIGHTAVG_ROE,YSTZ,SJLTZ"
             f"&filter=(REPORTDATE%3D%27{report_date}%27)"
             f"&pageNumber={page}&pageSize=500&sortColumns=SECURITY_CODE&sortTypes=1&source=WEB&client=WEB")
        try:
            d = json.loads(fetch(u, timeout=25, ref="https://data.eastmoney.com/"))
            r = d.get("result") or {}
            data = r.get("data") or []
            if not data:
                break
            for x in data:
                out[x["SECURITY_CODE"]] = x
            if page >= (r.get("pages") or 1):
                break
            page += 1
        except Exception as e:
            log(f"财务 {report_date} 第{page}页失败 {e}")
            break
    return out


if __name__ == "__main__":
    log("===== 开始采集 =====")
    market = get_market()
    parts = []
    for k, v in market.items():
        if not k.startswith("_"):
            parts.append("%s%+.2f%%" % (k, v["chg"]))
    log("大盘: " + "  ".join(parts))

    uni = get_universe()
    log(f"全市场 {len(uni)} 只")

    kl = get_klines(uni)
    log(f"K线 {len(kl)} 只")

    # 先粗筛超跌，减少资金流请求量
    pre = []
    for code, k in kl.items():
        cl, dt = k["closes"], k["dates"]
        if len(cl) >= 8 and (cl[-1] / cl[-6] - 1) * 100 <= -5:
            pre.append(code)
    log(f"近5日跌幅>5% 的 {len(pre)} 只，开始查资金流")
    flows = get_flows(pre, uni)
    log(f"资金流 {len(flows)} 只")

    picks, base_date = screen_oversold(uni, kl, flows, 8)
    log(f"选股① 命中 {len(picks)} 只，基准日 {base_date}")

    start = (datetime.date.today() - datetime.timedelta(days=32)).isoformat()
    log(f"拉取龙虎榜（{start} 起）")
    seats = get_seats(start)
    after = get_aftermove(start)
    log(f"席位记录 {len(seats)} 条 / 个股记录 {len(after)} 条")
    board = build_seat_board(seats, after)
    board.sort(key=lambda x: (-(x["times"]), -(x["buy"])))
    log(f"席位聚合 {len(board)} 个")

    payload = dict(generated=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                   trade_date=base_date, market=market, picks=picks,
                   seats=board[:80])
    with open(os.path.join(DATA, "snapshot.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    log("已保存 data/snapshot.json")
