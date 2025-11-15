"""
競艇予想AI v5 - 期待値計算・券種最適化エンジン
レース分類に応じた最適な購入戦略を提案
"""

import numpy as np
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)


class Optimizer:
    """期待値計算・券種最適化"""
    
    def optimize_tickets(self, predictions: Dict, odds: Dict, stability: int) -> Dict:
        """レース分類に応じた券種最適化"""
        
        if stability >= 70:
            return self._stable_strategy(predictions, odds)
        elif stability >= 40:
            return self._mixed_strategy(predictions, odds)
        else:
            return self._upset_strategy(predictions, odds)
    
    def _stable_strategy(self, predictions: Dict, odds: Dict) -> Dict:
        """安定レース: 本命1点 + 保険"""
        
        top_combo = predictions['honmei'][0]['boats']
        combo_key = f"{top_combo[0]}-{top_combo[1]}-{top_combo[2]}"
        
        sanrentan_odds = odds.get('sanrentan', {}).get(combo_key, 0)
        
        # 三連複オッズ（ソート済み）
        sanrenpuku_key = '-'.join(sorted(map(str, top_combo)))
        sanrenpuku_odds = odds.get('sanrenpuku', {}).get(sanrenpuku_key, 0)
        
        hit_prob = predictions['honmei'][0]['score'] / 3.0
        
        tickets = []
        
        if sanrentan_odds > 0:
            tickets.append({
                'type': '三連単',
                'combination': combo_key,
                'amount': 2500,
                'odds': sanrentan_odds,
                'expected_return': sanrentan_odds * 2500 * hit_prob,
                'purpose': 'メイン'
            })
        
        if sanrenpuku_odds > 0:
            tickets.append({
                'type': '三連複',
                'combination': sanrenpuku_key,
                'amount': 500,
                'odds': sanrenpuku_odds,
                'expected_return': sanrenpuku_odds * 500 * (hit_prob * 1.2),
                'purpose': '保険'
            })
        
        total_investment = sum(t['amount'] for t in tickets)
        total_expected = sum(t['expected_return'] for t in tickets)
        ev = ((total_expected - total_investment) / total_investment * 100) if total_investment > 0 else 0
        
        return {
            'strategy': '安定レース: 本命1点 + 保険',
            'tickets': tickets,
            'total_investment': total_investment,
            'expected_value': ev,
            'explanation': [
                f"三連単 {combo_key} が{sanrentan_odds}倍",
                f"的中確率{hit_prob:.1%}で期待値{ev:.1f}%",
                "三連複で保険をかけてリスク分散"
            ]
        }
    
    def _mixed_strategy(self, predictions: Dict, odds: Dict) -> Dict:
        """混戦レース: 軸流し"""
        
        axis = 1
        tickets = []
        
        # 三連単 TOP3
        for i, pred in enumerate(predictions['chuuane'][:3]):
            combo = pred['boats']
            combo_key = f"{combo[0]}-{combo[1]}-{combo[2]}"
            odd = odds.get('sanrentan', {}).get(combo_key, 0)
            
            if odd > 0:
                tickets.append({
                    'type': '三連単',
                    'combination': combo_key,
                    'amount': 800,
                    'odds': odd,
                    'expected_return': odd * 800 * pred['score'],
                    'purpose': f'本線{i+1}'
                })
        
        # 二連単 軸流し
        for second in range(2, 7):
            if second == axis:
                continue
            combo_key = f"{axis}-{second}"
            odd = odds.get('niretan', {}).get(combo_key, 0)
            
            if odd > 0:
                tickets.append({
                    'type': '二連単',
                    'combination': combo_key,
                    'amount': 120,
                    'odds': odd,
                    'purpose': '軸流し'
                })
        
        total_investment = sum(t['amount'] for t in tickets)
        
        return {
            'strategy': '混戦レース: 1号艇軸の流し',
            'tickets': tickets,
            'total_investment': total_investment
        }
    
    def _upset_strategy(self, predictions: Dict, odds: Dict) -> Dict:
        """荒れレース: 大穴狙い or 見送り"""
        
        # 期待値計算
        ev_ranking = []
        
        for pred in predictions['ooane'][:20]:
            combo = pred['boats']
            combo_key = f"{combo[0]}-{combo[1]}-{combo[2]}"
            odd = odds.get('sanrentan', {}).get(combo_key, 0)
            
            if odd > 0:
                hit_prob = pred['score'] / 3.0
                ev = (hit_prob * odd * 200) - 200
                
                ev_ranking.append({
                    'combination': combo_key,
                    'odds': odd,
                    'hit_prob': hit_prob,
                    'expected_value': ev
                })
        
        # 期待値順
        ev_ranking.sort(key=lambda x: x['expected_value'], reverse=True)
        
        # 期待値プラスのみ
        positive_ev = [x for x in ev_ranking if x['expected_value'] > 0]
        
        if len(positive_ev) == 0:
            return {
                'strategy': '見送り推奨',
                'reason': '期待値プラスの組み合わせなし',
                'tickets': [],
                'total_investment': 0
            }
        
        tickets = []
        for combo in positive_ev[:10]:
            tickets.append({
                'type': '三連単',
                'combination': combo['combination'],
                'amount': 200,
                'odds': combo['odds'],
                'expected_value': combo['expected_value'],
                'purpose': '大穴狙い'
            })
        
        return {
            'strategy': '荒れレース: 期待値上位の大穴10点',
            'tickets': tickets,
            'total_investment': 2000
        }
    
    def should_skip(self, expected_value: float, stability: int, data_quality: float) -> Tuple[bool, List[str]]:
        """見送り判定"""
        
        reasons = []
        
        if expected_value < 0:
            reasons.append('期待値マイナス')
        
        if stability < 30 and expected_value < 50:
            reasons.append('荒れる割に期待値不足')
        
        if data_quality < 0.7:
            reasons.append('データ品質不足')
        
        return len(reasons) > 0, reasons
