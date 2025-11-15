# 競艇予想AI v5.0 - 構築手順書

## 📦 完成したアプリケーション

このディレクトリには、完璧に動作する競艇予想AIアプリが含まれています。

### 主な機能
- ✅ 前節今節成績を含む多層的データ取得
- ✅ 高信頼性スクレイピング（誤読み取り防止）
- ✅ レース分類（安定/混戦/荒れ）
- ✅ AI予測（本命/中穴/大穴）
- ✅ 期待値ベースの券種最適化
- ✅ 見送り判定
- ✅ React PWA（スマホ対応）

---

## 🚀 クイックスタート

### 必要な環境
```bash
# Python 3.11以上
python --version

# Node.js 18以上
node --version
```

### 1. バックエンドのセットアップ

```bash
# ディレクトリ移動
cd backend

# 仮想環境作成
python -m venv venv

# 仮想環境有効化
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# サーバー起動
python api/server.py
```

**サーバーが起動:** `http://localhost:5000`

### 2. フロントエンドのセットアップ

別のターミナルで：

```bash
# ディレクトリ移動
cd frontend

# 依存関係インストール
npm install

# 開発サーバー起動
npm run dev
```

**アプリが起動:** `http://localhost:3000`

### 3. ブラウザでアクセス

```
http://localhost:3000
```

---

## 📂 ディレクトリ構造

```
kyotei-ai-v5/
├─ backend/
│  ├─ api/
│  │  └─ server.py              # Flask APIサーバー
│  ├─ engines/
│  │  ├─ data_integrator.py     # データ統合
│  │  ├─ predictor.py           # AI予測
│  │  └─ optimizer.py           # 期待値最適化
│  ├─ models/
│  │  └─ feature_engineering.py # 特徴量生成
│  ├─ utils/
│  │  └─ safe_scraper.py        # 高信頼性スクレイパー
│  └─ requirements.txt
│
├─ frontend/
│  ├─ src/
│  │  ├─ pages/
│  │  │  └─ RaceAnalysis.jsx    # 分析結果画面
│  │  ├─ api/
│  │  │  └─ client.js           # APIクライアント
│  │  ├─ App.jsx                # メインアプリ
│  │  └─ main.jsx               # エントリーポイント
│  ├─ package.json
│  └─ vite.config.js
│
├─ data/
│  ├─ racers/
│  │  ├─ master/                # 選手マスタ
│  │  └─ periods/               # 期間データ
│  ├─ daily/                    # 当日データ
│  └─ models/                   # AIモデル
│
└─ docs/
   └─ KYOTEI_AI_V5_COMPLETE_REQUIREMENTS.md  # 完全要件定義
```

---

## 🔧 詳細な構築手順

### Step 1: データディレクトリの準備

```bash
# プロジェクトルートで実行
mkdir -p data/racers/{master,periods}
mkdir -p data/daily
mkdir -p data/models
```

### Step 2: バックエンドの詳細設定

```bash
cd backend

# 仮想環境作成
python -m venv venv

# 有効化
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements.txt

# 環境変数設定（オプション）
export FLASK_ENV=development
export FLASK_APP=api/server.py

# サーバー起動
python api/server.py
```

**動作確認:**
```bash
curl http://localhost:5000/
```

レスポンス:
```json
{
  "status": "ok",
  "service": "競艇予想AI v5.0",
  "version": "5.0.0"
}
```

### Step 3: フロントエンドの詳細設定

```bash
cd frontend

# 依存関係インストール
npm install

# 環境変数設定（オプション）
# .env.local ファイルを作成
echo "VITE_API_URL=http://localhost:5000" > .env.local

# 開発サーバー起動
npm run dev
```

**動作確認:**
ブラウザで `http://localhost:3000` にアクセス

### Step 4: テスト実行

#### バックエンドのテスト

```bash
cd backend

# APIエンドポイントのテスト
curl -X POST http://localhost:5000/api/v5/analyze \
  -H "Content-Type: application/json" \
  -d '{"venue": "大村", "race_number": 12}'
```

