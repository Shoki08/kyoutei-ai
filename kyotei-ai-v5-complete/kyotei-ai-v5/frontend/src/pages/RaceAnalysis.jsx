/**
 * 競艇予想AI v5.0 - レース分析画面
 */

import { useState, useEffect } from 'react';
import { analyzeRace } from '../api/client';

function RaceAnalysis({ venue, raceNumber, onBack }) {
  const [loading, setLoading] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const analyze = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const data = await analyzeRace(venue, raceNumber);
        setResult(data);
      } catch (err) {
        setError(err.message || '分析に失敗しました');
      } finally {
        setLoading(false);
      }
    };

    analyze();
  }, [venue, raceNumber]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-blue-600 mx-auto mb-4"></div>
          <p className="text-lg font-bold">最新データ取得中...</p>
          <p className="text-sm text-gray-600 mt-2">30秒ほどお待ちください</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 p-4">
        <div className="container mx-auto max-w-2xl">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold text-red-600 mb-4">❌ エラー</h2>
            <p className="mb-4">{error}</p>
            <button
              onClick={onBack}
              className="bg-gray-600 text-white px-6 py-2 rounded hover:bg-gray-700"
            >
              戻る
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 見送り推奨の場合
  if (result?.should_skip || result?.status === 'skip') {
    return (
      <div className="min-h-screen bg-gray-100 p-4">
        <div className="container mx-auto max-w-2xl">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold text-orange-600 mb-4">🚫 見送り推奨</h2>
            
            <div className="mb-6">
              <p className="text-lg mb-2">このレースは購入を見送ることを推奨します</p>
              <div className="bg-orange-50 p-4 rounded">
                <h3 className="font-bold mb-2">理由:</h3>
                <ul className="space-y-1">
                  {result.skip_reasons?.map((reason, i) => (
                    <li key={i} className="text-sm">• {reason}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-gray-50 p-4 rounded">
                <p className="text-sm text-gray-600">安定度</p>
                <p className="text-2xl font-bold">{result.stability}%</p>
              </div>
              <div className="bg-gray-50 p-4 rounded">
                <p className="text-sm text-gray-600">期待値</p>
                <p className="text-2xl font-bold">{result.expected_value?.toFixed(1)}%</p>
              </div>
            </div>

            <button
              onClick={onBack}
              className="w-full bg-gray-600 text-white py-3 rounded font-bold hover:bg-gray-700"
            >
              ← 戻る
            </button>
          </div>
        </div>
      </div>
    );
  }

  // データ不足の場合
  if (result?.status === 'data_insufficient') {
    return (
      <div className="min-h-screen bg-gray-100 p-4">
        <div className="container mx-auto max-w-2xl">
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-bold text-yellow-600 mb-4">⚠️ データ不足</h2>
            <p className="mb-4">{result.message}</p>
            <div className="bg-yellow-50 p-4 rounded mb-4">
              <p className="text-sm">品質スコア: {(result.quality_score * 100).toFixed(0)}%</p>
            </div>
            <button
              onClick={onBack}
              className="w-full bg-gray-600 text-white py-3 rounded font-bold hover:bg-gray-700"
            >
              ← 戻る
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 成功時の分析結果表示
  const categoryColors = {
    stable: 'bg-green-100 text-green-800',
    mixed: 'bg-yellow-100 text-yellow-800',
    upset: 'bg-red-100 text-red-800'
  };

  const categoryIcons = {
    stable: '🟢',
    mixed: '🟡',
    upset: '🔴'
  };

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <div className="container mx-auto max-w-2xl">
        {/* ヘッダー */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-4">
          <button
            onClick={onBack}
            className="text-blue-600 mb-4 hover:underline"
          >
            ← 戻る
          </button>
          
          <h2 className="text-2xl font-bold mb-2">{venue} 第{raceNumber}R</h2>
          
          {/* レース分類 */}
          <div className={`inline-block px-4 py-2 rounded-full font-bold ${categoryColors[result.category]}`}>
            {categoryIcons[result.category]} {result.description}
          </div>

          <div className="grid grid-cols-2 gap-4 mt-4">
            <div className="bg-gray-50 p-4 rounded">
              <p className="text-sm text-gray-600">安定度</p>
              <p className="text-3xl font-bold">{result.stability}%</p>
            </div>
            <div className="bg-gray-50 p-4 rounded">
              <p className="text-sm text-gray-600">期待値</p>
              <p className="text-3xl font-bold text-blue-600">
                +{result.expected_value?.toFixed(1)}%
              </p>
            </div>
          </div>
        </div>

        {/* 推奨買い目 */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-4">
          <h3 className="text-xl font-bold mb-4">💰 推奨買い目</h3>
          
          <div className="mb-4">
            <p className="font-bold text-lg">{result.recommendations?.strategy}</p>
          </div>

          {result.recommendations?.tickets?.map((ticket, i) => (
            <div key={i} className="border-b py-3 last:border-b-0">
              <div className="flex justify-between items-center">
                <div>
                  <span className="font-bold text-lg">{ticket.combination}</span>
                  <span className="text-sm text-gray-600 ml-2">({ticket.type})</span>
                </div>
                <div className="text-right">
                  <p className="font-bold text-blue-600">{ticket.amount}円</p>
                  <p className="text-sm text-gray-600">{ticket.odds}倍</p>
                </div>
              </div>
              {ticket.purpose && (
                <p className="text-xs text-gray-500 mt-1">{ticket.purpose}</p>
              )}
            </div>
          ))}

          <div className="mt-4 pt-4 border-t">
            <div className="flex justify-between font-bold text-lg">
              <span>合計投資額</span>
              <span className="text-blue-600">{result.recommendations?.total_investment}円</span>
            </div>
          </div>
        </div>

        {/* AI予想（詳細） */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-4">
          <h3 className="text-xl font-bold mb-4">🤖 AI予想</h3>
          
          {/* 本命 */}
          <div className="mb-4">
            <h4 className="font-bold mb-2">本命予想（的中率重視）</h4>
            {result.predictions?.honmei?.slice(0, 3).map((pred, i) => (
              <div key={i} className="flex justify-between items-center py-2 border-b">
                <span>{pred.boats.join('-')}</span>
                <span className="text-sm text-gray-600">信頼度: {pred.confidence}%</span>
              </div>
            ))}
          </div>

          {/* 中穴 */}
          <div className="mb-4">
            <h4 className="font-bold mb-2">中穴予想（配当10-50倍）</h4>
            {result.predictions?.chuuane?.slice(0, 3).map((pred, i) => (
              <div key={i} className="flex justify-between items-center py-2 border-b">
                <span>{pred.boats.join('-')}</span>
                <span className="text-sm text-gray-600">信頼度: {pred.confidence}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* データ品質 */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-xl font-bold mb-4">📊 データ品質</h3>
          <div className="space-y-2">
            {result.data_quality?.checks?.map((check, i) => (
              <p key={i} className="text-sm">
                {check}
              </p>
            ))}
          </div>
          <div className="mt-4">
            <p className="text-sm text-gray-600">
              品質スコア: {(result.data_quality?.score * 100).toFixed(0)}%
            </p>
          </div>
        </div>

        {/* テレボートリンク */}
        <div className="mt-6 mb-8">
          <a
            href="https://www.teleboat.jp"
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full bg-green-600 text-white text-center py-4 rounded-lg font-bold hover:bg-green-700"
          >
            テレボートで投票 →
          </a>
        </div>
      </div>
    </div>
  );
}

export default RaceAnalysis;
