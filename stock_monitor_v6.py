import requests
import datetime
import pandas as pd
import os
import sys
import time

# 配置
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_institutional_summary(date_str):
    """抓取三大法人買賣超金額總計 (億元)"""
    url = f"https://www.twse.com.tw/rwd/zh/fund/BFI82U?date={date_str}&response=json"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        if data.get("stat") == "OK":
            summary = {}
            for row in data.get("data"):
                name = row[0]
                val = float(row[3].replace(',', '')) / 100000000 # 換算為億
                summary[name] = val
            return summary
    except:
        return None

def get_stock_details(date_str):
    """抓取個股買賣超詳細數據"""
    url = f"https://www.twse.com.tw/rwd/zh/fund/T86?date={date_str}&selectType=ALL&response=json"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        data = res.json()
        if data.get("stat") == "OK":
            df = pd.DataFrame(data.get("data"), columns=data.get("fields"))
            return df
    except:
        return None
    return None

def main():
    now = datetime.datetime.now()
    today_str = now.strftime("%Y%m%d")
    
    print(f"開始執行股票監控任務 v6 (執行時間: {now.strftime('%H:%M:%S')})...")
    
    # 1. 抓取今日大盤總計 (通常 15:00 前就有初步數據，或維持昨日)
    summary = get_institutional_summary(today_str)
    summary_date = today_str
    if not summary:
        # 嘗試找最近的有大盤數據的一天
        for i in range(1, 5):
            prev_date = (now - datetime.timedelta(days=i)).strftime("%Y%m%d")
            summary = get_institutional_summary(prev_date)
            if summary:
                summary_date = prev_date
                break

    # 2. 抓取個股詳細數據 (具備自動回溯機制)
    stock_df = get_stock_details(today_str)
    stock_date = today_str
    is_fallback = False
    
    if stock_df is None or stock_df.empty:
        print("今日個股數據尚未更新，啟動自動回溯機制...")
        is_fallback = True
        # 往回找最近一個有詳細個股數據的交易日
        for i in range(1, 7):
            prev_date = (now - datetime.timedelta(days=i)).strftime("%Y%m%d")
            stock_df = get_stock_details(prev_date)
            if stock_df is not None and not stock_df.empty:
                stock_date = prev_date
                print(f"成功回溯至 {stock_date} 的個股數據。")
                break

    # 3. 組合訊息
    msg = f"📊 *三大法人買賣監測報告*\n\n"
    msg += f"📅 報告日期： {today_str[:4]}/{today_str[4:6]}/{today_str[6:]}\n"
    msg += f"🕐 產生時間： {now.strftime('%H:%M:%S')}\n"
    msg += f"💻 系統版本： v6.0.0 (自動回溯穩定版)\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 大盤資訊
    msg += "🏛️ *大盤三大法人總計*\n"
    if summary:
        total = sum(summary.values())
        msg += f"📈 數據日期： {summary_date[:4]}/{summary_date[4:6]}/{summary_date[6:]}\n"
        msg += f"外資: {summary.get('外資及陸資(不含外資自營商)', 0):+.2f} 億\n"
        msg += f"投信: {summary.get('投信', 0):+.2f} 億\n"
        msg += f"合計: {total:+.2f} 億\n\n"
    else:
        msg += "⚠️ 大盤數據暫無資訊\n\n"

    # 個股資訊
    msg += "📊 *個股買賣超精選*\n"
    if is_fallback:
        msg += f"💡 _(今日數據尚未發布，自動顯示 {stock_date[4:6]}/{stock_date[6:]} 資訊)_\n\n"
    else:
        msg += f"📈 數據日期： {stock_date[:4]}/{stock_date[4:6]}/{stock_date[6:]}\n\n"

    if stock_df is not None and not stock_df.empty:
        # 處理欄位
        foreign_col = [c for c in stock_df.columns if "外陸資買賣超" in c][0]
        stock_df[foreign_col] = stock_df[foreign_col].astype(str).str.replace(',', '').astype(float)
        
        # 買超前 8 名
        top_buy = stock_df.sort_values(by=foreign_col, ascending=False).head(8)
        for _, row in top_buy.iterrows():
            val = int(row[foreign_col] / 1000) # 換算為張
            msg += f"• `{row['證券代號']}` {row['證券名稱']}: {val:+,} 張\n"
    else:
        msg += "⚠️ 暫無個股明細資訊\n"
        
    msg += "\n━━━━━━━━━━━━━━━━━━━━\n"
    msg += "📌 資料來源： 台灣證券交易所\n"
    msg += f"⏰ 更新時間： {now.strftime('%H:%M:%S')}"

    # 4. 發送 Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    
    print("\n--- 產生的完整報告內容 ---")
    print(msg)
    print("------------------------\n")

if __name__ == "__main__":
    main()
