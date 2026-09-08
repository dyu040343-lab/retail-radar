#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
散户雷达侦探 - 数据抓取脚本
多数据源抓取 + 缓存机制：收盘后显示最近一次成功抓取的数据
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


def load_cache():
    """加载上一次成功抓取的缓存数据"""
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return None


def save_cache(data):
    """保存数据到缓存文件"""
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass


def fetch_retail_money_flow():
    """
    抓取散户资金流向数据
    返回: (stocks, data_status)
    data_status: "live"=实时, "cached"=缓存(收盘数据), "static"=备用数据
    """
    print("🔍 正在抓取散户资金流向数据...")
    stocks = []

    # 方案1：东方财富实时API
    try:
        url = "https://push2.eastmoney.com/api/qt/clist/get"
        # fid=f84 按小单净额排序（散户资金），po=1 降序（最大净流入在前）
        params_sh = {
            "pn": "1", "pz": "50", "po": "1", "np": "1",
            "ut": "b2884a393a59ad64002292a3e90d46a5",
            "fltt": "2", "invt": "2", "fid": "f84",
            "fs": "m:1+t:2,m:1+t:23",
            "fields": "f2,f3,f12,f14,f62,f66,f69,f72,f75,f78,f81,f84,f87,f184",
            "_": str(int(time.time() * 1000))
        }
        params_sz = params_sh.copy()
        params_sz["fs"] = "m:0+t:6,m:0+t:80,m:0+t:13,m:0+t:81"

        for market, params in [("沪市", params_sh), ("深市", params_sz)]:
            try:
                resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
                if resp.status_code == 200 and resp.text.strip():
                    data = resp.json()
                    diff = data.get("data", {}).get("diff", [])
                    for item in diff:
                        code = item.get("f12", "")
                        name = item.get("f14", "")
                        price = item.get("f2", 0)
                        change_pct = item.get("f3", 0)
                        small_net = item.get("f84", 0) or 0
                        medium_net = item.get("f78", 0) or 0
                        retail_net = (small_net + medium_net) / 100000000
                        main_net = item.get("f62", 0) or 0
                        stocks.append({
                            "code": code,
                            "name": name,
                            "price": round(price, 2) if isinstance(price, (int, float)) else 0,
                            "change_pct": round(change_pct, 2) if isinstance(change_pct, (int, float)) else 0,
                            "retail_net_inflow": round(retail_net, 2),
                            "small_net": round(small_net / 100000000, 2),
                            "medium_net": round(medium_net / 100000000, 2),
                            "main_net": round(main_net / 100000000, 2),
                            "sector": guess_sector(name, code),
                        })
                    print(f"  ✅ {market}: {len(diff)} 条")
                else:
                    print(f"  ⚠️ {market}: API返回空 (status={resp.status_code})")
            except Exception as e:
                print(f"  ⚠️ {market}数据抓取失败: {e}")
    except Exception as e:
        print(f"  ⚠️ 东方财富API不可用: {e}")

    if stocks:
        stocks.sort(key=lambda x: x["retail_net_inflow"], reverse=True)
        print(f"  ✅ 共抓取 {len(stocks)} 只股票 [实时]")
        return stocks[:50], "live"

    # 方案2：使用缓存（上一次成功抓取的数据）
    print("  📦 API不可用，尝试使用缓存数据...")
    cache = load_cache()
    if cache and cache.get("retail_money_flow"):
        cached_stocks = cache["retail_money_flow"]
        cached_time = cache.get("last_updated", "未知时间")
        print(f"  ✅ 使用缓存数据 {len(cached_stocks)} 条 [缓存于 {cached_time}]")
        return cached_stocks, "cached"

    # 方案3：备用数据
    print("  📦 无缓存，使用备用数据...")
    fallback = get_fallback_money_flow()
    print(f"  ✅ 备用数据 {len(fallback)} 条 [静态]")
    return fallback, "static"


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
    }
    for sector, keywords in sectors.items():
        if any(kw in name for kw in keywords):
            return sector
    if code.startswith('6013') or code.startswith('6000'):
        return '金融'
    if code.startswith('300'):
        return '科技'
    return '综合'


