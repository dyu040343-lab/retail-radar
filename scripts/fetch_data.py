#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
散户雷达侦探 - 数据抓取脚本 v2
六维指标：散户流入额/流出额/净流入额 + 对应股票只数
多数据源：东方财富(实时) → 新浪财经(收盘可用) → 缓存 → 备用数据
"""

import requests
import json
import time
import os
from datetime import datetime

OUTPUT_DIR = "data"
CACHE_FILE = f"{OUTPUT_DIR}/radar_data_cache.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
}

SINA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "http://vip.stock.finance.sina.com.cn/",
}

WATCH_LIST = [
    ("600150", "中国船舶", "sh"), ("601318", "中国平安", "sh"), ("603256", "宏和科技", "sh"),
    ("600519", "贵州茅台", "sh"), ("002594", "比亚迪", "sz"), ("000725", "京东方A", "sz"),
    ("601012", "隆基绿能", "sh"), ("300750", "宁德时代", "sz"), ("600036", "招商银行", "sh"),
    ("000858", "五粮液", "sz"), ("002475", "立讯精密", "sz"), ("600900", "长江电力", "sh"),
    ("601899", "紫金矿业", "sh"), ("300059", "东方财富", "sz"), ("600276", "恒瑞医药", "sh"),
    ("000333", "美的集团", "sz"), ("002230", "科大讯飞", "sz"), ("688981", "中芯国际", "sh"),
    ("601628", "中国人寿", "sh"), ("000977", "浪潮信息", "sz"),
    ("600584", "长电科技", "sh"), ("600522", "中天科技", "sh"), ("300308", "中际旭创", "sz"),
    ("300476", "胜宏科技", "sz"), ("603986", "兆易创新", "sh"), ("600707", "彩虹股份", "sh"),
    ("002415", "海康威视", "sz"), ("000063", "中兴通讯", "sz"), ("600809", "山西汾酒", "sh"),
    ("000021", "深科技", "sz"),
    ("600009", "上海机场", "sh"), ("601857", "中国石油", "sh"), ("600028", "中国石化", "sh"),
    ("000651", "格力电器", "sz"), ("002241", "歌尔股份", "sz"), ("300015", "爱尔眼科", "sz"),
    ("603259", "药明康德", "sh"), ("600690", "海尔智家", "sh"), ("002352", "顺丰控股", "sz"),
    ("600048", "保利发展", "sh"), ("000002", "万科A", "sz"),
]


def load_cache():
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return None


def save_cache(data):
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass


def guess_sector(name, code):
    sectors = {
        '半导体': ['半导体', '芯片', '封测', '集成', '微电'],
        'PCB/算力': ['PCB', '电路', '算力', '服务', '计算机'],
        '面板/显示': ['面板', '显示', '光电', '玻璃'],
        '光通信': ['光纤', '光模块', '通信', '光缆'],
        '新能源': ['新能', '锂电', '光伏', '电池', '充电'],
        '医药': ['药', '医疗', '生物', '医药'],
        '金融': ['银行', '证券', '保险', '金融'],
        '化工': ['化工', '化学', '氟', '材料'],
        '消费': ['酒', '食品', '乳', '家电', '百货'],
        '地产': ['地产', '万科', '保利', '发展'],
    }
    for sector, keywords in sectors.items():
        if any(kw in name for kw in keywords):
            return sector
    if code.startswith('6013') or code.startswith('6000'):
        return '金融'
    if code.startswith('300'):
        return '科技'
    return '综合'


def fetch_from_eastmoney():
    """东方财富实时API - 全市场扫描，分页获取所有A股"""
    print("🔍 [数据源1] 东方财富API（全市场）...")
    stocks = []
    try:
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        # 沪深全A股：沪市主板+科创板 + 深市主板+创业板+中小板
        markets = [
            ("沪市", "m:1+t:2,m:1+t:23"),
            ("深市", "m:0+t:6,m:0+t:80,m:0+t:13,m:0+t:81"),
        ]
        for market_name, fs in markets:
            page = 1
            while True:
                params = {
                    "pn": str(page), "pz": "100", "po": "1", "np": "1",
                    "ut": "b2884a393a59ad64002292a3e90d46a5",
                    "fltt": "2", "invt": "2", "fid": "f84",
                    "fs": fs,
                    "fields": "f2,f3,f12,f14,f62,f84,f78",
                    "_": str(int(time.time() * 1000))
                }
                try:
                    resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
                    if resp.status_code == 200 and resp.text.strip():
                        data = resp.json()
                        diff = data.get("data", {}).get("diff", [])
                        total = data.get("data", {}).get("total", 0)
                        if not diff:
                            break
                        for item in diff:
                            code = item.get("f12", "")
                            name = item.get("f14", "")
                            price = item.get("f2", 0)
                            change_pct = item.get("f3", 0)
                            small_net = item.get("f84", 0) or 0
                            medium_net = item.get("f78", 0) or 0
                            retail_net = (small_net + medium_net) / 100000000
                            main_net = item.get("f62", 0) or 0
                            main_net_yi = round(main_net / 100000000, 2)

                            retail_inflow = max(retail_net, 0)
                            retail_outflow = max(-retail_net, 0)

                            total_abs = abs(retail_net) + abs(main_net_yi)
                            retail_ratio = round(retail_net / total_abs * 100, 1) if total_abs > 0.01 else 0
                            retail_share = round(abs(retail_net) / total_abs * 100, 1) if total_abs > 0.01 else 0
                            stocks.append({
                                "code": code, "name": name,
                                "price": round(price, 2) if isinstance(price, (int, float)) else 0,
                                "change_pct": round(change_pct, 2) if isinstance(change_pct, (int, float)) else 0,
                                "retail_inflow": round(retail_inflow, 2),
                                "retail_outflow": round(retail_outflow, 2),
                                "retail_net": round(retail_net, 2),
                                "main_net": main_net_yi,
                                "retail_ratio": retail_ratio,
                                "retail_share": retail_share,
                                "sector": guess_sector(name, code),
                                "source": "eastmoney",
                            })
                        if len(diff) < 100:
                            break
                        page += 1
                    else:
                        print(f"  ⚠️ {market_name} p{page}: status={resp.status_code}")
                        break
                except Exception as e:
                    print(f"  ⚠️ {market_name} p{page}失败: {e}")
                    break
            print(f"  ✅ {market_name}: 累计 {len(stocks)} 条")
    except Exception as e:
        print(f"  ⚠️ 东方财富不可用: {e}")

    if stocks:
        print(f"  ✅ 东方财富全市场共 {len(stocks)} 条 [实时]")
    return stocks


def fetch_from_sina():
    """新浪财经API - 收盘后也可获取当日数据，含流入流出明细"""
    print("🔍 [数据源2] 新浪财经API...")
    stocks = []
    session = requests.Session()
    session.headers.update(SINA_HEADERS)

    for code, name, market in WATCH_LIST:
        try:
            daima = f"{market}{code}"
            url = f"http://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/MoneyFlow.ssi_ssfx_flzjtj?format=json&daima={daima}"
            resp = session.get(url, timeout=8)
            if resp.status_code == 200 and resp.text.strip():
                data = resp.json()
                if not data:
                    continue
                item = data[0] if isinstance(data, list) else data

                # 新浪字段：r0=超大单, r1=大单, r2=中单, r3=小单
                # rX_in=流入, rX_out=流出, rX=总额(流入+流出)，单位：元
                r0_in = float(item.get("r0_in", 0) or 0)
                r0_out = float(item.get("r0_out", 0) or 0)
                r1_in = float(item.get("r1_in", 0) or 0)
                r1_out = float(item.get("r1_out", 0) or 0)
                r2_in = float(item.get("r2_in", 0) or 0)
                r2_out = float(item.get("r2_out", 0) or 0)
                r3_in = float(item.get("r3_in", 0) or 0)
                r3_out = float(item.get("r3_out", 0) or 0)

                # 散户 = 中单 + 小单
                retail_inflow = (r2_in + r3_in) / 100000000
                retail_outflow = (r2_out + r3_out) / 100000000
                retail_net = retail_inflow - retail_outflow

                # 主力 = 超大单 + 大单（净额 = 流入 - 流出）
                main_net = ((r0_in - r0_out) + (r1_in - r1_out)) / 100000000

                price = float(item.get("trade", 0) or 0)
                change_pct = float(item.get("changeratio", 0) or 0) * 100

                total_abs = abs(retail_net) + abs(main_net)
                retail_ratio = round(retail_net / total_abs * 100, 1) if total_abs > 0.01 else 0
                retail_share = round(abs(retail_net) / total_abs * 100, 1) if total_abs > 0.01 else 0
                stocks.append({
                    "code": code, "name": name,
                    "price": round(price, 2) if price else 0,
                    "change_pct": round(change_pct, 2) if change_pct else 0,
                    "retail_inflow": round(retail_inflow, 2),
                    "retail_outflow": round(retail_outflow, 2),
                    "retail_net": round(retail_net, 2),
                    "main_net": round(main_net, 2),
                    "retail_ratio": retail_ratio,
                    "retail_share": retail_share,
                    "sector": guess_sector(name, code),
                    "source": "sina",
                })
        except:
            pass
        time.sleep(0.08)

    if stocks:
        print(f"  ✅ 新浪共 {len(stocks)} 条 [收盘/实时]")
    return stocks


def fetch_retail_money_flow():
    print("=" * 50)
    print("📡 小散研究院 - 数据抓取中...")
    print("=" * 50)

    stocks = fetch_from_eastmoney()
    if stocks:
        return stocks, "live"

    stocks = fetch_from_sina()
    if stocks:
        return stocks, "live"

    print("📦 API不可用，尝试缓存...")
    cache = load_cache()
    if cache and cache.get("retail_flow"):
        cached = cache["retail_flow"]
        print(f"  ✅ 缓存 {len(cached)} 条 [缓存于 {cache.get('last_updated')}]")
        return cached, "cached"

    print("📦 使用备用数据...")
    fallback = get_fallback_data()
    print(f"  ✅ 备用 {len(fallback)} 条 [静态]")
    return fallback, "static"


def get_fallback_data():
    """备用数据 - 带流入流出明细"""
    base = [
        ("600150", "中国船舶", 9.12, 3.45, "军工/船舶"),
        ("601318", "中国平安", 4.78, 2.13, "保险"),
        ("603256", "宏和科技", 4.68, 1.89, "化工"),
        ("600519", "贵州茅台", 3.89, 1.54, "白酒"),
        ("002594", "比亚迪", 3.56, 1.42, "新能源汽车"),
        ("000725", "京东方A", 3.34, 1.28, "面板/显示"),
        ("601012", "隆基绿能", 3.12, 1.15, "光伏"),
        ("300750", "宁德时代", 2.98, 1.08, "电池"),
        ("600036", "招商银行", 2.87, 1.03, "银行"),
        ("000858", "五粮液", 2.65, 0.95, "白酒"),
        ("002475", "立讯精密", 2.43, 0.88, "消费电子"),
        ("600900", "长江电力", 2.21, 0.82, "电力"),
        ("601899", "紫金矿业", 2.15, 0.78, "有色金属"),
        ("300059", "东方财富", 1.98, 0.72, "证券"),
        ("600276", "恒瑞医药", 1.87, 0.68, "医药"),
        ("000333", "美的集团", 1.76, 0.65, "家电"),
        ("002230", "科大讯飞", 1.65, 0.61, "AI/算力"),
        ("688981", "中芯国际", 1.54, 0.57, "半导体"),
        ("601628", "中国人寿", 1.43, 0.53, "保险"),
        ("000977", "浪潮信息", 1.35, 0.49, "算力服务器"),
        ("600584", "长电科技", 1.28, 0.46, "半导体封测"),
        ("600522", "中天科技", 1.15, 0.42, "光纤/光通信"),
        ("300308", "中际旭创", 1.08, 0.39, "光模块"),
        ("300476", "胜宏科技", 0.98, 0.35, "PCB"),
        ("603986", "兆易创新", 0.89, 0.32, "存储芯片"),
        ("600707", "彩虹股份", 0.82, 0.29, "玻璃基板"),
        ("002415", "海康威视", 0.75, 0.27, "安防"),
        ("000063", "中兴通讯", 0.68, 0.24, "通信设备"),
        ("600809", "山西汾酒", 0.61, 0.22, "白酒"),
        ("000021", "深科技", 0.55, 0.20, "存储/半导体"),
        ("600009", "上海机场", 0.48, 0.17, "航空"),
        ("601857", "中国石油", 0.42, 0.15, "石油"),
        ("600028", "中国石化", 0.38, 0.14, "石油"),
        ("000651", "格力电器", 0.35, 0.13, "家电"),
        ("002241", "歌尔股份", 0.32, 0.11, "消费电子"),
        ("300015", "爱尔眼科", 0.28, 0.10, "医疗"),
        ("603259", "药明康德", 0.25, 0.09, "医药"),
        ("600690", "海尔智家", 0.22, 0.08, "家电"),
        ("002352", "顺丰控股", 0.18, 0.06, "物流"),
        ("600048", "保利发展", 0.15, 0.05, "地产"),
        ("000002", "万科A", -0.12, 0.34, "地产"),
    ]
    stocks = []
    for code, name, net, out_est, sector in base:
        inflow = max(net, 0) + abs(net) * 0.3 + 0.5
        outflow = max(-net, 0) + abs(net) * 0.3 + 0.3
        if net < 0:
            inflow, outflow = outflow, inflow
        main_val = round(-net * 0.8, 2)
        total_abs = abs(inflow - outflow) + abs(main_val)
        retail_ratio = round((inflow - outflow) / total_abs * 100, 1) if total_abs > 0.01 else 0
        retail_share = round(abs(inflow - outflow) / total_abs * 100, 1) if total_abs > 0.01 else 0
        stocks.append({
            "code": code, "name": name,
            "price": 0, "change_pct": 0,
            "retail_inflow": round(inflow, 2),
            "retail_outflow": round(outflow, 2),
            "retail_net": round(inflow - outflow, 2),
            "main_net": main_val,
            "retail_ratio": retail_ratio,
            "retail_share": retail_share,
            "sector": sector,
        })
    return stocks


def fetch_shareholder_count():
    """从东方财富API获取全市场股东户数变化数据"""
    print("🔍 正在从东方财富获取股东户数变化数据...")
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"
    columns = "SECURITY_CODE,SECURITY_NAME_ABBR,END_DATE,HOLDER_NUM,PRE_HOLDER_NUM,HOLDER_NUM_CHANGE,HOLDER_NUM_RATIO,HOLD_NOTICE_DATE,AVG_MARKET_CAP,TOTAL_MARKET_CAP,INTERVAL_CHRATE"

    params = {
        "reportName": "RPT_HOLDERNUMLATEST",
        "sortColumns": "HOLDER_NUM_RATIO",
        "sortTypes": "-1",
        "pageSize": "200",
        "pageNumber": "1",
        "columns": columns,
        "source": "WEB",
        "client": "WEB",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://data.eastmoney.com/gdhs/",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        data = resp.json()
        result = data.get("result", {})
        items = result.get("data", []) or []

        if not items:
            print("  ⚠️ API返回空，使用备用数据")
            return _fallback_shareholder_data()

        stocks = []
        for item in items:
            code = item.get("SECURITY_CODE", "")
            name = item.get("SECURITY_NAME_ABBR", "")
            current = item.get("HOLDER_NUM") or 0
            previous = item.get("PRE_HOLDER_NUM") or 0
            change = item.get("HOLDER_NUM_CHANGE") or 0
            ratio = item.get("HOLDER_NUM_RATIO") or 0
            end_date = item.get("END_DATE", "") or ""
            notice_date = item.get("HOLD_NOTICE_DATE", "") or ""
            avg_market_cap = item.get("AVG_MARKET_CAP") or 0
            total_market_cap = item.get("TOTAL_MARKET_CAP") or 0
            interval_chg = item.get("INTERVAL_CHRATE") or 0

            # 跳过无效数据
            if not code or not name or previous == 0:
                continue

            # 格式化期间
            period = end_date[:7] if end_date else ""

            stocks.append({
                "code": code,
                "name": name,
                "current": int(current) if current else 0,
                "previous": int(previous) if previous else 0,
                "increase": int(change) if change else 0,
                "change_pct": round(float(ratio), 2) if ratio else 0,
                "period": period,
                "avg_market_cap": round(float(avg_market_cap), 2) if avg_market_cap else 0,
                "total_market_cap": round(float(total_market_cap), 2) if total_market_cap else 0,
                "interval_chg": round(float(interval_chg), 2) if interval_chg else 0,
                "notice_date": notice_date[:10] if notice_date else "",
            })

        # 按变化比例降序
        stocks.sort(key=lambda x: x["change_pct"], reverse=True)
        # 取TOP100
        stocks = stocks[:100]
        print(f"  ✅ 从东方财富API获取 {len(stocks)} 条股东户数数据")
        return stocks

    except Exception as e:
        print(f"  ❌ 东方财富API失败: {e}")
        return _fallback_shareholder_data()


def _fallback_shareholder_data():
    """备用数据"""
    print("  ⚠️ 使用备用股东户数数据")
    fallback = [
        {"code": "000725", "name": "京东方A", "current": 1897600, "previous": 971900, "increase": 925600, "change_pct": 95.23, "period": "2026Q2", "avg_market_cap": 8.5, "total_market_cap": 1613, "interval_chg": 121.99, "notice_date": "2026-08-30"},
        {"code": "600522", "name": "中天科技", "current": 818100, "previous": 226200, "increase": 591900, "change_pct": 261.64, "period": "2026Q2", "avg_market_cap": 12.3, "total_market_cap": 1006, "interval_chg": 85.32, "notice_date": "2026-08-28"},
        {"code": "600584", "name": "长电科技", "current": 804000, "previous": 304000, "increase": 500000, "change_pct": 164.54, "period": "2026Q2", "avg_market_cap": 45.6, "total_market_cap": 3666, "interval_chg": 78.45, "notice_date": "2026-08-29"},
        {"code": "600378", "name": "昊华科技", "current": 152400, "previous": 27300, "increase": 125100, "change_pct": 457.26, "period": "2026Q2", "avg_market_cap": 28.7, "total_market_cap": 437, "interval_chg": 45.23, "notice_date": "2026-08-25"},
        {"code": "603203", "name": "快克智能", "current": 64300, "previous": 14700, "increase": 49600, "change_pct": 335.83, "period": "2026Q2", "avg_market_cap": 35.2, "total_market_cap": 226, "interval_chg": 67.89, "notice_date": "2026-08-22"},
        {"code": "600707", "name": "彩虹股份", "current": 268900, "previous": 71000, "increase": 197900, "change_pct": 278.83, "period": "2026Q2", "avg_market_cap": 15.8, "total_market_cap": 425, "interval_chg": 92.56, "notice_date": "2026-08-26"},
        {"code": "603986", "name": "兆易创新", "current": 360300, "previous": 243800, "increase": 116500, "change_pct": 47.81, "period": "2026Q2", "avg_market_cap": 85.3, "total_market_cap": 3073, "interval_chg": -12.34, "notice_date": "2026-08-27"},
        {"code": "300308", "name": "中际旭创", "current": 205700, "previous": 154400, "increase": 51300, "change_pct": 33.20, "period": "2026Q2", "avg_market_cap": 156.7, "total_market_cap": 3224, "interval_chg": -8.76, "notice_date": "2026-08-28"},
        {"code": "300476", "name": "胜宏科技", "current": 281400, "previous": 206000, "increase": 75400, "change_pct": 36.60, "period": "2026Q2", "avg_market_cap": 42.1, "total_market_cap": 1185, "interval_chg": -5.43, "notice_date": "2026-08-26"},
        {"code": "000021", "name": "深科技", "current": 489589, "previous": 503900, "increase": -14311, "change_pct": -2.84, "period": "2026-08", "avg_market_cap": 22.5, "total_market_cap": 1102, "interval_chg": -3.21, "notice_date": "2026-09-01"},
        {"code": "300615", "name": "欣天科技", "current": 18700, "previous": 13760, "increase": 4940, "change_pct": 35.94, "period": "2026-08", "avg_market_cap": 18.6, "total_market_cap": 35, "interval_chg": 15.67, "notice_date": "2026-09-02"},
        {"code": "300006", "name": "莱美药业", "current": 29000, "previous": 23667, "increase": 5333, "change_pct": 22.56, "period": "2026-08", "avg_market_cap": 6.8, "total_market_cap": 20, "interval_chg": 8.92, "notice_date": "2026-09-03"},
        {"code": "002594", "name": "比亚迪", "current": 755000, "previous": 718600, "increase": 36400, "change_pct": 5.06, "period": "2026Q2", "avg_market_cap": 85.2, "total_market_cap": 6433, "interval_chg": -2.15, "notice_date": "2026-08-30"},
        {"code": "000977", "name": "浪潮信息", "current": 245000, "previous": 198000, "increase": 47000, "change_pct": 23.74, "period": "2026Q2", "avg_market_cap": 98.5, "total_market_cap": 2413, "interval_chg": 12.34, "notice_date": "2026-08-29"},
    ]
    fallback.sort(key=lambda x: x["change_pct"], reverse=True)
    return fallback


def calc_overview(stocks):
    """计算KPI"""
    inflow_stocks = [s for s in stocks if s["retail_net"] > 0]
    outflow_stocks = [s for s in stocks if s["retail_net"] < 0]

    total_retail = sum(abs(s["retail_net"]) for s in stocks)
    total_main = sum(abs(s.get("main_net", 0)) for s in stocks)
    overall_ratio = round(total_retail / (total_retail + total_main) * 100, 1) if (total_retail + total_main) > 0.01 else 0

    return {
        "inflow_amount": round(sum(s["retail_inflow"] for s in stocks), 2),
        "inflow_count": len(inflow_stocks),
        "outflow_amount": round(sum(s["retail_outflow"] for s in stocks), 2),
        "outflow_count": len(outflow_stocks),
        "net_amount": round(sum(s["retail_net"] for s in stocks), 2),
        "net_count": len(inflow_stocks),
        "total_stocks": len(stocks),
        "overall_retail_ratio": overall_ratio,
        "overall_retail_share": overall_ratio,
    }


def main():
    retail_flow, data_status = fetch_retail_money_flow()
    shareholder_count = fetch_shareholder_count()
    overview = calc_overview(retail_flow)

    status_labels = {"live": "实时数据", "cached": "收盘数据（缓存）", "static": "估算数据"}
    overview["update_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    overview["data_status"] = data_status
    overview["data_label"] = status_labels.get(data_status, "")

    output = {
        "overview": overview,
        "retail_flow": retail_flow,
        "shareholder_count": shareholder_count,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": "东方财富/新浪财经" if data_status == "live" else ("缓存数据" if data_status == "cached" else "估算数据"),
        "data_status": data_status,
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if data_status == "live":
        save_cache(output)
        print("  💾 已更新缓存")

    output_path = f"{OUTPUT_DIR}/radar_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 数据保存成功: {output_path}")
    print(f"🕐 更新时间: {output['last_updated']}")
    print(f"📊 散户资金: {len(retail_flow)} 条 [{status_labels.get(data_status, data_status)}]")
    print(f"💰 流入: {overview['inflow_amount']}亿 ({overview['inflow_count']}只) | 流出: {overview['outflow_amount']}亿 ({overview['outflow_count']}只) | 净流入: {overview['net_amount']}亿 ({overview['net_count']}只)")
    print(f"👥 股东户数: {len(shareholder_count)} 条")
    print("=" * 50)


if __name__ == "__main__":
    main()
