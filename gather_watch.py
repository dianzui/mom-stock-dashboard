#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""采集妈妈自选 24 只的定量数据 → data/fundamentals.json"""
import json, os, urllib.request, datetime
from concurrent.futures import ThreadPoolExecutor

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

WATCH = [
    ("600150", "中国船舶"), ("002683", "广东宏大"), ("601211", "国泰海通"), ("002351", "漫步者"),
    ("300852", "四会富仕"), ("688133", "泰坦科技"), ("603214", "爱婴室"), ("000921", "海信家电"),
    ("601012", "隆基绿能"), ("002492", "恒基达鑫"), ("002079", "苏州固锝"), ("002241", "歌尔股份"),
    ("688510", "航亚科技"), ("300445", "康斯特"), ("301367", "瑞迈特"), ("300677", "英科医疗"),
    ("688825", "长鑫科技"), ("600111", "北方稀土"), ("300113", "顺网科技"), ("300748", "金力永磁"),
    ("000933", "神火股份"), ("301047", "义翘神州"), ("601611", "中国核建"), ("002517", "恺英网络"),
]

# 行业风口 / 主要风险（定性，来自公开信息与行业常识，非量化数据）
QUAL = {
    "600150": ("船舶制造·周期上行", "造船价高位但新船订单增速放缓，业绩兑现慢"),
    "002683": ("民爆+矿服·资源开采配套", "民爆需求跟基建/矿业资本开支，区域集中度高"),
    "601211": ("券商·牛市β", "业绩强依赖成交量和行情，市场转冷即回落"),
    "002351": ("消费电子·AI耳机", "营收连续负增长，扣非基本零增长，AI 只是概念"),
    "300852": ("PCB·算力硬件", "客户集中、单价随算力资本开支波动"),
    "688133": ("科研试剂·国产替代", "下游科研经费依赖，盈利质量弱"),
    "603214": ("母婴零售·生育率相关", "出生率长期下行，门店扩张受限"),
    "000921": ("白电·出海+以旧换新", "地产链拖累内销，海外关税风险"),
    "601012": ("光伏·产能出清中", "全行业亏损，硅料价格仍低，反转未确认"),
    "002492": ("石化仓储物流", "区域垄断但增长慢，油价与化工景气相关"),
    "002079": ("半导体封装·国产替代", "规模小、议价弱，随半导体周期波动"),
    "002241": ("消费电子·AI眼镜/声学", "大客户依赖（苹果等），订单转移风险"),
    "688510": ("航空发动机零部件", "客户高度集中，交付节奏受主机厂影响"),
    "300445": ("压力检测仪表", "细分市场小，成长天花板明确"),
    "301367": ("家用呼吸机·出海", "集采与海外注册风险，单品依赖"),
    "300677": ("医疗耗材·手套", "产能过剩余波，价格战"),
    "688825": ("DRAM·存储超级周期", "刚上市流通盘仅6.6%，估值极高，周期见顶风险"),
    "600111": ("稀土·战略资源+配额", "价格受配额与出口管制政策主导，波动剧烈"),
    "300113": ("算力/网吧流量", "主业弱，靠概念，业绩兑现差"),
    "300748": ("稀土永磁·机器人/新能源", "稀土成本占比高，下游需求波动"),
    "000933": ("电解铝+煤炭·周期高位", "铝价煤价决定一切，毛利率处历史高位"),
    "301047": ("生物试剂·科研服务", "科研经费与海外订单波动，此前疫情基数扰动"),
    "601611": ("核电建设·核准加速", "工程类低毛利，回款周期长"),
    "002517": ("游戏·AI+版号", "流水依赖爆款，监管与版号政策风险"),
}


def fetch(url, timeout=15, ref=None):
    h = dict(UA)
    if ref: h["Referer"] = ref
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")

