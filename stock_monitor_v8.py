#!/usr/bin/env python3
"""
股票三大法人監控系統 v8 (Batch)
支援分段發送，解決 Telegram 訊息長度限制問題。
每 5 檔股票自動分段發送一則訊息。
"""

import os
import sys
import subprocess
import importlib
import time

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
STOCK_LIST = os.environ.get("STOCK_LIST", "2330,2317,2454,3711,2308,2376,2347,9933,8069,3037,4958,2356,2891,2881,2882,2834,2451,6166,4104,1476,2409,00981A,0050").split(",")
MONITOR_DAYS = int(os.environ.get("MONITOR_DAYS", "15"))
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "5"))  # 每批發送的股票數
REQUEST_DELAY = float(os.environ.get("REQUEST_DELAY", "0.5"))  # 請求間隔（秒）

def send_telegram(message):
    """發送單則 Telegram 訊息"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[本地輸出]\n{message}")
        return True
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        response = requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"},
            timeout=10
        )
        if response.status_code == 200:
            print("✅ 訊息發送成功")
            return True
        else:
            print(f"❌ 發送失敗 (HTTP {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ 發送異常: {e}")
        return False

def get_stock_data(stock_id, dl, df_info, end_date, start_date_price, start_date_inst):
    """獲取單檔股票的所有資訊"""
    try:
        # 1. 股票名稱
        name = stock_id
        if not df_info.empty:
            info = df_info[df_info['stock_id'] == stock_id]
            if not info.empty:
                name = info.iloc[0]['stock_name']
        
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
                price_data = {
                    'close': latest['close'],
                    'volume': int(latest['Trading_Volume'] / 1000),
                    'change_pct': change_pct,
                    'vol_change': vol_change,
                    'date': latest['date']
                }
        except Exception:
            pass
        
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
        except Exception:
            pass
        
        if inst_msg:
            msg = f"📊 *{name} ({stock_id})*\n📅 {date_str}\n"
            if price_data:
                p_emoji = "📈" if price_data['change_pct'] > 0 else "📉" if price_data['change_pct'] < 0 else "➡️"
                msg += f"💰 收盤: ${price_data['close']:.2f} {p_emoji} {price_data['change_pct']:+.2f}%\n📈 成交量: {price_data['volume']:,} 張 ({price_data['vol_change']})\n"
            msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n" + inst_msg + "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            return msg
        
        return None
    except Exception as e:
        print(f"❌ {stock_id} 錯誤: {e}")
        return None

def main():
    print(f"🚀 開始處理 {len(STOCK_LIST)} 檔股票（分批發送模式，每批 {BATCH_SIZE} 檔）...")
    
    dl = DataLoader()
    
    try:
        print("🔍 獲取股票基本資訊...")
        df_info = dl.taiwan_stock_info()
    except Exception as e:
        print(f"⚠️ 獲取股票資訊失敗: {e}")
        df_info = pd.DataFrame()
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date_price = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    start_date_inst = (datetime.now() - timedelta(days=MONITOR_DAYS)).strftime('%Y-%m-%d')
    
    # 分批處理股票
    batch_messages = []
    current_batch = ""
    batch_count = 0
    
    for idx, stock_id in enumerate(STOCK_LIST, 1):
        print(f"📈 [{idx}/{len(STOCK_LIST)}] 正在處理 {stock_id}...")
        
        msg = get_stock_data(stock_id, dl, df_info, end_date, start_date_price, start_date_inst)
        
        if msg:
            current_batch += msg + "\n"
            batch_count += 1
            print(f"✅ {stock_id} 成功")
        else:
            print(f"❌ {stock_id} 無法人數據")
        
        # 每達到 BATCH_SIZE 或是最後一檔，就發送一批
        if batch_count >= BATCH_SIZE or idx == len(STOCK_LIST):
            if current_batch.strip():
                batch_messages.append(current_batch)
                print(f"\n📦 第 {len(batch_messages)} 批準備發送（包含 {batch_count} 檔股票）")
                current_batch = ""
                batch_count = 0
        
        # 避免 API 被限制，每次請求間隔
        time.sleep(REQUEST_DELAY)
    
    # 發送所有批次
    if batch_messages:
        print(f"\n📤 開始發送 {len(batch_messages)} 則訊息...")
        for batch_idx, batch_msg in enumerate(batch_messages, 1):
            print(f"📨 發送第 {batch_idx}/{len(batch_messages)} 則訊息...")
            send_telegram(batch_msg)
            time.sleep(1)  # 訊息間隔
    else:
        print("📭 沒有可報告的數據")

if __name__ == "__main__":
    main()
