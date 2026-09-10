#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小散研究院 - 数据抓取脚本 v3
数据源：akshare（封装东方财富，四档完整：超大单/大单/中单/小单）
散户 = 小单，主力 = 超大单 + 大单 + 中单
"""

import json
import os
import time
import requests
from datetime import datetime

OUTPUT_DIR = "data"
CACHE_FILE = f"{OUTPUT_DIR}/radar_data_cache.json"

EASTMONEY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
}


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


def to_float(val):
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def fetch_from_akshare():
    """新浪财经批量接口 - 全市场资金流数据"""
    print("🔍 [数据源] 新浪财经批量接口（资金流）...")

    SINA_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "http://vip.stock.finance.sina.com.cn/",
        "Accept": "*/*",
    }

    all_items = []

    for attempt in range(3):
        try:
            all_items = []
            for page in [1, 2, 3]:
                url = "https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/MoneyFlow.ssl_bkzj_ssggzj"
                params = {
                    "page": page,
                    "num": 2000,
                    "sort": "netamount",
                    "asc": "0",
                    "bankuai": "ssgzj",
                    "nodeId": "0",
                    "fenlei": "0",
                    "bankuaiType": "ssgzj",
                }
                resp = requests.get(url, params=params, headers=SINA_HEADERS, timeout=15)
                resp.encoding = "gbk"
                items = json.loads(resp.text)
                if not items:
                    break
                all_items.extend(items)
                print(f"  📄 第{page}页: {len(items)} 条")

            if all_items:
                print(f"  📊 新浪返回 {len(all_items)} 条")
                break
        except Exception as e:
            print(f"  ⚠️ 第{attempt+1}/3次获取失败: {e}")
            if attempt == 2:
                print("  📦 新浪不可用，尝试缓存...")
                return []
            time.sleep(2)
    else:
        return []

    # 调试: 打印第一条数据的所有字段
    if all_items:
        print(f"  🔧 样本字段: {list(all_items[0].keys())}")

    stocks = []
    for item in all_items:
        code = str(item.get("symbol", "")).strip()
        name = str(item.get("name", "")).strip()
        if not code or not name:
            continue

        # 新浪字段: r0=特大单, r1=大单, r2=中单, r3=小单/散户
        r0_in = to_float(item.get("r0_in", 0))
        r0_out = to_float(item.get("r0_out", 0))
        r1_in = to_float(item.get("r1_in", 0))
        r1_out = to_float(item.get("r1_out", 0))
        r2_in = to_float(item.get("r2_in", 0))
        r2_out = to_float(item.get("r2_out", 0))
        r3_in = to_float(item.get("r3_in", 0))
        r3_out = to_float(item.get("r3_out", 0))

        price = to_float(item.get("price", 0))
        change_pct = to_float(item.get("changepercent", 0))

        yi = 100000000
        super_net_yi = round((r0_in - r0_out) / yi, 4)
        large_net_yi = round((r1_in - r1_out) / yi, 4)
        medium_net_yi = round((r2_in - r2_out) / yi, 4)
        small_net_yi = round((r3_in - r3_out) / yi, 4)

        retail_net = small_net_yi
        main_net = round(super_net_yi + large_net_yi + medium_net_yi, 4)

        retail_inflow = max(retail_net, 0)
        retail_outflow = max(-retail_net, 0)

        total_amount = round(to_float(item.get("amount", 0)) / yi, 2)

        total_abs = abs(retail_net) + abs(main_net)
        dynamic_ratio = round(retail_net / total_abs * 100, 1) if total_abs > 0.001 else 0

        # 净占比（各档净额占总成交额的比例）
        super_pct = round(super_net_yi / total_amount * 100, 2) if total_amount > 0.01 else 0
        large_pct = round(large_net_yi / total_amount * 100, 2) if total_amount > 0.01 else 0
        medium_pct = round(medium_net_yi / total_amount * 100, 2) if total_amount > 0.01 else 0
        small_pct = round(small_net_yi / total_amount * 100, 2) if total_amount > 0.01 else 0

        stocks.append({
            "code": code,
            "name": name,
            "price": round(price, 2) if price else 0,
            "change_pct": round(change_pct, 2) if change_pct else 0,
            "retail_inflow": round(retail_inflow, 4),
            "retail_outflow": round(retail_outflow, 4),
            "retail_net": round(retail_net, 4),
            "main_net": round(main_net, 4),
            "super_net": super_net_yi,
            "large_net": large_net_yi,
            "medium_net": medium_net_yi,
            "small_net": small_net_yi,
            "super_pct": super_pct,
            "large_pct": large_pct,
            "medium_pct": medium_pct,
            "small_pct": small_pct,
            "total_amount": total_amount,
            "dynamic_ratio": dynamic_ratio,
            "sector": guess_sector(name, code),
            "source": "sina",
        })

    print(f"  ✅ 解析完成: {len(stocks)} 条")
    return stocks


def fetch_retail_money_flow():
    print("=" * 50)
    print("📡 小散研究院 - 数据抓取中...")
    print("=" * 50)

    stocks = fetch_from_akshare()
    if stocks and len(stocks) > 50:
        print(f"  ✅ 使用 akshare 全市场数据（{len(stocks)} 条）")
        return stocks, "live"

    print("📦 akshare 不可用，尝试缓存...")
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
    """备用数据 - 含四档明细"""
    base = [
        ("600150", "中国船舶", 9.12, "军工/船舶"),
        ("601318", "中国平安", 4.78, "保险"),
        ("603256", "宏和科技", 4.68, "化工"),
        ("600519", "贵州茅台", 3.89, "白酒"),
        ("002594", "比亚迪", 3.56, "新能源汽车"),
        ("000725", "京东方A", 3.34, "面板/显示"),
        ("601012", "隆基绿能", 3.12, "光伏"),
        ("300750", "宁德时代", 2.98, "电池"),
        ("600036", "招商银行", 2.87, "银行"),
        ("000858", "五粮液", 2.65, "白酒"),
        ("002475", "立讯精密", 2.43, "消费电子"),
        ("600900", "长江电力", 2.21, "电力"),
        ("601899", "紫金矿业", 2.15, "有色金属"),
        ("300059", "东方财富", 1.98, "证券"),
        ("600276", "恒瑞医药", 1.87, "医药"),
        ("000333", "美的集团", 1.76, "家电"),
        ("002230", "科大讯飞", 1.65, "AI/算力"),
        ("688981", "中芯国际", 1.54, "半导体"),
        ("601628", "中国人寿", 1.43, "保险"),
        ("000977", "浪潮信息", 1.35, "算力服务器"),
        ("600584", "长电科技", 1.28, "半导体封测"),
        ("600522", "中天科技", 1.15, "光纤/光通信"),
        ("300308", "中际旭创", 1.08, "光模块"),
        ("300476", "胜宏科技", 0.98, "PCB"),
        ("603986", "兆易创新", 0.89, "存储芯片"),
        ("600707", "彩虹股份", 0.82, "玻璃基板"),
        ("002415", "海康威视", 0.75, "安防"),
        ("000063", "中兴通讯", 0.68, "通信设备"),
        ("600809", "山西汾酒", 0.61, "白酒"),
        ("000021", "深科技", 0.55, "存储/半导体"),
        ("600009", "上海机场", 0.48, "航空"),
        ("601857", "中国石油", 0.42, "石油"),
        ("600028", "中国石化", 0.38, "石油"),
        ("000651", "格力电器", 0.35, "家电"),
        ("002241", "歌尔股份", 0.32, "消费电子"),
        ("300015", "爱尔眼科", 0.28, "医疗"),
        ("603259", "药明康德", 0.25, "医药"),
        ("600690", "海尔智家", 0.22, "家电"),
        ("002352", "顺丰控股", 0.18, "物流"),
        ("600048", "保利发展", 0.15, "地产"),
        ("000002", "万科A", -0.12, "地产"),
    ]
    stocks = []
    for code, name, net, sector in base:
        super_n = round(net * 0.3, 4)
        large_n = round(net * 0.25, 4)
        medium_n = round(net * 0.15, 4)
        small_n = round(net, 4)
        main_n = round(super_n + large_n + medium_n, 4)
        total_abs = abs(small_n) + abs(main_n)
        dyn = round(small_n / total_abs * 100, 1) if total_abs > 0.001 else 0
        total_amt = round(abs(net) * 10, 2)
        stocks.append({
            "code": code, "name": name,
            "price": 0, "change_pct": 0,
            "retail_inflow": max(small_n, 0),
            "retail_outflow": max(-small_n, 0),
            "retail_net": small_n,
            "main_net": main_n,
            "super_net": super_n,
            "large_net": large_n,
            "medium_net": medium_n,
            "small_net": small_n,
            "super_pct": 0, "large_pct": 0, "medium_pct": 0, "small_pct": 0,
            "total_amount": total_amt,
            "dynamic_ratio": dyn,
            "sector": sector,
        })
    return stocks


def fetch_shareholder_count():
    """从东方财富数据中心获取股东户数变化数据"""
    print("🔍 正在从东方财富获取股东户数变化数据...")
    import requests
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

    try:
        resp = requests.get(url, params=params, headers=EASTMONEY_HEADERS, timeout=15)
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

            if not code or not name or previous == 0:
                continue

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

        stocks.sort(key=lambda x: x["change_pct"], reverse=True)
        stocks = stocks[:100]
        print(f"  ✅ 从东方财富API获取 {len(stocks)} 条股东户数数据")
        return stocks

    except Exception as e:
        print(f"  ❌ 东方财富API失败: {e}")
        return _fallback_shareholder_data()


def _fallback_shareholder_data():
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
    """计算KPI汇总"""
    inflow_stocks = [s for s in stocks if s.get("retail_net", 0) > 0]
    outflow_stocks = [s for s in stocks if s.get("retail_net", 0) < 0]

    total_retail_net_abs = sum(abs(s.get("retail_net", 0)) for s in stocks)
    total_main_net_abs = sum(abs(s.get("main_net", 0)) for s in stocks)
    dynamic_ratio = round(total_retail_net_abs / (total_retail_net_abs + total_main_net_abs) * 100, 1) if (total_retail_net_abs + total_main_net_abs) > 0.01 else 0

    total_super = round(sum(s.get("super_net", 0) for s in stocks), 4)
    total_large = round(sum(s.get("large_net", 0) for s in stocks), 4)
    total_medium = round(sum(s.get("medium_net", 0) for s in stocks), 4)
    total_small = round(sum(s.get("small_net", 0) for s in stocks), 4)

    return {
        "inflow_amount": round(sum(s.get("retail_inflow", 0) for s in stocks), 2),
        "inflow_count": len(inflow_stocks),
        "outflow_amount": round(sum(s.get("retail_outflow", 0) for s in stocks), 2),
        "outflow_count": len(outflow_stocks),
        "net_amount": round(sum(s.get("retail_net", 0) for s in stocks), 2),
        "net_count": len(inflow_stocks),
        "total_stocks": len(stocks),
        "dynamic_ratio": dynamic_ratio,
        "super_total": total_super,
        "large_total": total_large,
        "medium_total": total_medium,
        "small_total": total_small,
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
        "data_source": "akshare/东方财富" if data_status == "live" else ("缓存数据" if data_status == "cached" else "估算数据"),
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
    print(f"📈 四档: 超大单{overview['super_total']}亿 | 大单{overview['large_total']}亿 | 中单{overview['medium_total']}亿 | 小单{overview['small_total']}亿")
    print(f"👥 股东户数: {len(shareholder_count)} 条")
    print("=" * 50)


if __name__ == "__main__":
    main()
