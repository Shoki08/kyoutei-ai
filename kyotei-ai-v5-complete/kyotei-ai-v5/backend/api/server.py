"""
競艇予想AI v5 - Flask APIサーバー
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import logging
import sys
from pathlib import Path

# パス追加
sys.path.append(str(Path(__file__).parent.parent))

from engines.data_integrator import DataIntegrator
from engines.predictor import MultiTargetPredictor, RaceClassifier
from engines.optimizer import Optimizer

app = Flask(__name__)
CORS(app)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# グローバル変数
integrator = DataIntegrator()
predictor = MultiTargetPredictor()
classifier = RaceClassifier()
optimizer = Optimizer()
prediction_history = []

# モデル読み込み
try:
    predictor.load_models()
    logger.info("✓ モデル読み込み完了")
except Exception as e:
    logger.warning(f"モデル読み込み失敗: {e} - デモモードで起動")


@app.route('/')
def index():
    """ヘルスチェック"""
    return jsonify({
        'status': 'ok',
        'service': '競艇予想AI v5.0',
        'version': '5.0.0',
        'features': [
            '多層的データ取得（前節今節含む）',
            'レース分類（安定/混戦/荒れ）',
            '期待値ベースの券種最適化',
            '見送り判定',
            '高信頼性スクレイピング'
        ],
        'models_loaded': predictor.models_loaded
    })


@app.route('/api/v5/analyze', methods=['POST'])
def analyze_race():
    """
    レース分析のメインエンドポイント
    
    Request:
    {
        "venue": "大村",
        "race_number": 12
    }
    """
    
    try:
        data = request.json
        
        if not data or 'venue' not in data or 'race_number' not in data:
            return jsonify({'error': '競艇場とレース番号が必要です'}), 400
        
        venue = data['venue']
        race_number = data['race_number']
        
        logger.info(f"📡 分析リクエスト: {venue} {race_number}R")
        
        # ========================================
        # Step 1: データ統合（Layer 1-4）
        # ========================================
        logger.info("Step 1: データ統合中...")
        
        try:
            complete_data = integrator.integrate_all_layers(venue, race_number)
        except Exception as e:
            logger.error(f"データ統合失敗: {e}")
            return jsonify({
                'status': 'error',
                'error': 'データ収集に失敗しました',
                'detail': str(e)
            }), 503
        
        # データ品質チェック
        data_quality = complete_data['data_quality']
        
        if data_quality['score'] < 0.7:
            logger.warning(f"データ品質不足: {data_quality['score']:.0%}")
            return jsonify({
                'status': 'data_insufficient',
                'message': '情報不足のため精度が低下します',
                'quality_score': data_quality['score'],
                'missing': data_quality['missing_critical'],
                'recommendation': '見送りを推奨'
            })
        
        # ========================================
        # Step 2: レース分類
        # ========================================
        logger.info("Step 2: レース分類中...")
        
        race_class = classifier.classify(complete_data)
        
        # ========================================
        # Step 3: AI予測
        # ========================================
        logger.info("Step 3: AI予測実行中...")
        
        predictions = predictor.predict(complete_data)
        
        # ========================================
        # Step 4: 期待値計算・券種最適化
        # ========================================
        logger.info("Step 4: 券種最適化中...")
        
        optimized = optimizer.optimize_tickets(
            predictions,
            complete_data.get('odds', {}),
            race_class['stability']
        )
        
        # ========================================
        # Step 5: 見送り判定
        # ========================================
        logger.info("Step 5: 見送り判定中...")
        
        best_ev = optimized.get('expected_value', 0)
        should_skip, skip_reasons = optimizer.should_skip(
            best_ev,
            race_class['stability'],
            data_quality['score']
        )
        
        if should_skip:
            logger.info(f"⚠️ 見送り推奨: {skip_reasons}")
            return jsonify({
                'status': 'skip',
                'venue': venue,
                'race_number': race_number,
                'should_skip': True,
                'skip_reasons': skip_reasons,
                'stability': race_class['stability'],
                'expected_value': best_ev,
                'recommendation': '見送りを推奨'
            })
        
        # ========================================
        # Step 6: レスポンス生成
        # ========================================
        prediction_id = f"pred_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        response = {
            'status': 'success',
            'prediction_id': prediction_id,
            'venue': venue,
            'race_number': race_number,
            'date': complete_data.get('scraped_at', ''),
            
            # レース分類
            'category': race_class['category'],
            'stability': race_class['stability'],
            'description': race_class['description'],
            
            # 予想結果
            'predictions': {
                'honmei': predictions['honmei'],
                'chuuane': predictions['chuuane'],
                'ooane': predictions['ooane']
            },
            
            # 推奨買い目
            'recommendations': optimized,
            
            # 期待値
            'expected_value': best_ev,
            
            # データ品質
            'data_quality': data_quality,
            
            # メタ情報
            'demo_mode': predictions.get('demo_mode', False),
            'timestamp': datetime.now().isoformat()
        }
        
        # 履歴保存
        prediction_history.append({
            'prediction_id': prediction_id,
            'request': data,
            'response': response,
            'timestamp': datetime.now().isoformat()
        })
        
        # 最新100件のみ保持
        if len(prediction_history) > 100:
            prediction_history.pop(0)
        
        logger.info(f"✅ 分析完了: {prediction_id}")
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"❌ エラー: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/api/v5/stats', methods=['GET'])
def get_stats():
    """統計情報取得"""
    
    total_predictions = len(prediction_history)
    
    # 基本統計
    stats = {
        'total_predictions': total_predictions,
        'demo_mode_predictions': sum(1 for p in prediction_history if p['response'].get('demo_mode', False)),
        'skipped_races': sum(1 for p in prediction_history if p['response'].get('status') == 'skip'),
        'successful_predictions': sum(1 for p in prediction_history if p['response'].get('status') == 'success'),
        'average_stability': 0,
        'category_distribution': {
            'stable': 0,
            'mixed': 0,
            'upset': 0
        }
    }
    
    # カテゴリ分布
    for pred in prediction_history:
        if pred['response'].get('status') == 'success':
            category = pred['response'].get('category')
            if category in stats['category_distribution']:
                stats['category_distribution'][category] += 1
    
    return jsonify(stats)


@app.route('/api/v5/result', methods=['POST'])
def register_result():
    """結果登録"""
    
    try:
        data = request.json
        
        prediction_id = data.get('prediction_id')
        actual_result = data.get('actual_result')
        actual_odds = data.get('actual_odds', 0)
        
        if not prediction_id or not actual_result:
            return jsonify({'error': '予測IDと結果が必要です'}), 400
        
        # 予測を探す
        pred_record = None
        for record in prediction_history:
            if record['prediction_id'] == prediction_id:
                pred_record = record
                break
        
        if not pred_record:
            return jsonify({'error': '予測IDが見つかりません'}), 404
        
        # 的中判定
        # （実装省略 - 実際は詳細な的中判定を行う）
        
        logger.info(f"結果登録: {prediction_id}")
        
        return jsonify({
            'success': True,
            'prediction_id': prediction_id
        })
        
    except Exception as e:
        logger.error(f"結果登録エラー: {e}")
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'エンドポイントが見つかりません'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'サーバーエラーが発生しました'}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🚤 競艇予想AI v5.0 APIサーバー起動")
    print("=" * 60)
    print("機能:")
    print("  ✓ 多層的データ取得（前節今節含む）")
    print("  ✓ レース分類（安定/混戦/荒れ）")
    print("  ✓ 期待値ベースの券種最適化")
    print("  ✓ 見送り判定")
    print("=" * 60)
    print(f"URL: http://localhost:5000")
    print("=" * 60)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True
    )
