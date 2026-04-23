#!/usr/bin/env python3
"""
股票三大法人監控系統 v8 (Updated)
自動抓取三大法人買賣超數據，計算連買/連賣，並透過 Telegram 發送通知。

功能：
- 自動安裝缺失的依賴套件
- 抓取指定股票的三大法人數據
- 計算連續買賣天數
- 發送格式化的 Telegram 通知
"""

import os
import sys
import subprocess
import importlib

# ==========================================
# 自動依賴安裝
# ==========================================

def install_requirements():
    """檢查並自動安裝必要的套件"""
    required_packages = {
        'FinMind': 'FinMind',
        'requests': 'requests',
        'pandas': 'pandas',
    }
    
    missing_packages = []
    for import_name, package_name in required_packages.items():
        try:
            importlib.import_module(import_name)
            print(f"✓ {package_name} 已安裝")
        except ImportError:
            print(f"✗ {package_name} 未安裝，準備安裝...")
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"\n正在安裝缺失的套件: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q"] + missing_packages)
            print("✓ 所有套件安裝完成\n")
        except subprocess.CalledProcessError as e:
            print(f"✗ 安裝失敗: {e}")
            sys.exit(1)

# 執行自動安裝
install_requirements()

# 現在導入所有必要的模組
import requests
import pandas as pd
from datetime import datetime, timedelta
from FinMind.data import DataLoader

# ==========================================
# 配置區域
# ==========================================

# Telegram 配置 (從環境變數或直接設定)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# 持股清單 (預設範例: 台積電、鴻海、聯發科)
STOCK_LIST = os.environ.get("STOCK_LIST", "2330,2317,2454,3037,4958,3711,2308,2376,2347,9933").split(",")

# 監控天數 (預設: 15 天)
MONITOR_DAYS = int(os.environ.get("MONITOR_DAYS", "15"))

# ==========================================
# 核心功能
# ==========================================

def is_trading_day(date_str):
    """
    檢查是否為交易日
    簡單判斷: 排除週末 (假設台灣股市週一至週五交易)
    """
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    return date_obj.weekday() < 5  # 0-4 代表週一至週五

def get_institutional_data(stock_id, days=15):
    """獲取特定股票的三大法人數據"""
    try:
        dl = DataLoader()
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        print(f"  抓取 {stock_id} 的數據 ({start_date} 至 {end_date})...")
        df = dl.taiwan_stock_institutional_investors(
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )
        return df
    except Exception as e:
        print(f"  ✗ 抓取 {stock_id} 失敗: {e}")
        return None

def process_data(df):
    """
    處理數據並計算連買連賣
    
    返回:
        (results_dict, last_update_date)
        - results_dict: 包含各法人的淨買賣超與連續天數
        - last_update_date: 最後更新日期
    """
    if df is None or df.empty:
        return None, None
    
    # 計算淨買賣超 (買進 - 賣出)
    df['net_buy'] = df['buy'] - df['sell']
    
    # 轉換為以日期為索引，法人為欄位的表格
    pivot_df = df.pivot_table(index='date', columns='name', values='net_buy', aggfunc='sum')
    pivot_df = pivot_df.sort_index(ascending=False)  # 最新日期在前
    
    if pivot_df.empty:
        return None, None
    
    results = {}
    target_investors = {
        'Foreign_Investor': '外資',
        'Investment_Trust': '投信',
        'Dealer_self': '自營商'
    }
    
    for eng_name, chi_name in target_investors.items():
        if eng_name not in pivot_df.columns:
            results[chi_name] = {"net": 0, "consecutive": 0}
            continue
        
        series = pivot_df[eng_name]
        today_net = series.iloc[0]
        
        # 計算連續天數
        consecutive = 0
        if today_net > 0:
            for val in series:
                if val > 0:
                    consecutive += 1
                else:
                    break
        elif today_net < 0:
            for val in series:
                if val < 0:
                    consecutive -= 1
                else:
                    break
        
        results[chi_name] = {"net": today_net, "consecutive": consecutive}
    
    last_date = pivot_df.index[0]
    return results, last_date

def format_message(stock_id, results, update_date):
    """格式化 Telegram 訊息"""
    if results is None:
        return f"❌ 無法獲取 {stock_id} 的數據\n"
    
    msg = f"📊 *股票代號: {stock_id}* ({update_date})\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    for name, data in results.items():
        net = data['net'] / 1000  # 換算成張數
        con = data['consecutive']
        
        if net > 0:
            status = "買超"
            emoji = "🔴"
        elif net < 0:
            status = "賣超"
            emoji = "🟢"
        else:
            status = "無交易"
            emoji = "⚪"
        
        con_text = ""
        if con > 1:
            con_text = f" 🔥連買 {con} 天"
        elif con < -1:
            con_text = f" ❄️連賣 {abs(con)} 天"
        
        msg += f"{emoji} {name}: {status} {abs(net):.1f} 張{con_text}\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    return msg

def send_telegram_notification(message):
    """發送 Telegram 通知"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n⚠️  Telegram 配置缺失，僅輸出訊息內容：\n")
        print(message)
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✓ Telegram 通知發送成功！")
            return True
        else:
            print(f"✗ Telegram 發送失敗 (HTTP {response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"✗ 發送異常: {e}")
        return False

def main():
    """主程式"""
    print("=" * 50)
    print("股票三大法人監控系統 v8 (Updated)")
    print("=" * 50)
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"監控股票: {', '.join(STOCK_LIST)}")
    print(f"監控天數: {MONITOR_DAYS} 天")
    print("=" * 50 + "\n")
    
    full_report = ""
    success_count = 0
    
    for stock_id in STOCK_LIST:
        print(f"正在處理 {stock_id}...")
        df = get_institutional_data(stock_id, days=MONITOR_DAYS)
        
        if df is not None and not df.empty:
            analysis, last_date = process_data(df)
            if analysis is not None:
                msg = format_message(stock_id, analysis, last_date)
                full_report += msg
                success_count += 1
                print(f"  ✓ {stock_id} 處理完成")
            else:
                print(f"  ✗ {stock_id} 數據處理失敗")
        else:
            print(f"  ✗ 無法獲取 {stock_id} 的數據")
        print()
    
    print("=" * 50)
    if full_report:
        print(f"成功處理 {success_count}/{len(STOCK_LIST)} 檔股票\n")
        send_telegram_notification(full_report)
    else:
        print("✗ 沒有可報告的數據")
    print("=" * 50)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程式被中斷")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ 發生未預期的錯誤: {e}")
        sys.exit(1)
