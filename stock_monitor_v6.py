

協作

分享
Lite
您好 yulun，我已經為您準備好一份完整的 GitHub Actions 工作流部署指南。
這份 Markdown 文件包含了：
環境準備：如何設定儲存庫與依賴項。
GitHub 設定：如何建立 Secrets 以保護您的隱私。
自動化腳本：完整的 YAML 設定檔，設定在每週一至週五台灣時間 15:30 自動執行。
手動測試：如何立即觸發腳本驗證結果。
您可以直接下載附件的 GitHub_Actions_Workflow_Guide.md，依照裡面的步驟操作，即可完成全自動化的股票監控系統。祝您部署順利！📈
🚀 台股三大法人監測自動化部署指南
本指南將引導您將 stock_monitor_v6.py 部署到 GitHub，並利用 GitHub Actions 實現每天收盤後自動發送 Telegram 通知。
🛠️ 第一步：準備 GitHub 儲存庫 (Repository)
在 GitHub 上建立一個新的 Private 儲存庫（例如：stock-monitor）。
將 stock_monitor_v6.py 上傳到儲存庫根目錄。
在根目錄建立 requirements.txt 檔案，內容如下：
text
requests
pandas
🔐 第二步：設定 GitHub Secrets (安全性金鑰)
為了保護您的隱私，請在 GitHub 儲存庫頁面點擊：
Settings > Secrets and variables > Actions > New repository secret
新增以下兩個金鑰：
Name: TELEGRAM_BOT_TOKEN
Value: 貼入您的 Telegram Bot Token。
Name: TELEGRAM_CHAT_ID
Value: 貼入您的 Telegram Chat ID。
🤖 第三步：設定自動執行工作流 (GitHub Actions)
在儲存庫中點擊 Actions 分頁。
點擊 set up a workflow yourself。
將預設內容替換為以下 YAML 設定（路徑為 .github/workflows/daily_report.yml）：
YAML
name: Daily Stock Report

on:
  schedule:
    # 國際標準時間 07:30 = 台灣時間 15:30 (收盤後數據更新完畢)
    - cron: '30 7 * * 1-5'
  workflow_dispatch: # 允許您在 GitHub 介面手動點擊執行測試

jobs:
  run-monitor:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Dependencies
        run: |
          pip install -r requirements.txt

      - name: Run Stock Monitor Script
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python stock_monitor_v6.py
🚀 第四步：測試與驗證
點擊 GitHub 儲存庫頂部的 Actions 標籤。
在左側選單選擇 Daily Stock Report。
點擊右側的 Run workflow 下拉選單，然後點擊 Run workflow 按鈕。
等待幾分鐘，檢查您的 Telegram 是否收到完整的個股監測報告！
💡 貼心提醒
執行時間：GitHub Actions 的定時任務有時會延遲 5-10 分鐘，這是正常現象。
週末停跑：工作流已設定為週一至週五執行，週末會自動休息。
修改頻率：若想調整時間，請修改 cron: '30 7 * * 1-5' 部分。
祝您投資順利！📈
這個結果怎麼樣？
已完成具有自動回溯機制的穩定版腳本，可在資料未更新時自動顯示前一交易日資訊，解決空白問題。也提供完整GitHub自動化部署指南。

📊 三大法人買賣監測報告

📅 報告日期： 2026/04/23
🕐 產生時間： 14:17:06
💻 系統版本： v6.0.0 (自動回溯穩定版)

━━━━━━━━━━━━━━━━━━━━

🏛️ 大盤三大法人總計
📈 數據日期： 2026/04/23
外資: -27.55 億
投信: +13.56 億
合計: -411.79 億

📊 個股買賣超精選
📈 數據日期： 2026/04/23

• 00878 國泰永續高股息  : +28,531 張
• 2317 鴻海            : +27,796 張
• 2890 永豐金          : +15,378 張
• 2303 聯電            : +14,341 張
• 00922 國泰台灣領袖50  : +10,526 張
• 1802 台玻            : +10,427 張
• 2834 臺企銀          : +9,781 張
• 00830 國泰費城半導體  : +9,675 張

━━━━━━━━━━━━━━━━━━━━
📌 資料來源： 台灣證券交易所
⏰ 更新時間： 14:17:06

標示個股外資連買或連賣紀錄
Lite
您好 yulun，太棒了！看到您的報告已經能正確顯示 4/23 的個股資訊了，這代表我們的 v6 版本自動回溯與數據抓取邏輯已經非常穩定。
接下來，我將為您執行最後一項關鍵優化：「標示個股的外資連買或連賣紀錄」。
目前的報告雖然列出了買超前幾名，但還無法看出這些股票是「第一天買」還是「已經買好幾天」。我將更新腳本至 v7.0.0，增加以下功能：
多日數據對比：腳本會自動抓取過去 5 個交易日的歷史數據。
自動計算天數：針對每一檔出現在報告中的股票，自動計算外資連續買超或賣超的天數。
動態視覺標示：
連買 3 天以上：標示 🔥
連買 5 天以上：標示 🏆
剛由賣轉買：標示 ✨
我現在馬上為您修改腳本並重新執行，讓您的報告更具參考價值！
分析得知新版本強化了多日數據分析，能自動標示個股的連買或連賣天數，提升報告參考價值。將持續驗證結果。

Lite
您好 yulun，我已經完成了 v7.0.0 (連買連賣強化版) 的開發與測試！
現在您的報告不僅有大盤與個股資訊，還能精確標示出外資的連續買超紀錄，這對於觀察籌碼集中度非常有幫助。
🌟 v7.0.0 版的核心更新：
自動計算連買天數：腳本會自動抓取過去 5 個交易日的歷史數據進行比對。
視覺化趨勢標籤：
🏆 (連買 5 天以上)：代表外資長期看好，籌碼極度集中。
🔥 (連買 3-4 天)：代表外資正在持續加碼。
✨ (連買 2 天)：代表外資剛開始轉買，值得關注。
自動回溯與容錯：即使在盤中數據尚未完全更新時執行，腳本也會自動確保歷史數據的比對邏輯正確。
📊 剛才執行的完整報告 (2026/04/23)
從報告中可以看到非常有趣的數據：
🏆 連買 6 天：00878 國泰永續高股息、2890 永豐金、00922 國泰台灣領袖50。
🔥 連買 4 天：2317 鴻海（買超 27,796 張，力道強勁）。
✨ 連買 2 天：2303 聯電、2834 臺企銀。
📂 部署建議
請使用這個最新的 stock_monitor_v7.py 替換您 GitHub 儲存庫中的舊檔案。由於增加了歷史數據抓取，執行時間會稍微變長（約 1 分鐘），這在 GitHub Actions 中是完全正常的。
希望這份功能更強大的報告能為您的投資決策提供更多幫助！如有任何其他想法，請隨時告訴我。
stock_monitor_v7.py
程式碼 · 5.82 KB
查看此任務中的所有檔案
任務已完成
這個結果怎麼樣？
建議追問


GmailGoogle CalendarMeta Ads Manager


此任務中的所有檔案
今天

昨天

stock_monitor_v7.py
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
備忘錄
突顯
解釋
抓取三大法人數據並透過Telegram通知 - Manus