def fetch_gbk(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("gbk", "ignore")


def quotes():
    codes = []
    for c, _ in WATCH:
        codes.append(("sh" if c[0] in "56" else "sz") + c)
    out = {}
    s = fetch_gbk("https://qt.gtimg.cn/q=" + ",".join(codes))
    for line in s.split(";"):
        if "~" not in line: continue
        f = line.split("~")
        if len(f) < 50: continue
        code = f[2]
        try:
            out[code] = dict(price=float(f[3] or 0), chg=float(f[32] or 0),
                             turn=float(f[38] or 0), pe=float(f[39] or 0),
                             mktcap=float(f[45] or 0), pb=float(f[46] or 0))
        except Exception:
            pass
    return out


def fin_one(code):
    sym = ("sh" if code[0] in "56" else "sz") + code
    for rd in ("2026-09-30", "2026-06-30", "2026-03-31"):
        u = ("https://datacenter-web.eastmoney.com/api/data/v1/get?reportName=RPT_LICO_FN_CPD"
             "&columns=SECURITY_CODE,REPORTDATE,NOTICE_DATE,TOTAL_OPERATE_INCOME,PARENT_NETPROFIT,"
             "XSMLL,WEIGHTAVG_ROE,YSTZ,SJLTZ"
             f"&filter=(SECURITY_CODE%3D%22{code}%22)(REPORTDATE%3D%27{rd}%27)"
             "&pageNumber=1&pageSize=2&source=WEB&client=WEB")
        try:
            d = json.loads(fetch(u, ref="https://data.eastmoney.com/"))
            arr = (d.get("result") or {}).get("data") or []
            if arr:
                x = arr[0]
                return dict(report=(x.get("REPORTDATE") or "")[:10],
                            notice=(x.get("NOTICE_DATE") or "")[:10],
                            rev=x.get("TOTAL_OPERATE_INCOME"), np=x.get("PARENT_NETPROFIT"),
                            gpm=x.get("XSMLL"), roe=x.get("WEIGHTAVG_ROE"),
                            rev_yoy=x.get("YSTZ"), np_yoy=x.get("SJLTZ"))
        except Exception:
            pass
    return {}


def flow_one(code):
    sym = ("sh" if code[0] in "56" else "sz") + code
    try:
        s = fetch("http://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
                  f"MoneyFlow.ssl_qsfx_zjlrqs?page=1&num=22&sort=opendate&asc=0&daima={sym}",
                  ref="https://finance.sina.com.cn")
        arr = json.loads(s)
        if not arr: return {}
        tot = sum(float(x["netamount"]) for x in arr)
        last = float(arr[0]["netamount"])
        return dict(flow1m=round(tot / 1e8, 2), flow_last=round(last / 1e8, 2), days=len(arr))
    except Exception:
        return {}


def main():
    q = quotes()
    print("行情", len(q))
    rows = []
    for code, name in WATCH:
        f = fin_one(code)
        fl = flow_one(code)
        qq = q.get(code, {})
        theme, risk = QUAL.get(code, ("", ""))
        row = dict(code=code, name=name, price=qq.get("price"), chg=qq.get("chg"),
                   turn=qq.get("turn"), pe=qq.get("pe"), mktcap=qq.get("mktcap"),
                   theme=theme, risk=risk)
        row.update({k: (round(v / 1e8, 2) if k in ("rev", "np") and isinstance(v, (int, float)) else v)
                    for k, v in f.items()})
        row.update(fl)
        rows.append(row)
    out = dict(generated=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), rows=rows)
    with open(os.path.join(DATA, "fundamentals.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    for r in rows:
        print(f"{r['name']:6s} {r.get('report','—')} 营收{r.get('rev','—')}亿 增速{r.get('rev_yoy')}"
              f" 净利{r.get('np','—')}亿 增速{r.get('np_yoy')} 毛利{r.get('gpm')} 近1月主力{r.get('flow1m')}亿")
    print("已保存 data/fundamentals.json")


if __name__ == "__main__":
    main()
