import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from FinMind.data import DataLoader

# ==========================================
# 配置區域
# ==========================================
# 請在此填入您的 Telegram Bot Token 與 Chat ID
# 如果未填入，腳本將僅在終端機輸出結果
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# 持股清單 (範例：台積電, 鴻海, 聯發科, 日月光, 技嘉, 台達電, 聯強, 中鼎, 元太, 欣興, 臻鼎KY, 英業達, 中信金, 凌華, 康霈, 統一台股增長)
# 您可以根據需求修改此清單
STOCK_LIST = ["2330", "2317", "2454", "3711", "2376",  "2308", "2347", "9933", "8069", "3037", "4958", "2356", "2891", "6166", "6919", "00981A"
              
              

# ==========================================
# 核心功能
# ==========================================

def get_institutional_data(stock_id, days=15):
    """獲取特定股票的三大法人數據"""
    dl = DataLoader()
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    df = dl.taiwan_stock_institutional_investors(
        stock_id=stock_id,
        start_date=start_date,
        end_date=end_date
    )
    return df

def process_data(df):
    """處理數據並計算連買連賣"""
    if df.empty:
        return None
    
    # 將數據按日期和法人類型彙總
    # 這裡我們關注的是 'Foreign_Investor' (外資), 'Investment_Trust' (投信), 'Dealer_self' (自營商)
    # 我們計算每日的淨買賣超 (buy - sell)
    df['net_buy'] = df['buy'] - df['sell']
    
    # 轉換為以日期為索引，法人為欄位的表格
    pivot_df = df.pivot_table(index='date', columns='name', values='net_buy', aggfunc='sum')
    pivot_df = pivot_df.sort_index(ascending=False) # 最新日期在前
    
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
                if val > 0: consecutive += 1
                else: break
        elif today_net < 0:
            for val in series:
                if val < 0: consecutive -= 1
                else: break
        
        results[chi_name] = {"net": today_net, "consecutive": consecutive}
        
    return results, pivot_df.index[0]

def format_message(stock_id, results, update_date):
    """格式化 Telegram 訊息"""
    msg = f"📊 *股票代號: {stock_id}* ({update_date})\n"
    msg += "----------------------------\n"
    
    for name, data in results.items():
        net = data['net'] / 1000 # 換算成張數 (假設單位是股)
        con = data['consecutive']
        
        status = "買超" if net > 0 else "賣超" if net < 0 else "無交易"
        emoji = "🔴" if net > 0 else "🟢" if net < 0 else "⚪"
        
        con_text = ""
        if con > 1:
            con_text = f" (🔥連買 {con} 天)"
        elif con < -1:
            con_text = f" (❄️連賣 {abs(con)} 天)"
            
        msg += f"{emoji} {name}: {status} {abs(net):.1f} 張{con_text}\n"
    
    return msg

def send_telegram_notification(message):
    """發送 Telegram 通知"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram 配置缺失，僅輸出訊息內容：")
        print(message)
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Telegram 通知發送成功！")
        else:
            print(f"Telegram 發送失敗: {response.text}")
    except Exception as e:
        print(f"發送異常: {e}")

def main():
    print(f"執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    full_report = ""
    for stock_id in STOCK_LIST:
        print(f"正在處理 {stock_id}...")
        df = get_institutional_data(stock_id)
        if df is not None and not df.empty:
            analysis, last_date = process_data(df)
            full_report += format_message(stock_id, analysis, last_date) + "\n"
        else:
            print(f"無法獲取 {stock_id} 的數據")
            
    if full_report:
        send_telegram_notification(full_report)
    else:
        print("沒有可報告的數據")

if __name__ == "__main__":
    main()