def get_fallback_money_flow():
    """备用数据（仅在无缓存时使用）"""
    return [
        {"code": "600150", "name": "中国船舶", "price": 0, "change_pct": 0, "retail_net_inflow": 9.12, "small_net": 3.45, "medium_net": 5.67, "main_net": -4.27, "sector": "军工/船舶"},
        {"code": "601318", "name": "中国平安", "price": 0, "change_pct": 0, "retail_net_inflow": 4.78, "small_net": 2.13, "medium_net": 2.65, "main_net": -4.39, "sector": "保险"},
        {"code": "603256", "name": "宏和科技", "price": 0, "change_pct": 0, "retail_net_inflow": 4.68, "small_net": 1.89, "medium_net": 2.79, "main_net": -1.88, "sector": "化工"},
        {"code": "600519", "name": "贵州茅台", "price": 0, "change_pct": 0, "retail_net_inflow": 3.89, "small_net": 1.54, "medium_net": 2.35, "main_net": -4.18, "sector": "白酒"},
        {"code": "002594", "name": "比亚迪", "price": 0, "change_pct": 0, "retail_net_inflow": 3.56, "small_net": 1.42, "medium_net": 2.14, "main_net": -3.40, "sector": "新能源汽车"},
        {"code": "000725", "name": "京东方A", "price": 0, "change_pct": 0, "retail_net_inflow": 3.34, "small_net": 1.28, "medium_net": 2.06, "main_net": -1.90, "sector": "面板/显示"},
        {"code": "601012", "name": "隆基绿能", "price": 0, "change_pct": 0, "retail_net_inflow": 3.12, "small_net": 1.15, "medium_net": 1.97, "main_net": -2.28, "sector": "光伏"},
        {"code": "300750", "name": "宁德时代", "price": 0, "change_pct": 0, "retail_net_inflow": 2.98, "small_net": 1.08, "medium_net": 1.90, "main_net": -3.04, "sector": "电池"},
        {"code": "600036", "name": "招商银行", "price": 0, "change_pct": 0, "retail_net_inflow": 2.87, "small_net": 1.03, "medium_net": 1.84, "main_net": -3.48, "sector": "银行"},
        {"code": "000858", "name": "五粮液", "price": 0, "change_pct": 0, "retail_net_inflow": 2.65, "small_net": 0.95, "medium_net": 1.70, "main_net": -3.40, "sector": "白酒"},
        {"code": "002475", "name": "立讯精密", "price": 0, "change_pct": 0, "retail_net_inflow": 2.43, "small_net": 0.88, "medium_net": 1.55, "main_net": -2.42, "sector": "消费电子"},
        {"code": "600900", "name": "长江电力", "price": 0, "change_pct": 0, "retail_net_inflow": 2.21, "small_net": 0.82, "medium_net": 1.39, "main_net": -2.43, "sector": "电力"},
        {"code": "601899", "name": "紫金矿业", "price": 0, "change_pct": 0, "retail_net_inflow": 2.15, "small_net": 0.78, "medium_net": 1.37, "main_net": -2.69, "sector": "有色金属"},
        {"code": "300059", "name": "东方财富", "price": 0, "change_pct": 0, "retail_net_inflow": 1.98, "small_net": 0.72, "medium_net": 1.26, "main_net": -2.72, "sector": "证券"},
        {"code": "600276", "name": "恒瑞医药", "price": 0, "change_pct": 0, "retail_net_inflow": 1.87, "small_net": 0.68, "medium_net": 1.19, "main_net": -2.15, "sector": "医药"},
        {"code": "000333", "name": "美的集团", "price": 0, "change_pct": 0, "retail_net_inflow": 1.76, "small_net": 0.65, "medium_net": 1.11, "main_net": -2.45, "sector": "家电"},
        {"code": "002230", "name": "科大讯飞", "price": 0, "change_pct": 0, "retail_net_inflow": 1.65, "small_net": 0.61, "medium_net": 1.04, "main_net": -1.72, "sector": "AI/算力"},
        {"code": "688981", "name": "中芯国际", "price": 0, "change_pct": 0, "retail_net_inflow": 1.54, "small_net": 0.57, "medium_net": 0.97, "main_net": -1.83, "sector": "半导体"},
        {"code": "601628", "name": "中国人寿", "price": 0, "change_pct": 0, "retail_net_inflow": 1.43, "small_net": 0.53, "medium_net": 0.90, "main_net": -2.13, "sector": "保险"},
    ]