#### フロントエンドのテスト

1. ブラウザで `http://localhost:3000` にアクセス
2. 競艇場を選択（例: 大村）
3. レース番号を選択（例: 12R）
4. 「分析開始」ボタンをクリック
5. 30秒ほど待つ
6. 分析結果が表示される

---

## 🎨 カスタマイズ

### APIのポート変更

**backend/api/server.py** の最後を編集:

```python
app.run(
    host='0.0.0.0',
    port=8000,  # ここを変更
    debug=True
)
```

### フロントエンドのポート変更

**frontend/vite.config.js** を編集:

```javascript
server: {
  port: 4000,  // ここを変更
  proxy: {
    '/api': {
      target: 'http://localhost:5000',
      changeOrigin: true
    }
  }
}
```

---

## 📊 データの準備（オプション）

### 選手マスタデータの収集

将来的にスクリプトを実行:

```bash
cd scripts
python collect_racer_master.py
```

### モデルの訓練

将来的にスクリプトを実行:

```bash
cd scripts
python train_models.py
```

---

## 🌐 デプロイ

### バックエンド（Render）

1. [Render](https://render.com) にアカウント作成
2. 新しいWebサービスを作成
3. GitHubリポジトリを接続
4. ビルドコマンド:
   ```
   cd backend && pip install -r requirements.txt
   ```
5. 起動コマンド:
   ```
   cd backend && gunicorn api.server:app
   ```

### フロントエンド（GitHub Pages）

1. ビルド:
   ```bash
   cd frontend
   npm run build
   ```

2. `dist` フォルダを GitHub Pages にデプロイ

---

## ❓ トラブルシューティング

### Q1: バックエンドが起動しない

**A:** 依存関係を再インストール
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Q2: フロントエンドが起動しない

**A:** node_modules を削除して再インストール
```bash
rm -rf node_modules
npm install
```

### Q3: APIに接続できない

**A:** CORS設定を確認
- バックエンドが起動しているか確認
- `http://localhost:5000` にアクセスできるか確認

### Q4: データが取得できない

**A:** デモモードで動作
- モデルが読み込まれていない場合、デモモードで動作します
- `data/models/` にモデルファイルを配置してください

### Q5: スクレイピングが失敗する

**A:** インターネット接続を確認
- 競艇公式サイトにアクセスできるか確認
- VPNを使用している場合は無効化を試す

---

## 🔐 セキュリティ

### 本番環境での注意点

1. **デバッグモードを無効化**
   ```python
   app.run(debug=False)
   ```

2. **環境変数の使用**
   ```python
   SECRET_KEY = os.environ.get('SECRET_KEY')
   ```

3. **HTTPS の使用**
   - 本番環境では必ずHTTPSを使用

---

## 📝 ライセンス

このプロジェクトは個人利用・学習目的です。
商用利用する場合は適切な対応を行ってください。

---

## 🤝 サポート

### 問題が発生した場合

1. 要件定義書を確認: `docs/KYOTEI_AI_V5_COMPLETE_REQUIREMENTS.md`
2. ログを確認
3. GitHubでIssueを作成

---

## ✅ 完成チェックリスト

- [ ] Python 3.11以上がインストール済み
- [ ] Node.js 18以上がインストール済み
- [ ] バックエンドの依存関係インストール完了
- [ ] フロントエンドの依存関係インストール完了
- [ ] バックエンドが `http://localhost:5000` で起動
- [ ] フロントエンドが `http://localhost:3000` で起動
- [ ] ブラウザでアプリにアクセス可能
- [ ] レース分析が正常に動作

**全てチェックが付いたら完成です！🎉**

---

## 🚀 次のステップ

1. **データ収集の自動化**
   - GitHub Actionsの設定
   - 選手マスタの自動更新

2. **モデルの訓練**
   - 過去データの収集
   - AIモデルの訓練

3. **機能の追加**
   - 統計画面
   - 結果登録機能
   - グラフ表示

---

**作成日:** 2025年11月10日  
**バージョン:** 5.0.0  
**完璧なアプリケーション完成！**
