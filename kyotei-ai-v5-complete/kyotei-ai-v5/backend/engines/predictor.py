"""
競艇予想AI v5 - AI予測エンジン
本命・中穴・大穴の3段階予想
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb
import joblib
from pathlib import Path
from typing import Dict, List
import logging

from .feature_engineering import FeatureEngineer

logger = logging.getLogger(__name__)


class MultiTargetPredictor:
    """マルチターゲット予測エンジン"""
    
    def __init__(self):
        self.honmei_model = None
        self.chuuane_model = None
        self.ooane_model = None
        self.scaler = StandardScaler()
        self.feature_engineer = FeatureEngineer()
        self.models_loaded = False
    
    def load_models(self, models_dir: str = 'data/models'):
        """モデル読み込み"""
        
        models_path = Path(models_dir)
        
        try:
            self.honmei_model = joblib.load(models_path / 'honmei_model.pkl')
            self.chuuane_model = joblib.load(models_path / 'chuuane_model.pkl')
            self.ooane_model = joblib.load(models_path / 'ooane_model.pkl')
            self.scaler = joblib.load(models_path / 'scaler.pkl')
            self.models_loaded = True
            logger.info("✓ モデル読み込み完了")
            return True
        except Exception as e:
            logger.error(f"モデル読み込み失敗: {e}")
            self.models_loaded = False
            return False
    
    def build_models(self):
        """モデル構築（訓練前）"""
        
        # 本命モデル（LightGBM - 精度重視）
        self.honmei_model = lgb.LGBMClassifier(
            objective='multiclass',
            num_class=6,
            n_estimators=1000,
            learning_rate=0.03,
            max_depth=10,
            num_leaves=31,
            min_child_samples=30,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.3,
            reg_lambda=0.3,
            random_state=42,
            verbose=-1
        )
        
        # 中穴モデル（Gradient Boosting - バランス型）
        self.chuuane_model = GradientBoostingClassifier(
            n_estimators=500,
            learning_rate=0.05,
            max_depth=8,
            min_samples_split=20,
            min_samples_leaf=10,
            subsample=0.8,
            random_state=42
        )
        
        # 大穴モデル（Random Forest - 多様性重視）
        self.ooane_model = RandomForestClassifier(
            n_estimators=500,
            max_depth=12,
            min_samples_split=10,
            min_samples_leaf=5,
            max_features='sqrt',
            bootstrap=True,
            random_state=42
        )
        
        logger.info("✓ モデル構築完了")
    
    def predict(self, race_data: Dict) -> Dict:
        """3段階予想実行"""
        
        if not self.models_loaded:
            logger.warning("モデル未読み込み - デモモードで実行")
            return self._demo_prediction(race_data)
        
        # 特徴量生成
        features = self.feature_engineer.create_features(race_data)
        features_scaled = self.scaler.transform(features)
        
        # 各モデルで予測
        honmei_probs = self.honmei_model.predict_proba(features_scaled)[0]
        chuuane_probs = self.chuuane_model.predict_proba(features_scaled)[0]
        ooane_probs = self.ooane_model.predict_proba(features_scaled)[0]
        
        # 3連単組み合わせ生成
        honmei_combos = self._generate_combinations(honmei_probs, 'honmei')
        chuuane_combos = self._generate_combinations(chuuane_probs, 'chuuane')
        ooane_combos = self._generate_combinations(ooane_probs, 'ooane')
        
        return {
            'honmei': honmei_combos[:5],
            'chuuane': chuuane_combos[:10],
            'ooane': ooane_combos[:15],
            'probabilities': {
                'honmei': honmei_probs.tolist(),
                'chuuane': chuuane_probs.tolist(),
                'ooane': ooane_probs.tolist()
            }
        }
    
    def _generate_combinations(self, probs: np.ndarray, target: str) -> List[Dict]:
        """3連単組み合わせ生成"""
        
        combinations = []
        
        for first in range(6):
            for second in range(6):
                if second == first:
                    continue
                for third in range(6):
                    if third == first or third == second:
                        continue
                    
                    # スコア計算
                    if target == 'honmei':
                        score = probs[first] * 1.5 + probs[second] * 0.5 + probs[third] * 0.3
                    elif target == 'chuuane':
                        score = probs[first] * 1.0 + probs[second] * 0.8 + probs[third] * 0.6
                    else:  # ooane
                        score = probs[first] * 0.8 + probs[second] * 1.0 + probs[third] * 0.9
                    
                    combinations.append({
                        'boats': [first + 1, second + 1, third + 1],
                        'score': float(score),
                        'confidence': min(95, max(30, int(score * 100)))
                    })
        
        combinations.sort(key=lambda x: x['score'], reverse=True)
        return combinations
    
    def _demo_prediction(self, race_data: Dict) -> Dict:
        """デモ予想（モデル未読み込み時）"""
        
        logger.info("デモモード: 簡易予想を実行")
        
        boats = race_data['boats']
        
        # 簡易スコア計算
        scores = []
        for i, boat in enumerate(boats):
            score = boat['national_rate'].get('win_rate', 0.0) / 10.0
            score += boat['motor_info'].get('motor_rate_2', 30.0) / 100.0
            score += [0.3, 0.15, 0.1, 0.05, 0.0, -0.05][i]  # コース有利度
            scores.append(score)
        
        scores = np.array(scores)
        scores = scores / scores.sum()  # 正規化
        
        # 組み合わせ生成
        honmei_combos = self._generate_combinations(scores, 'honmei')
        chuuane_combos = self._generate_combinations(scores, 'chuuane')
        ooane_combos = self._generate_combinations(scores, 'ooane')
        
        return {
            'honmei': honmei_combos[:5],
            'chuuane': chuuane_combos[:10],
            'ooane': ooane_combos[:15],
            'demo_mode': True,
            'probabilities': {
                'honmei': scores.tolist(),
                'chuuane': scores.tolist(),
                'ooane': scores.tolist()
            }
        }


class RaceClassifier:
    """レース分類器（安定/混戦/荒れ）"""
    
    def classify(self, race_data: Dict) -> Dict:
        """レース分類"""
        
        features = self._extract_features(race_data)
        stability_score = self._calculate_stability(features)
        
        if stability_score >= 70:
            category = 'stable'
            description = '実力通りの結果が出やすい'
            strategy = 'honmei'
        elif stability_score >= 40:
            category = 'mixed'
            description = '実力が拮抗、中穴狙い'
            strategy = 'chuuane'
        else:
            category = 'upset'
            description = '波乱の可能性大'
            strategy = 'ooane'
        
        return {
            'category': category,
            'stability': int(stability_score),
            'description': description,
            'strategy': strategy,
            'factors': features
        }
    
    def _extract_features(self, race_data: Dict) -> Dict:
        """分類用特徴量"""
        
        boats = race_data['boats']
        odds = race_data.get('odds', {}).get('sanrentan', {})
        
        all_rates = [b['national_rate'].get('win_rate', 0.0) for b in boats]
        all_motors = [b['motor_info'].get('motor_rate_2', 30.0) for b in boats]
        odds_values = list(odds.values()) if odds else [10.0]
        
        return {
            'rate_variance': float(np.var(all_rates)) if all_rates else 0.0,
            'rate_gap': float(max(all_rates) - min(all_rates)) if all_rates else 0.0,
            'odds_variance': float(np.var(odds_values)) if odds_values else 0.0,
            'course1_advantage': float(boats[0]['national_rate'].get('win_rate', 0.0) - np.mean(all_rates[1:])) if len(boats) >= 2 else 0.0,
            'wind_speed': float(race_data.get('weather', {}).get('wind_speed', 0.0)),
            'motor_gap': float(max(all_motors) - min(all_motors)) if all_motors else 0.0
        }
    
    def _calculate_stability(self, features: Dict) -> float:
        """安定度スコア計算"""
        
        score = 100.0
        
        score -= features['rate_variance'] * 2
        score += features['rate_gap'] * 0.5
        score += features['course1_advantage'] * 5
        score -= features['odds_variance'] * 0.5
        score -= features['wind_speed'] * 3
        score -= features['motor_gap'] * 0.3
        
        return max(0, min(100, score))
