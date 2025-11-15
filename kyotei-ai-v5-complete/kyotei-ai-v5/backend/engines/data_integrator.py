"""
競艇予想AI v5 - データ統合エンジン
Layer 1-4の全データを統合
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict
import logging

from ..utils.safe_scraper import SafeScraper

logger = logging.getLogger(__name__)


class DataIntegrator:
    """データ統合エンジン"""
    
    def __init__(self, data_dir: str = 'data'):
        self.data_dir = Path(data_dir)
        self.scraper = SafeScraper()
    
    def integrate_all_layers(self, venue: str, race_number: int, date: str = None) -> Dict:
        """Layer 1-4を統合"""
        
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        venue_code = self.scraper.venue_codes.get(venue)
        if not venue_code:
            raise ValueError(f"競艇場名が不正: {venue}")
        
        logger.info(f"データ統合開始: {venue} {race_number}R ({date})")
        
        # ========================================
        # Layer 3: 当日データを読み込み
        # ========================================
        race_data = self._load_daily_data(venue_code, date, race_number)
        
        # ========================================
        # Layer 1 & 2: 選手データを統合
        # ========================================
        for boat in race_data['boats']:
            racer_id = boat.get('racer_id')
            if not racer_id:
                continue
            
            # 選手マスタ（Layer 1）
            master = self._load_racer_master(racer_id)
            if master:
                boat['career_stats'] = master.get('career_stats', {})
                boat['venue_stats'] = master.get('venue_stats', {}).get(venue_code, {})
            
            # 期間データ（Layer 2）
            period = self._load_period_data(racer_id, date[:6])
            if period:
                boat['current_period'] = period.get('current_period', {})
                boat['previous_period'] = period.get('previous_period', {})
                boat['recent_10'] = period.get('recent_10_races', [])
                boat['form_analysis'] = period.get('form_analysis', {})
        
        # ========================================
        # Layer 4: 直前データをスクレイピング
        # ========================================
        try:
            live_data = self.scraper.scrape_live_data(venue_code, date, race_number)
        except Exception as e:
            logger.error(f"直前データ取得失敗: {e}")
            live_data = self._default_live_data()
        
        # ========================================
        # 統合データ作成
        # ========================================
        complete_data = {
            **race_data,
            'tenji': live_data.get('tenji', {}),
            'odds': live_data.get('odds', {}),
            'weather': live_data.get('weather', {}),
            'data_quality': self._calculate_data_quality(race_data, live_data)
        }
        
        logger.info("✓ データ統合完了")
        
        return complete_data
    
    def _load_daily_data(self, venue_code: str, date: str, race_number: int) -> Dict:
        """Layer 3: 当日データ読み込み"""
        
        daily_path = self.data_dir / 'daily' / date / f'{venue_code}_race{race_number}.json'
        
        if daily_path.exists():
            with open(daily_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            logger.warning(f"当日データなし: {daily_path}")
            # スクレイピングで取得を試みる
            try:
                return self.scraper.scrape_race_list(venue_code, date, race_number)
            except:
                return self._default_race_data(race_number)
    
    def _load_racer_master(self, racer_id: int) -> Dict:
        """Layer 1: 選手マスタ読み込み"""
        
        master_path = self.data_dir / 'racers' / 'master' / f'{racer_id}.json'
        
        if master_path.exists():
            with open(master_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _load_period_data(self, racer_id: int, year_month: str) -> Dict:
        """Layer 2: 期間データ読み込み"""
        
        period_path = self.data_dir / 'racers' / 'periods' / f'{racer_id}_{year_month}.json'
        
        if period_path.exists():
            with open(period_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _default_race_data(self, race_number: int) -> Dict:
        """デフォルトレースデータ"""
        
        boats = []
        for i in range(1, 7):
            boats.append({
                'course': i,
                'racer_id': 0,
                'name': 'データなし',
                'national_rate': {'win_rate': 5.0, 'place_rate_2': 30.0},
                'local_rate': {'win_rate': 5.0},
                'motor_info': {'motor_rate_2': 30.0},
                'boat_info': {'boat_rate_2': 30.0}
            })
        
        return {
            'race_number': race_number,
            'boats': boats,
            'race_info': {}
        }
    
    def _default_live_data(self) -> Dict:
        """デフォルト直前データ"""
        
        return {
            'tenji': {'tenji_time': []},
            'odds': {'sanrentan': {}, 'sanrenpuku': {}, 'niretan': {}},
            'weather': {'wind_speed': 0.0, 'wave_height': 0}
        }
    
    def _calculate_data_quality(self, race_data: Dict, live_data: Dict) -> Dict:
        """データ品質スコア"""
        
        score = 0.0
        checks = []
        
        # 基本データ（30%)
        boats = race_data.get('boats', [])
        if len(boats) == 6:
            score += 0.10
            checks.append("✓ 出走表OK")
        
        if all(b.get('national_rate', {}).get('win_rate', 0) > 0 for b in boats):
            score += 0.10
            checks.append("✓ 全国勝率OK")
        
        if all(b.get('motor_info', {}).get('motor_rate_2', 0) > 0 for b in boats):
            score += 0.10
            checks.append("✓ モーター2連率OK")
        
        # 期間データ（20%）
        if all(b.get('current_period') for b in boats):
            score += 0.10
            checks.append("✓ 今節成績OK")
        else:
            checks.append("✗ 今節成績なし")
        
        if all(b.get('form_analysis') for b in boats):
            score += 0.10
            checks.append("✓ フォーム分析OK")
        else:
            checks.append("✗ フォーム分析なし")
        
        # 展示タイム（20%）
        tenji_list = live_data.get('tenji', {}).get('tenji_time', [])
        if len(tenji_list) == 6:
            score += 0.20
            checks.append("✓ 展示タイムOK")
        else:
            checks.append("✗ 展示タイムなし")
        
        # オッズ（20%）
        odds = live_data.get('odds', {}).get('sanrentan', {})
        if len(odds) > 100:
            score += 0.20
            checks.append("✓ オッズOK")
        else:
            checks.append("✗ オッズ不足")
        
        # 天候（10%）
        if live_data.get('weather', {}).get('wind_speed') is not None:
            score += 0.10
            checks.append("✓ 天候OK")
        
        return {
            'score': score,
            'checks': checks,
            'is_reliable': score >= 0.7,
            'missing_critical': [c for c in checks if c.startswith('✗')]
        }
