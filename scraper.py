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

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
]

STADIUM_BIAS = {
    "01": "STRONG_INS", "02": "WEAK_INS", "03": "WEAK_INS", "04": "WEAK_INS", "05": "NORMAL",
    "06": "WEAK_INS", "07": "STRONG_INS", "08": "NORMAL", "09": "NORMAL", "10": "NORMAL",
    "11": "NORMAL", "12": "STRONG_INS", "13": "NORMAL", "14": "WEAK_INS", "15": "NORMAL",
    "16": "STRONG_INS", "17": "NORMAL", "18": "STRONG_INS", "19": "STRONG_INS", "20": "NORMAL",
    "21": "STRONG_INS", "22": "NORMAL", "23": "NORMAL", "24": "STRONG_INS"
}

class KyoteiPredictor:
    def __init__(self):
        t_delta = datetime.timedelta(hours=9)
        JST = datetime.timezone(t_delta, 'JST')
        self.today = datetime.datetime.now(JST).date()
        self.date_str = self.today.strftime("%Y%m%d")
        print(f"Target Date (JST): {self.date_str}")

    def get_headers(self):
        return {"User-Agent": random.choice(USER_AGENTS)}

    def fetch_page(self, url):
        for i in range(3):
            try:
                resp = requests.get(url, headers=self.get_headers(), timeout=10)
                resp.raise_for_status()
                resp.encoding = resp.apparent_encoding
                return resp
            except Exception:
                time.sleep(2)
        return None

    def get_active_stadiums(self):
        url = f"{BASE_URL}/index?hd={self.date_str}"
        resp = self.fetch_page(url)
        if not resp: return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        stadiums = []
        for link in soup.find_all('a', href=True):
            if "race_list" in link['href'] and "jcd=" in link['href']:
                try:
                    jcd = link['href'].split('jcd=')[1].split('&')[0]
                    stadiums.append(jcd)
                except: continue
        return sorted(list(set(stadiums)))

    def get_odds(self, jcd, race_no):
        """【新機能】3連単オッズを取得して辞書化する"""
        url = f"{BASE_URL}/odds3t?jcd={jcd}&no={race_no}&hd={self.date_str}"
        odds_map = {}
        try:
            resp = self.fetch_page(url)
            if not resp: return {}
            
            # BeautifulSoupでテーブル解析
            soup = BeautifulSoup(resp.text, 'html.parser')
            # オッズが表示されているtdタグ(class="oddsPoint")などを探す
            # サイト構造に依存するため、汎用的なテキスト抽出を行う
            
            # 簡易実装: "1-2-3" のような並びと、その近くの数値を正規表現で抜く
            text = soup.get_text().replace("\n", " ").replace("\r", "")
            
            # パターン: 1-2-3 12.5 のような並びを探す
            # ※実際はHTML構造解析が必要だが、軽量化のため正規表現で推定
            # 例: \d-\d-\d\s+(\d+\.\d+)
            matches = re.findall(r"(\d{1}-\d{1}-\d{1})\s+([\d\.]+)", text)
            
            for m in matches:
                try:
                    comb = m[0] # "1-2-3"
                    val = float(m[1]) # 12.5
                    odds_map[comb] = val
                except:
                    continue
                    
        except Exception as e:
            print(f"Odds parsing warning: {e}")
        
        return odds_map

    def get_race_data(self, jcd, race_no):
        """レース情報の統合取得"""
        list_url = f"{BASE_URL}/racelist?jcd={jcd}&no={race_no}&hd={self.date_str}"
        info_url = f"{BASE_URL}/beforeinfo?jcd={jcd}&no={race_no}&hd={self.date_str}"
        
        data = {"jcd": jcd, "race_no": race_no, "racers": [], "weather": {"wind": 2, "wave": 2}}
        
        # 1. 気象
        try:
            resp = self.fetch_page(info_url)
            if resp:
                txt = BeautifulSoup(resp.text, 'html.parser').get_text()
                w = re.search(r"風速.*?(\d+)m", txt)
                if w: data["weather"]["wind"] = int(w.group(1))
                wv = re.search(r"波高.*?(\d+)cm", txt)
                if wv: data["weather"]["wave"] = int(wv.group(1))
        except: pass

        # 2. 出走表
        try:
            dfs = pd.read_html(list_url)
            df = next((d for d in dfs if len(d) == 6), None)
            if df is not None:
                for i, row in df.iterrows():
                    rs = str(row.values)
                    cls = "A1" if "A1" in rs else "A2" if "A2" in rs else "B1"
                    
                    mp = 30.0
                    nums = re.findall(r"\d+\.\d+", rs)
                    valid = [float(n) for n in nums if 20.0 <= float(n) <= 80.0]
                    if valid: mp = max(valid)

                    data["racers"].append({
                        "lane": i+1, "class": cls, "motor_pct": mp, "st": 0.17
                    })
        except: return None
        
        if not data["racers"]: return None
        return data

    def predict(self, data):
        # まずオッズを取得
        odds_map = self.get_odds(data["jcd"], data["race_no"])
        
        wind = data["weather"]["wind"]
        wave = data["weather"]["wave"]
        b1 = data["racers"][0]
        jcd = data["jcd"]
        
        # SKIP判定
        limit = 5 if jcd == "03" else 7
        if wind >= limit or wave >= 7:
            return {"logic": "SKIP", "preds": ["見送り (悪天候)"]}

        # ロジック判定
        st_type = STADIUM_BIAS.get(jcd, "NORMAL")
        is_rough = False
        is_solid = False
        
        # 判定ロジック
        rough_th = 5 if st_type == "STRONG_INS" else 4
        if (wind >= rough_th or b1["class"] in ["B1", "B2"]):
            if "A" in data["racers"][3]["class"] or data["racers"][3]["motor_pct"] >= 40:
                is_rough = True
        elif wind <= 3 and b1["class"] == "A1" and st_type != "WEAK_INS":
            is_solid = True
            
        if not is_rough and not is_solid:
            if st_type == "STRONG_INS" and b1["class"] == "A1" and wind <= 5: is_solid = True
            else: return {"logic": "SKIP", "preds": ["見送り (混戦)"]}

        # スコアリング
        scores = []
        for r in data["racers"]:
            sc = 100
            l = r["lane"]
            sc += {1:50, 2:30, 3:20}.get(l, 0)
            if st_type == "STRONG_INS" and l==1: sc+=20
            if st_type == "WEAK_INS" and l in [3,4]: sc+=15
            if r["class"]=="A1": sc+=50
            elif r["class"]=="A2": sc+=25
            sc += (r["motor_pct"]-30.0)*2
            if r["motor_pct"]>=40: sc+=20
            
            if is_rough:
                if l==1: sc-=60
                if l==4: sc+=40
                if l>=5: sc+=20
            else:
                if l==1: sc+=60
                if l==2: sc+=15
            scores.append({"l":l, "s":sc})
            
        scores.sort(key=lambda x: x["s"], reverse=True)
        o = [s["l"] for s in scores]
        
        # 買い目候補 (多めに作る)
        candidates = []
        if is_solid:
            # 堅実買い目候補
            candidates = [
                f"{o[0]}-{o[1]}-{o[2]}",
                f"{o[0]}-{o[1]}-{o[3]}",
                f"{o[0]}-{o[2]}-{o[1]}",
                f"{o[0]}-{o[2]}-{o[3]}",
                f"{o[0]}-{o[3]}-{o[1]}"
            ]
        else:
            # 穴買い目候補
            candidates = [
                f"{o[0]}-{o[1]}-{o[2]}",
                f"{o[0]}-{o[2]}-{o[1]}",
                f"{o[1]}-{o[0]}-{o[2]}",
                f"{o[1]}-{o[2]}-{o[0]}",
                f"{o[0]}-{o[1]}-{o[3]}" # ヒモ荒れ
            ]
            
        # 【Ver 4.0】オッズフィルター
        # 安すぎるオッズ (SOLIDなら4.0倍以下、ROUGHなら10.0倍以下) は削除
        final_preds = []
        min_odds = 4.0 if is_solid else 10.0
        
        for c in candidates:
            current_odds = odds_map.get(c, 0.0)
            # オッズが取れていない(0.0)場合は、発売前かもしれないので一応残す
            # オッズが取れていて、かつ基準より低い(ガミる)場合は捨てる
            if current_odds > 0 and current_odds < min_odds:
                continue # 削除
            
            # 表示用にオッズを付記
            display_str = c
            if current_odds > 0:
                display_str += f" ({current_odds}倍)"
            final_preds.append(display_str)
            
        # 全部消えてしまった場合の救済 (一番マシなものを残す)
        if not final_preds and candidates:
             final_preds.append(candidates[0] + " (安)")

        return {"logic": "ROUGH" if is_rough else "SOLID", "preds": final_preds[:4]}

    def run(self):
        print(f"Starting REAL Scraping (Ver 4.0 with Odds)...")
        db = {}
        stadiums = self.get_active_stadiums()
        if not stadiums:
            with open(f"{DATA_DIR}/latest_odds.json", "w", encoding="utf-8") as f: json.dump({}, f)
            return

        for jcd in stadiums:
            db[jcd] = []
            for r in range(1, 13):
                print(f"Processing {jcd}R{r}...")
                data = self.get_race_data(jcd, r)
                if data:
                    res = self.predict(data)
                    if res:
                        db[jcd].append({
                            "race_no": r,
                            "prediction_logic": res["logic"],
                            "predictions": res["preds"]
                        })
                time.sleep(1)
        
        with open(f"{DATA_DIR}/latest_odds.json", "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        print("Done.")

if __name__ == "__main__":
    KyoteiPredictor().run()
