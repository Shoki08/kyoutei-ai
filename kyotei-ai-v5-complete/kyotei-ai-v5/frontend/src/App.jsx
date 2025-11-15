/**
 * 競艇予想AI v5.0 - メインアプリ
 */

import { useState } from 'react';
import RaceAnalysis from './pages/RaceAnalysis';
import './App.css';

const VENUES = [
  '桐生', '戸田', '江戸川', '平和島', '多摩川', '浜名湖',
  '蒲郡', '常滑', '津', '三国', 'びわこ', '住之江',
  '尼崎', '鳴門', '丸亀', '児島', '宮島', '徳山',
  '下関', '若松', '芦屋', '福岡', '唐津', '大村'
];

function App() {
  const [venue, setVenue] = useState('大村');
  const [raceNumber, setRaceNumber] = useState(12);
  const [analyzing, setAnalyzing] = useState(false);

  const handleAnalyze = () => {
    setAnalyzing(true);
  };

  if (analyzing) {
    return <RaceAnalysis venue={venue} raceNumber={raceNumber} onBack={() => setAnalyzing(false)} />;
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* ヘッダー */}
      <header className="bg-blue-600 text-white p-4 shadow-lg">
        <h1 className="text-2xl font-bold">🚤 競艇予想AI v5.0</h1>
        <p className="text-sm opacity-90">高精度・期待値重視の予想システム</p>
      </header>

      {/* メインコンテンツ */}
      <main className="container mx-auto p-4 max-w-2xl">
        <div className="bg-white rounded-lg shadow-md p-6 mt-4">
          <h2 className="text-xl font-bold mb-4">レース選択</h2>

          {/* 競艇場選択 */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">競艇場</label>
            <select
              value={venue}
              onChange={(e) => setVenue(e.target.value)}
              className="w-full p-2 border rounded"
            >
              {VENUES.map((v) => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
          </div>

          {/* レース番号選択 */}
          <div className="mb-6">
            <label className="block text-sm font-medium mb-2">レース番号</label>
            <select
              value={raceNumber}
              onChange={(e) => setRaceNumber(Number(e.target.value))}
              className="w-full p-2 border rounded"
            >
              {[...Array(12)].map((_, i) => (
                <option key={i + 1} value={i + 1}>第{i + 1}R</option>
              ))}
            </select>
          </div>

          {/* 分析ボタン */}
          <button
            onClick={handleAnalyze}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-bold hover:bg-blue-700 transition"
          >
            🔍 分析開始
          </button>

          {/* 説明 */}
          <div className="mt-6 p-4 bg-blue-50 rounded">
            <h3 className="font-bold mb-2">✨ 主な機能</h3>
            <ul className="text-sm space-y-1">
              <li>✓ 前節今節成績を含む多層的データ分析</li>
              <li>✓ レース分類（安定/混戦/荒れ）</li>
              <li>✓ 期待値ベースの券種最適化</li>
              <li>✓ 見送り判定</li>
            </ul>
          </div>
        </div>

        {/* フッター */}
        <footer className="text-center text-sm text-gray-600 mt-8 pb-4">
          <p>競艇予想AI v5.0</p>
          <p className="text-xs mt-1">予想は参考です。投資は自己責任でお願いします。</p>
        </footer>
      </main>
    </div>
  );
}

export default App;
