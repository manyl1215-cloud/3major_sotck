#!/usr/bin/env python3
"""
股票三大法人監控系統 v8 (Final Robust)
自動抓取三大法人買賣超數據、股價、成交量等資訊，計算連買/連賣，並透過 Telegram 發送通知。

功能：
- 自動安裝缺失的依賴套件
- 抓取指定股票的三大法人數據、股價、成交量
- 計算連續買賣天數、漲跌幅、量增量減
- 強化容錯機制：即使股價抓取失敗，仍確保法人數據通知發送
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
STOCK_LIST = os.environ.get("STOCK_LIST", "2330,2317,2454,3711,2308,2376,2347,9933,8069,3037,4958,2356,2891,2881,2882,2834,2451,6166,4104,1476,2409,00981A,0050").split(",")

# 監控天數 (預設: 15 天)
MONITOR_DAYS = int(os.environ.get("MONITOR_DAYS", "15"))

# ==========================================
# 核心功能
# ==========================================

def get_stock_info(stock_id):
    """獲取股票的中文名稱與產業類別"""
    try:
        dl = DataLoader()
        df_info = dl.taiwan_stock_info()
        stock_info = df_info[df_info['stock_id'] == stock_id]
        
        if not stock_info.empty:
            # 取第一筆記錄
            row = stock_info.iloc[0]
            return {
                'name': row['stock_name'],
                'industry': row['industry_category']
            }
    except Exception as e:
        pass  # 靜默失敗，使用預設值
    
    return {'name': stock_id, 'industry': '未知'}

def get_today_stock_price(stock_id):
    """獲取今日的股價、成交量與漲跌幅"""
    try:
        dl = DataLoader()
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        
        df = dl.taiwan_stock_daily(
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )
        
        if df is None or df.empty:
            return None
        
        # 取最新的交易日資料
        latest = df.iloc[-1]
        
        # 計算漲跌幅
        if len(df) >= 2:
            prev_close = df.iloc[-2]['close']
            today_close = latest['close']
            change_pct = ((today_close - prev_close) / prev_close) * 100
            
            # 計算量增量減
            prev_volume = df.iloc[-2]['Trading_Volume']
            today_volume = latest['Trading_Volume']
            volume_change = "量增" if today_volume > prev_volume else "量減" if today_volume < prev_volume else "持平"
        else:
            change_pct = 0
            volume_change = "無前日"
        
        return {
            'close': latest['close'],
            'volume': latest['Trading_Volume'],
            'volume_change': volume_change,
            'change_pct': change_pct,
            'date': latest['date']
        }
    except Exception as e:
        # 靜默失敗，返回 None
        return None

def get_institutional_data(stock_id, days=15):
    """獲取特定股票的三大法人數據"""
    try:
        dl = DataLoader()
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        df = dl.taiwan_stock_institutional_investors(
            stock_id=stock_id,
            start_date=start_date,
            end_date=end_date
        )
        return df
    except Exception as e:
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

def format_message(stock_id, stock_info, price_info, institutional_analysis, update_date):
    """
    格式化 Telegram 訊息
    
    注意：此函數已強化容錯機制，即使 price_info 為 None，仍會產生訊息
    """
    if institutional_analysis is None:
        return None  # 如果沒有法人數據，不產生訊息
    
    # 股票基本資訊
    stock_name = stock_info['name']
    industry = stock_info['industry']
    
    msg = f"📊 *{stock_name} ({stock_id})* | {industry}\n"
    msg += f"📅 {update_date}\n"
    
    # 股價與成交量資訊（可選，如果失敗不會中斷訊息）
    if price_info:
        try:
            close_price = price_info['close']
            volume = price_info['volume']
            volume_change = price_info['volume_change']
            change_pct = price_info['change_pct']
            
            # 漲跌顏色
            if change_pct > 0:
                change_emoji = "📈"
            elif change_pct < 0:
                change_emoji = "📉"
            else:
                change_emoji = "➡️"
            
            msg += f"💰 收盤: ${close_price:.2f} {change_emoji} {change_pct:+.2f}%\n"
            msg += f"📈 成交量: {volume:,} 張 ({volume_change})\n"
        except Exception as e:
            # 股價資訊格式化失敗，仍繼續產生法人數據部分
            pass
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    # 三大法人資訊
    for name, data in institutional_analysis.items():
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
    print("=" * 60)
    print("股票三大法人監控系統 v8 (Final Robust)")
    print("=" * 60)
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"監控股票: {', '.join(STOCK_LIST)}")
    print(f"監控天數: {MONITOR_DAYS} 天")
    print("=" * 60 + "\n")
    
    full_report = ""
    success_count = 0
    
    for stock_id in STOCK_LIST:
        print(f"正在處理 {stock_id}...")
        
        try:
            # 獲取股票基本資訊
            stock_info = get_stock_info(stock_id)
            print(f"  ✓ 股票名稱: {stock_info['name']}")
            
            # 獲取今日股價資訊 (可選，失敗不影響)
            price_info = get_today_stock_price(stock_id)
            if price_info:
                print(f"  ✓ 股價資訊已取得")
            else:
                print(f"  ⚠️  股價資訊無法取得（將跳過此部分）")
            
            # 獲取法人數據 (必須)
            df = get_institutional_data(stock_id, days=MONITOR_DAYS)
            
            if df is not None and not df.empty:
                analysis, last_date = process_data(df)
                if analysis is not None:
                    msg = format_message(stock_id, stock_info, price_info, analysis, last_date)
                    if msg:  # 確保訊息不為空
                        full_report += msg
                        success_count += 1
                        print(f"  ✓ {stock_id} 處理完成，訊息已加入待發送隊列")
                    else:
                        print(f"  ✗ {stock_id} 訊息格式化失敗")
                else:
                    print(f"  ✗ {stock_id} 數據處理失敗")
            else:
                print(f"  ✗ 無法獲取 {stock_id} 的法人數據")
        except Exception as e:
            print(f"  ✗ 處理 {stock_id} 時發生異常: {e}")
        
        print()
    
    print("=" * 60)
    if full_report:
        print(f"成功處理 {success_count}/{len(STOCK_LIST)} 檔股票\n")
        print("正在發送 Telegram 通知...\n")
        send_telegram_notification(full_report)
    else:
        print("✗ 沒有可報告的數據")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n程式被中斷")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ 發生未預期的錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(
