"""
競艇予想AI v5 - 特徴量エンジニアリング
多層的データから予測用特徴量を生成
"""

import numpy as np
from typing import Dict, List


class FeatureEngineer:
    """特徴量生成エンジン"""
    
    def create_features(self, race_data: Dict) -> np.ndarray:
        """完全な特徴量ベクトルを生成"""
        
        features = []
        
        # A. 基本特徴量
        features.extend(self._basic_features(race_data))
        
        # B. 期間特徴量（前節今節）
        features.extend(self._period_features(race_data))
        
        # C. 直前特徴量（展示・オッズ）
        features.extend(self._live_features(race_data))
        
        # D. 相対特徴量
        features.extend(self._relative_features(race_data))
        
        # E. レース全体特徴量
        features.extend(self._race_features(race_data))
        
        return np.array(features).reshape(1, -1)
    
    def _basic_features(self, race_data: Dict) -> List[float]:
        """基本特徴量（艇ごと）"""
        
        features = []
        boats = race_data['boats']
        
        for i, boat in enumerate(boats):
            # 勝率・連対率
            features.append(boat['national_rate'].get('win_rate', 0.0))
            features.append(boat['national_rate'].get('place_rate_2', 0.0))
            features.append(boat['local_rate'].get('win_rate', 0.0))
            
            # モーター・ボート
            features.append(boat['motor_info'].get('motor_rate_2', 30.0))
            features.append(boat['boat_info'].get('boat_rate_2', 30.0))
            
            # 級別
            class_map = {'A1': 4, 'A2': 3, 'B1': 2, 'B2': 1}
            features.append(class_map.get(boat.get('class', 'B1'), 2))
            
            # コース有利度
            course_advantage = [2.0, 1.1, 0.8, 0.6, 0.5, 0.4][i]
            features.append(course_advantage)
            
            # 競艇場相性
            venue_win_rate = boat.get('venue_stats', {}).get('win_rate', 0.2)
            features.append(venue_win_rate)
        
        return features
    
    def _period_features(self, race_data: Dict) -> List[float]:
        """期間特徴量（前節今節）"""
        
        features = []
        boats = race_data['boats']
        
        for boat in boats:
            # 今節成績
            current = boat.get('current_period', {}).get('period_stats', {})
            features.append(current.get('win_rate', 0.0))
            features.append(current.get('avg_st', 0.15))
            features.append(current.get('avg_finish', 3.5))
            
            # 前節成績
            previous = boat.get('previous_period', {}).get('period_stats', {})
            features.append(previous.get('win_rate', 0.0))
            features.append(previous.get('avg_finish', 3.5))
            
            # フォーム分析
            form = boat.get('form_analysis', {})
            features.append(form.get('form_score', 0.5))
            features.append(form.get('recent_avg_finish', 3.5))
            features.append(form.get('recent_avg_st', 0.15))
            
            # トレンド
            trend_map = {'上昇中': 1.0, '安定': 0.5, '下降中': 0.0}
            features.append(trend_map.get(form.get('trend', '安定'), 0.5))
            
            # 連勝数
            consecutive_wins = min(form.get('consecutive_wins', 0), 5)
            features.append(consecutive_wins / 5.0)
        
        return features
    
    def _live_features(self, race_data: Dict) -> List[float]:
        """直前特徴量（展示・オッズ）"""
        
        features = []
        
        # 展示タイム
        tenji_list = race_data.get('tenji', {}).get('tenji_time', [])
        for i in range(6):
            if i < len(tenji_list):
                tenji = tenji_list[i]
                features.append(tenji.get('time', 6.90))
                features.append(tenji.get('rank', 3))
                features.append(tenji.get('start_timing', 0.15))
            else:
                features.extend([6.90, 3, 0.15])
        
        # オッズ信頼度
        odds_data = race_data.get('odds', {}).get('sanrentan', {})
        for i in range(1, 7):
            avg_odds = self._calc_avg_odds(i, odds_data)
            features.append(avg_odds)
            
            confidence = 1.0 / (avg_odds + 1.0) if avg_odds > 0 else 0.5
            features.append(confidence)
        
        # 天候
        weather = race_data.get('weather', {})
        features.append(weather.get('wind_speed', 0.0))
        features.append(weather.get('wave_height', 0))
        features.append(weather.get('temperature', 20.0))
        
        return features
    
    def _relative_features(self, race_data: Dict) -> List[float]:
        """相対特徴量"""
        
        features = []
        boats = race_data['boats']
        
        # 実力の相対評価
        all_rates = [b['national_rate'].get('win_rate', 0.0) for b in boats]
        all_motors = [b['motor_info'].get('motor_rate_2', 30.0) for b in boats]
        
        mean_rate = np.mean(all_rates) if all_rates else 5.0
        mean_motor = np.mean(all_motors) if all_motors else 30.0
        
        for boat in boats:
            rate_diff = boat['national_rate'].get('win_rate', 0.0) - mean_rate
            motor_diff = boat['motor_info'].get('motor_rate_2', 30.0) - mean_motor
            
            features.extend([rate_diff, motor_diff])
        
        return features
    
    def _race_features(self, race_data: Dict) -> List[float]:
        """レース全体特徴量"""
        
        features = []
        boats = race_data['boats']
        
        # 実力のばらつき
        all_rates = [b['national_rate'].get('win_rate', 0.0) for b in boats]
        if all_rates:
            features.append(np.var(all_rates))
            features.append(max(all_rates) - min(all_rates))
        else:
            features.extend([0.0, 0.0])
        
        # オッズ分散
        odds_list = list(race_data.get('odds', {}).get('sanrentan', {}).values())
        if odds_list:
            features.append(np.var(odds_list))
        else:
            features.append(0.0)
        
        # 1号艇有利度
        if len(boats) >= 2:
            course1_rate = boats[0]['national_rate'].get('win_rate', 0.0)
            others_avg = np.mean([b['national_rate'].get('win_rate', 0.0) for b in boats[1:]])
            features.append(course1_rate - others_avg)
        else:
            features.append(0.0)
        
        return features
    
    def _calc_avg_odds(self, boat_num: int, odds_data: Dict) -> float:
        """この艇が絡む組み合わせの平均オッズ"""
        
        relevant_odds = []
        for combo, odd in odds_data.items():
            if str(boat_num) in combo.split('-'):
                relevant_odds.append(odd)
        
        return np.mean(relevant_odds) if relevant_odds else 50.0
