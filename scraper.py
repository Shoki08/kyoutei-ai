import requests
import pandas as pd
import datetime
import json
import os
import time
import random
import re
from bs4 import BeautifulSoup

# ==========================================
# 設定
# ==========================================
BASE_URL = "https://www.boatrace.jp/owpc/pc/race"
DATA_DIR = "docs/data"
os.makedirs(DATA_DIR, exist_ok=True)

# User-Agentリスト
USER_AGENTS = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]

class KyoteiPredictor:
    def __init__(self):
        # 【重要】GitHub Actions(UTC)でも日本時間(JST)の日付を取得する設定
        t_delta = datetime.timedelta(hours=9)
        JST = datetime.timezone(t_delta, 'JST')
        self.today = datetime.datetime.now(JST).date()
        self.date_str = self.today.strftime("%Y%m%d")
        print(f"Target Date (JST): {self.date_str}")

    def get_headers(self):
        return {"User-Agent": random.choice(USER_AGENTS)}

    def fetch_page(self, url):
        """汎用ページ取得"""
        retries = 3
        for i in range(retries):
            try:
                resp = requests.get(url, headers=self.get_headers(), timeout=10)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding
                return resp
            except Exception as e:
                print(f"Warning: Network Error ({url}) - {e}")
                time.sleep(2)
        return None

    def get_active_stadiums(self):
        """開催中のレース場コードを取得"""
        url = f"{BASE_URL}/index?hd={self.date_str}"
        resp = self.fetch_page(url)
        if not resp: return []
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        stadiums = []
        
        links = soup.find_all('a', href=True)
        for link in links:
            href = link['href']
            if "race_list" in href and "jcd=" in href:
                try:
                    query_part = href.split('?')[1] if '?' in href else href
                    params = {p.split('=')[0]: p.split('=')[1] for p in query_part.split('&') if '=' in p}
                    if 'jcd' in params:
                        stadiums.append(params['jcd'])
                except:
                    continue
        return sorted(list(set(stadiums)))

    def parse_weather(self, soup):
        """気象情報を抽出"""
        weather_data = {"wind": 2, "wave": 2, "wind_dir": 0} # デフォルト値
        try:
            text = soup.get_text()
            wind_match = re.search(r"風速.*?(\d+)m", text)
            if wind_match: weather_data["wind"] = int(wind_match.group(1))
            wave_match = re.search(r"波高.*?(\d+)cm", text)
            if wave_match: weather_data["wave"] = int(wave_match.group(1))
        except Exception as e:
            print(f"Weather parse warning: {e}")
        return weather_data

    def get_race_details(self, jcd, race_no):
        list_url = f"{BASE_URL}/racelist?jcd={jcd}&no={race_no}&hd={self.date_str}"
        info_url = f"{BASE_URL}/beforeinfo?jcd={jcd}&no={race_no}&hd={self.date_str}"
        
        race_data = {
            "id": f"{self.date_str}-{jcd}-{race_no}",
            "jcd": jcd,
            "race_no": race_no,
            "racers": [],
            "weather": {"wind": 0, "wave": 0},
            "status": "future"
        }

        # 1. 気象情報
        try:
            resp_info = self.fetch_page(info_url)
            if resp_info:
                soup = BeautifulSoup(resp_info.text, 'html.parser')
                race_data["weather"] = self.parse_weather(soup)
        except Exception:
            pass

        # 2. 出走表
        try:
            dfs = pd.read_html(list_url)
            racer_df = None
            for df in dfs:
                if len(df) == 6:
                    racer_df = df
                    break
            
            if racer_df is not None:
                for idx, row in racer_df.iterrows():
                    row_str = str(row.values)
                    # 級別判定
                    racer_class = "B1"
                    if "A1" in row_str: racer_class = "A1"
                    elif "A2" in row_str: racer_class = "A2"
                    elif "B2" in row_str: racer_class = "B2"
                    
                    race_data["racers"].append({
                        "lane": idx + 1,
                        "class": racer_class,
                        "motor_pct": 30.0, 
                        "st": 0.17
                    })
            else:
                return None
        except Exception as e:
            print(f"Table error ({jcd}R{race_no}): {e}")
            return None
            
        return race_data

    def predict(self, data):
        """本番用予測ロジック（Solid/Rough）"""
        if not data or len(data["racers"]) < 6: return None

        wind = data["weather"].get("wind", 0)
        wave = data["weather"].get("wave", 0)
        boat1 = data["racers"][0]

        is_rough = False
        # 荒れる条件: 風速4m以上, 波高4cm以上, 1号艇がB級
        if wind >= 4 or wave >= 4 or boat1["class"] in ["B1", "B2"]:
            is_rough = True
        
        data["prediction_logic"] = "ROUGH" if is_rough else "SOLID"
        scores = []

        for r in data["racers"]:
            score = 100
            lane = r["lane"]
            
            # 基礎点
            score += {1: 50, 2: 30, 3: 20}.get(lane, 0)
            # 級別補正
            if r["class"] == "A1": score += 40
            elif r["class"] == "A2": score += 20

            if is_rough:
                # 荒れ: イン信頼度ダウン、カド(4)・アウト(5,6)評価アップ
                if lane == 1: score -= 40
                if lane >= 4: score += 35
            else:
                # 堅実: イン信頼、ST重視
                if lane == 1: score += 30
                score += (0.20 - r["st"]) * 100

            scores.append({"lane": lane, "score": score})

        scores.sort(key=lambda x: x["score"], reverse=True)
        
        o = [s["lane"] for s in scores]
        data["predictions"] = [
            f"{o[0]}-{o[1]}-{o[2]}",
            f"{o[0]}-{o[1]}-{o[3]}",
            f"{o[0]}-{o[2]}-{o[1]}",
            f"{o[1]}-{o[0]}-{o[2]}"
        ]
        return data

    def run(self):
        print(f"Starting REAL Scraping Job for {self.date_str}...")
        result_db = {}
        stadiums = self.get_active_stadiums()
        
        if not stadiums:
            print("No active races found for today. Exiting.")
            # ファイルを空にせず、既存データを残すか、空配列を保存するか
            # ここでは「開催なし」として空ファイルを保存する
            with open(f"{DATA_DIR}/latest_odds.json", "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
            return

        print(f"Active Stadiums: {stadiums}")
        for jcd in stadiums:
            result_db[jcd] = []
            # 全12レース
            for r in range(1, 13):
                print(f"Processing {jcd}R{r}...")
                raw_data = self.get_race_details(jcd, r)
                if raw_data:
                    prediction = self.predict(raw_data)
                    if prediction:
                        result_db[jcd].append(prediction)
                time.sleep(1) # 負荷軽減

        # JSON保存
        with open(f"{DATA_DIR}/latest_odds.json", "w", encoding="utf-8") as f:
            json.dump(result_db, f, ensure_ascii=False, indent=2)
        print(f"Success. Data saved to {DATA_DIR}/latest_odds.json")

if __name__ == "__main__":
    KyoteiPredictor().run()