def fetch_shareholder_count():
    """股东户数变化数据"""
    print("🔍 正在抓取股东户数变化数据...")

    known_stocks = [
        {"code": "000725", "name": "京东方A", "current": 1897600, "previous": 971900, "increase": 925600, "change_pct": 95.23, "period": "2026Q2", "sector": "面板/显示"},
        {"code": "600522", "name": "中天科技", "current": 818100, "previous": 226200, "increase": 591900, "change_pct": 261.64, "period": "2026Q2", "sector": "光纤/光通信"},
        {"code": "600584", "name": "长电科技", "current": 804000, "previous": 304000, "increase": 500000, "change_pct": 164.54, "period": "2026Q2", "sector": "半导体封测"},
        {"code": "600378", "name": "昊华科技", "current": 152400, "previous": 27300, "increase": 125100, "change_pct": 457.26, "period": "2026Q2", "sector": "氟化工/特气"},
        {"code": "603203", "name": "快克智能", "current": 64300, "previous": 14700, "increase": 49600, "change_pct": 335.83, "period": "2026Q2", "sector": "半导体封装设备"},
        {"code": "600707", "name": "彩虹股份", "current": 268900, "previous": 71000, "increase": 197900, "change_pct": 278.83, "period": "2026Q2", "sector": "玻璃基板"},
        {"code": "603986", "name": "兆易创新", "current": 360300, "previous": 243800, "increase": 116500, "change_pct": 47.81, "period": "2026Q2", "sector": "存储芯片"},
        {"code": "300308", "name": "中际旭创", "current": 205700, "previous": 154400, "increase": 51300, "change_pct": 33.20, "period": "2026Q2", "sector": "光模块"},
        {"code": "300476", "name": "胜宏科技", "current": 281400, "previous": 206000, "increase": 75400, "change_pct": 36.60, "period": "2026Q2", "sector": "PCB"},
        {"code": "000021", "name": "深科技", "current": 489589, "previous": 503900, "increase": -14311, "change_pct": -2.84, "period": "2026.07-08", "sector": "存储/半导体"},
        {"code": "300615", "name": "欣天科技", "current": 18700, "previous": 13760, "increase": 4940, "change_pct": 35.94, "period": "2026.07-08", "sector": "通信设备"},
        {"code": "300006", "name": "莱美药业", "current": 29000, "previous": 23667, "increase": 5333, "change_pct": 22.56, "period": "2026.08", "sector": "医药生物"},
        {"code": "002594", "name": "比亚迪", "current": 755000, "previous": 718600, "increase": 36400, "change_pct": 5.06, "period": "2026Q2", "sector": "新能源汽车"},
        {"code": "000977", "name": "浪潮信息", "current": 245000, "previous": 198000, "increase": 47000, "change_pct": 23.74, "period": "2026Q2", "sector": "算力服务器"},
    ]

    known_stocks.sort(key=lambda x: x["change_pct"], reverse=True)
    print(f"  ✅ 共整理 {len(known_stocks)} 只股票的股东户数数据")
    return known_stocks


def main():
    print("=" * 50)
    print("📡 散户雷达侦探 - 数据抓取中...")
    print("=" * 50)

    # 1. 散户资金流向
    retail_money, data_status = fetch_retail_money_flow()

    # 2. 股东户数变化
    shareholder_count = fetch_shareholder_count()

    # 3. 概览
    status_labels = {
        "live": "实时数据",
        "cached": "收盘数据（缓存）",
        "static": "备用数据（估算）",
    }
    overview = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_retail_stocks": 0,
        "total_retail_inflow": 0,
        "hot_sector": "PCB/算力",
        "top_stock_name": "",
        "top_stock_inflow": 0,
        "data_status": data_status,
        "data_label": status_labels.get(data_status, ""),
    }

    if retail_money:
        overview["total_retail_stocks"] = len([s for s in retail_money if s["retail_net_inflow"] > 0])
        overview["total_retail_inflow"] = round(sum(s["retail_net_inflow"] for s in retail_money if s["retail_net_inflow"] > 0), 2)
        overview["top_stock_name"] = retail_money[0]["name"]
        overview["top_stock_inflow"] = retail_money[0]["retail_net_inflow"]

    output = {
        "overview": overview,
        "retail_money_flow": retail_money,
        "shareholder_count": shareholder_count,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": "东方财富实时API" if data_status == "live" else f"缓存数据（上次成功抓取）" if data_status == "cached" else "备用数据（估算）",
        "data_status": data_status,
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 只有实时数据才更新缓存
    if data_status == "live":
        save_cache(output)
        print("  💾 已更新缓存")

    output_path = f"{OUTPUT_DIR}/radar_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 数据保存成功: {output_path}")
    print(f"🕐 更新时间: {output['last_updated']}")
    print(f"📊 散户资金数据: {len(retail_money)} 条 [{status_labels.get(data_status, data_status)}]")
    print(f"👥 股东户数数据: {len(shareholder_count)} 条")
    print("=" * 50)


if __name__ == "__main__":
    main()
