import requests
import datetime
import pandas as pd
import os
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

def get_recent_trading_days(target_date, count=5):
    """取得最近的交易日列表"""
    days = []
    current = target_date
    while len(days) < count:
        # 簡單排除週末
        if current.weekday() < 5:
            days.append(current.strftime("%Y%m%d"))
        current -= datetime.timedelta(days=1)
    return days

def main():
    now = datetime.datetime.now()
    today_str = now.strftime("%Y%m%d")
    
    print(f"開始執行股票監控任務 v7 (執行時間: {now.strftime('%H:%M:%S')})...")
    
    # 1. 抓取今日大盤總計
    summary = get_institutional_summary(today_str)
    summary_date = today_str
    if not summary:
        for i in range(1, 5):
            prev_date = (now - datetime.timedelta(days=i)).strftime("%Y%m%d")
            summary = get_institutional_summary(prev_date)
            if summary:
                summary_date = prev_date
                break

    # 2. 抓取多日歷史數據以計算連買/連賣
    recent_days = get_recent_trading_days(now, count=7) # 多抓幾天備用
    history_dfs = {}
    
    # 優先嘗試抓取今日，若無則回溯
    latest_df = get_stock_details(today_str)
    latest_date = today_str
    
    if latest_df is None or latest_df.empty:
        for d in recent_days[1:]:
            latest_df = get_stock_details(d)
            if latest_df is not None and not latest_df.empty:
                latest_date = d
                break
    
    if latest_df is None or latest_df.empty:
        print("無法取得任何個股數據。")
        return

    history_dfs[latest_date] = latest_df
    
    # 抓取過去幾天的數據做比對
    idx = recent_days.index(latest_date)
    compare_days = recent_days[idx+1 : idx+6]
    for d in compare_days:
        df = get_stock_details(d)
        if df is not None and not df.empty:
            history_dfs[d] = df
            
    sorted_history_dates = sorted(history_dfs.keys(), reverse=True)

    # 3. 組合訊息
    msg = f"📊 *三大法人買賣監測報告*\n\n"
    msg += f"📅 報告日期： {today_str[:4]}/{today_str[4:6]}/{today_str[6:]}\n"
    msg += f"💻 系統版本： v7.0.0 (連買連賣強化版)\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # 大盤資訊
    if summary:
        total = sum(summary.values())
        msg += "🏛️ *大盤三大法人總計*\n"
        msg += f"📈 數據日期： {summary_date[:4]}/{summary_date[4:6]}/{summary_date[6:]}\n"
        msg += f"外資: {summary.get('外資及陸資(不含外資自營商)', 0):+.2f} 億\n"
        msg += f"投信: {summary.get('投信', 0):+.2f} 億\n"
        msg += f"合計: {total:+.2f} 億\n\n"

    # 個股資訊
    msg += "📊 *個股外資動向精選*\n"
    msg += f"📈 數據日期： {latest_date[4:6]}/{latest_date[6:]}\n\n"

    # 處理欄位
    foreign_col = [c for c in latest_df.columns if "外陸資買賣超" in c][0]
    latest_df[foreign_col] = latest_df[foreign_col].astype(str).str.replace(',', '').astype(float)
    
    # 買超前 10 名
    top_buy = latest_df.sort_values(by=foreign_col, ascending=False).head(10)
    
    for _, row in top_buy.iterrows():
        sid, sname = row["證券代號"], row["證券名稱"]
        val = int(row[foreign_col] / 1000) # 換算為張
        
        # 計算連買天數
        streak = 0
        for d in sorted_history_dates:
            df = history_dfs[d]
            s_row = df[df["證券代號"] == sid]
            if not s_row.empty:
                s_val = float(str(s_row.iloc[0][foreign_col]).replace(',', ''))
                if s_val > 0: streak += 1
                else: break
            else: break
        
        streak_label = ""
        if streak >= 5: streak_label = f" 🏆 (連買 {streak} 天)"
        elif streak >= 3: streak_label = f" 🔥 (連買 {streak} 天)"
        elif streak == 2: streak_label = f" ✨ (連買 2 天)"
        
        msg += f"• `{sid}` {sname.strip()}: {val:+,} 張{streak_label}\n"
        
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
