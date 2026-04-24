#!/usr/bin/env python3
import os
import sys
import subprocess
import importlib

def install_requirements():
    required_packages = {'FinMind': 'FinMind', 'requests': 'requests', 'pandas': 'pandas'}
    for import_name, package_name in required_packages.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package_name])

install_requirements()

import requests
import pandas as pd
from datetime import datetime, timedelta
from FinMind.data import DataLoader

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
STOCK_LIST = os.environ.get("STOCK_LIST", "2330,2317,2454,3711,9933,4104").split(",")
MONITOR_DAYS = int(os.environ.get("MONITOR_DAYS", "15"))

def main():
    print(f"🚀 開始處理 {len(STOCK_LIST)} 檔股票...")
    dl = DataLoader()
    
    try:
        print("🔍 獲取股票基本資訊...")
        df_info = dl.taiwan_stock_info()
    except Exception as e:
        print(f"⚠️ 獲取股票資訊失敗: {e}")
        df_info = pd.DataFrame()

    full_report = ""
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date_price = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    start_date_inst = (datetime.now() - timedelta(days=MONITOR_DAYS)).strftime('%Y-%m-%d')

    for stock_id in STOCK_LIST:
        print(f"📈 正在處理 {stock_id}...")
        try:
            # 1. 股票名稱
            name = stock_id
            if not df_info.empty:
                info = df_info[df_info['stock_id'] == stock_id]
                if not info.empty: name = info.iloc[0]['stock_name']
            
            # 2. 股價資訊
            price_data = None
            try:
                df_p = dl.taiwan_stock_daily(stock_id=stock_id, start_date=start_date_price, end_date=end_date)
                if df_p is not None and not df_p.empty:
                    latest = df_p.iloc[-1]
                    if len(df_p) >= 2:
                        prev = df_p.iloc[-2]
                        change_pct = ((latest['close'] - prev['close']) / prev['close']) * 100
                        vol_change = "量增" if latest['Trading_Volume'] > prev['Trading_Volume'] else "量減"
                    else:
                        change_pct, vol_change = 0, "N/A"
                    price_data = {'close': latest['close'], 'volume': int(latest['Trading_Volume'] / 1000), 'change_pct': change_pct, 'vol_change': vol_change, 'date': latest['date']}
            except Exception: pass

            # 3. 法人資訊
            inst_msg = ""
            date_str = end_date
            try:
                df_i = dl.taiwan_stock_institutional_investors(stock_id=stock_id, start_date=start_date_inst, end_date=end_date)
                if df_i is not None and not df_i.empty:
                    df_i['net_buy'] = df_i['buy'] - df_i['sell']
                    pivot = df_i.pivot_table(index='date', columns='name', values='net_buy', aggfunc='sum').sort_index(ascending=False)
                    date_str = pivot.index[0]
                    mapping = {'Foreign_Investor': '外資', 'Investment_Trust': '投信', 'Dealer_self': '自營商'}
                    for eng, chi in mapping.items():
                        if eng in pivot.columns:
                            series = pivot[eng]
                            today_net = series.iloc[0] / 1000
                            con = 0
                            if today_net > 0:
                                for v in series:
                                    if v > 0: con += 1
                                    else: break
                            elif today_net < 0:
                                for v in series:
                                    if v < 0: con -= 1
                                    else: break
                            status = "買超" if today_net > 0 else "賣超" if today_net < 0 else "無交易"
                            emoji = "🔴" if today_net > 0 else "🟢" if today_net < 0 else "⚪"
                            con_text = f" 🔥連買 {con} 天" if con > 1 else f" ❄️連賣 {abs(con)} 天" if con < -1 else ""
                            inst_msg += f"{emoji} {chi}: {status} {abs(today_net):.1f} 張{con_text}\n"
            except Exception: pass

            if inst_msg:
                msg = f"📊 *{name} ({stock_id})*\n📅 {date_str}\n"
                if price_data:
                    p_emoji = "📈" if price_data['change_pct'] > 0 else "📉" if price_data['change_pct'] < 0 else "➡️"
                    msg += f"💰 收盤: ${price_data['close']:.2f} {p_emoji} {price_data['change_pct']:+.2f}%\n📈 成交量: {price_data['volume']:,} 張 ({price_data['vol_change']})\n"
                msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n" + inst_msg + "━━━━━━━━━━━━━━━━━━━━━━━━\n"
                full_report += msg + "\n"
                print(f"✅ {stock_id} 處理完成")
            else:
                print(f"❌ {stock_id} 無法人數據")
                
        except Exception as e:
            print(f"❌ {stock_id} 錯誤: {e}")

    if full_report:
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            print("📤 正在發送 Telegram 通知...")
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": full_report, "parse_mode": "Markdown"})
        else:
            print("\n--- 最終報告 ---\n")
            print(full_report)
    else:
        print("📭 沒有可報告的數據")

if __name__ == "__main__":
    main()
