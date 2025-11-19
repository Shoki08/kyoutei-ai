import requests
import pandas as pd
import datetime
import json
import os
import time
import random
from bs4 import BeautifulSoup

# ==========================================
# 設定と定数
# ==========================================
BASE_URL = "https://www.boatrace.jp/owpc/pc/race"
DATA_DIR = "docs/data"
os.makedirs(DATA_DIR, exist_ok=True)

# iOS SafariやChromeを模倣したUser-Agentリスト [cite: 42]
USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]

class KyoteiPredictor:
    def __init__(self):
        self.today = datetime.date.today()
        self.date_str = self.today.strftime("%Y%m%d")

    def get_headers(self):
        return {"User-Agent": random.choice(USER_AGENTS)}

    def fetch_page(self, url):
        """汎用ページ取得メソッド：リトライ処理とエンコーディング自動判別 [cite: 43, 44]"""
        retries = 3
        for i in range(retries):
            try:
                resp = requests.get(url, headers=self.get_headers(), timeout=10)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding  # 文字化け対策
                return resp
            except requests.RequestException as e:
                print(f"Network Error ({url}): {e}, Retrying... ({i+1}/{retries})")
                time.sleep(2)
        return None

    def get_active_stadiums(self):
        """本日開催のレース場リストを取得 [cite: 46]"""
        url = f"{BASE_URL}/index?hd={self.date_str}"
        resp = self.fetch_page(url)
        if not resp: return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        stadiums = []
        
        # jcdパラメータを持つリンクを抽出
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            if "race_list" in href and "jcd=" in href:
                try:
                    # クエリパラメータ解析 (?jcd=01&...)
                    query = href.split('?')[1]
                    params = {p.split('=')[0]: p.split('=')[1] for p in query.split('&')}
                    if 'jcd' in params:
                        stadiums.append(params['jcd'])
                except IndexError:
                    continue
        return sorted(list(set(stadiums)))

    def get_race_details(self, jcd, race_no):
        """出走表と直前情報の取得・構造化 [cite: 50]"""
        list_url = f"{BASE_URL}/racelist?jcd={jcd}&no={race_no}&hd={self.date_str}"
        info_url = f"{BASE_URL}/beforeinfo?jcd={jcd}&no={race_no}&hd={self.date_str}"
        
        race_data = {
            "id": f"{self.date_str}-{jcd}-{race_no}",
            "jcd": jcd,
            "race_no": race_no,
            "racers": [],
            "weather": {"wind": 0, "wave": 0, "wind_dir": 0},
            "status": "future"
        }

        # 1. 直前情報の取得（気象データ）
        try:
            resp_info = self.fetch_page(info_url)
            if resp_info:
                soup = BeautifulSoup(resp_info.text, 'html.parser')
                # 簡易実装: 実際はHTML構造に合わせてクラス指定が必要
                # ここではシミュレーション用のロジックとして、風速・波高を安全側に設定
                race_data["weather"]["wind"] = 2  # 仮定値
                race_data["weather"]["wave"] = 2  # 仮定値
        except Exception as e:
            print(f"Info scrape error: {e}")

        # 2. 出走表の取得（Pandas read_html利用） [cite: 55]
        try:
            dfs = pd.read_html(list_url)
            racer_df = None
            for df in dfs:
                if len(df) == 6 and df.shape[1] > 5:
                    racer_df = df
                    break
            
            if racer_df is not None:
                for idx, row in racer_df.iterrows():
                    raw_row = [str(x) for x in row.values]
                    
                    # 級別判定
                    racer_class = "B1"
                    if "A1" in str(raw_row): racer_class = "A1"
                    elif "A2" in str(raw_row): racer_class = "A2"
                    elif "B2" in str(raw_row): racer_class = "B2"

                    # 選手データ構築
                    racer = {
                        "lane": idx + 1,
                        "class": racer_class,
                        "motor_pct": 30.0, # 実際は詳細パースが必要
                        "st": 0.17
                    }
                    race_data["racers"].append(racer)
            else:
                return None
        except Exception as e:
            print(f"Table parse error jcd={jcd} r={race_no}: {e}")
            return None
            
        return race_data

    def predict(self, data):
        """Solid / Rough ロジックの適用 [cite: 64-73]"""
        if not data or len(data["racers"]) < 6: return None

        wind = data["weather"].get("wind", 0)
        wave = data["weather"].get("wave", 0)
        boat1 = data["racers"][0] # 1号艇

        # 荒れる条件判定 [cite: 66]
        is_rough = False
        if wind >= 4 or wave >= 4 or boat1["class"] == "B1" or boat1["class"] == "B2":
            is_rough = True
        
        data["prediction_logic"] = "ROUGH" if is_rough else "SOLID"
        scores = []

        for r in data["racers"]:
            score = 100
            lane = r["lane"]

            # 基礎点
            if lane == 1: score += 50
            if lane == 2: score += 30
            if lane == 3: score += 20
            
            # 級別補正
            if r["class"] == "A1": score += 40
            elif r["class"] == "A2": score += 20

            # ロジック分岐
            if is_rough:
                # 荒れ想定: インの信頼度を下げる [cite: 69]
                if lane == 1: score -= 40
                # カド(4コース)やアウトのまくりを評価 [cite: 70]
                if lane in [4, 5, 6]:
                    score += 30 + (r["motor_pct"] * 0.5)
            else:
                # 堅い想定: イン信頼 [cite: 71]
                if lane == 1: score += 30
                score += (0.20 - r["st"]) * 100

            scores.append({"lane": lane, "score": score})

        # スコア順にソート
        scores.sort(key=lambda x: x["score"], reverse=True)

        # 買い目生成
        first = scores[0]["lane"]
        second = scores[1]["lane"]
        third = scores[2]["lane"]
        fourth = scores[3]["lane"]

        data["predictions"] = [
            f"{first}-{second}-{third}",
            f"{first}-{second}-{fourth}",
            f"{first}-{third}-{second}",
            f"{second}-{first}-{third}" # 抑え
        ]
        return data

    def run(self):
        print("Starting Scraping Job...")
        result_db = {}
        stadiums = self.get_active_stadiums()
        print(f"Active Stadiums: {stadiums}")

        for jcd in stadiums:
            result_db[jcd] = []
            # 全12レース処理
            for r in range(1, 13):
                print(f"Processing {jcd}R{r}...")
                raw_data = self.get_race_details(jcd, r)
                if raw_data:
                    prediction = self.predict(raw_data)
                    if prediction:
                        result_db[jcd].append(prediction)
                time.sleep(1) # 負荷軽減

        # JSON保存 [cite: 77]
        with open(f"{DATA_DIR}/latest_odds.json", "w", encoding="utf-8") as f:
            json.dump(result_db, f, ensure_ascii=False, indent=2)
        
        # 更新時刻保存
        with open(f"{DATA_DIR}/timestamp.txt", "w") as f:
            f.write(datetime.datetime.now().isoformat())

if __name__ == "__main__":
    bot = KyoteiPredictor()
    bot.run()