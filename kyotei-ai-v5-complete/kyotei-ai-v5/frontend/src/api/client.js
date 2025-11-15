/**
 * 競艇予想AI v5.0 - APIクライアント
 */

import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 60000, // 60秒
  headers: {
    'Content-Type': 'application/json'
  }
});

/**
 * レース分析
 */
export const analyzeRace = async (venue, raceNumber) => {
  try {
    const response = await apiClient.post('/api/v5/analyze', {
      venue,
      race_number: raceNumber
    });
    return response.data;
  } catch (error) {
    console.error('分析エラー:', error);
    throw error;
  }
};

/**
 * 統計情報取得
 */
export const getStats = async () => {
  try {
    const response = await apiClient.get('/api/v5/stats');
    return response.data;
  } catch (error) {
    console.error('統計取得エラー:', error);
    throw error;
  }
};

/**
 * 結果登録
 */
export const registerResult = async (predictionId, actualResult, actualOdds) => {
  try {
    const response = await apiClient.post('/api/v5/result', {
      prediction_id: predictionId,
      actual_result: actualResult,
      actual_odds: actualOdds
    });
    return response.data;
  } catch (error) {
    console.error('結果登録エラー:', error);
    throw error;
  }
};

/**
 * ヘルスチェック
 */
export const healthCheck = async () => {
  try {
    const response = await apiClient.get('/');
    return response.data;
  } catch (error) {
    console.error('ヘルスチェックエラー:', error);
    throw error;
  }
};

export default apiClient;
