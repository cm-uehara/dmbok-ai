# DMBOK AI — データマネジメント成熟度診断システム

DMBOK（Data Management Body of Knowledge）の11の知識領域に基づいて、Gitリポジトリや Backlog プロジェクトのデータマネジメント成熟度を診断し、スコアリングレポートを生成するAIエージェントシステムです。

Cursor や Claude Code のスキルとして動作し、対話的な壁打ち相談にも対応します。

## 特徴

- **DMBOK 11領域のスコアリング** — 成熟度レベル1〜5で評価し、根拠と改善提案を提示
- **リッチなレポート出力** — Markdown / HTML（レーダーチャート付き） / PDF の3形式
- **データ収集の自動化** — Gitリポジトリの構造解析、Backlogエクスポートデータの分析
- **壁打ち・相談機能** — データガバナンス推進の相談相手として対話的にアドバイス
- **Cursor / Claude Code ネイティブ** — API不要、スキルとしてそのまま動作

## 前提条件

- Python 3.9 以上
- [Cursor](https://cursor.com/ja) または [Claude Code](https://claude.com/product/claude-code)
- （PDF生成時のみ）Playwright + Chromium

## セットアップ

```bash
# 1. リポジトリをクローン / ダウンロード
git clone <repository-url>
cd dmbok-ai

# 2. Python 依存パッケージをインストール
pip install -r skills/dmbok-assess/scripts/requirements.txt

# 3. (オプション) PDF生成を使う場合
pip install playwright
playwright install chromium
```

## 使い方

### DMBOK 診断（アセスメント）

Cursor でこのプロジェクトを開き、新しいチャットで以下のように依頼します。

**Git リポジトリを診断する場合:**

```
/path/to/your-repo を DMBOK 診断して
```

**Backlog エクスポートデータを診断する場合:**

```
/path/to/backlog-export の Backlog データを DMBOK 診断して
```

**両方を診断する場合:**

```
Git リポジトリ /path/to/your-repo と Backlog エクスポート /path/to/backlog-export を DMBOK 診断して
```

**PDF も出力したい場合:**

```
/path/to/your-repo を DMBOK 診断して。PDF でもレポートを出力して
```

Agent が以下のフローを自動実行します:

1. `knowledge/` のナレッジベースを読み込み
2. `skills/dmbok-assess/scripts/git_scan.py` / `backlog_scan.py` でデータ収集
3. 11領域それぞれをスコアリング
4. `output/` に Markdown + JSON を出力
5. `skills/dmbok-assess/scripts/generate_report.py` でリッチ HTML（+ PDF）レポートを生成

### 壁打ち・相談

データマネジメントに関する相談もできます。

```
データガバナンスの進め方について相談したい
```

```
マスターデータ管理を始めたいが、何から手を付ければよいか
```

ナレッジベースに基づいて、対話的にアドバイスを提供します。

### ツール単体での利用

Agent を介さず、CLIツールを直接実行することもできます。

```bash
# Git リポジトリの走査
python skills/dmbok-assess/scripts/git_scan.py /path/to/repo
python skills/dmbok-assess/scripts/git_scan.py /path/to/repo --output output/git_scan_result.md

# Backlog エクスポートデータの走査
python skills/dmbok-assess/scripts/backlog_scan.py /path/to/backlog-export
python skills/dmbok-assess/scripts/backlog_scan.py /path/to/backlog-export --output output/backlog_scan_result.md

# アセスメント結果 JSON から HTML レポート生成
python skills/dmbok-assess/scripts/generate_report.py output/assessment_data.json --out-dir output/

# HTML + PDF レポート生成
python skills/dmbok-assess/scripts/generate_report.py output/assessment_data.json --out-dir output/ --pdf
```

## プロジェクト構成

```
dmbok-ai/
├── README.md                              # このファイル
├── AGENTS.md                              # AI Agent への指示定義
├── knowledge/                             # DMBOK ナレッジベース
│   ├── 00_overview.md                     #   全体像・スコアリング方針
│   ├── 01_data_governance.md              #   データガバナンス
│   ├── 02_data_architecture.md            #   データアーキテクチャ
│   ├── 03_data_modeling_and_design.md     #   データモデリングとデザイン
│   ├── 04_data_storage_and_operations.md  #   データストレージとオペレーション
│   ├── 05_data_security.md                #   データセキュリティ
│   ├── 06_data_integration_and_interoperability.md  #   データ統合と相互運用性
│   ├── 07_document_and_content_management.md        #   ドキュメントとコンテンツ管理
│   ├── 08_reference_and_master_data.md    #   参照データとマスターデータ
│   ├── 09_data_warehousing_and_bi.md      #   データウェアハウスと BI
│   ├── 10_metadata_management.md          #   メタデータ管理
│   └── 11_data_quality.md                 #   データ品質
├── CLAUDE.md                              # Claude Code 向け指示
├── skills/                                # スキル本体（環境非依存）
│   ├── dmbok-assess/                      #   DMBOK 診断スキル
│   │   ├── README.md                      #   スキルの指示本体
│   │   ├── scripts/                       #   データ収集・レポート生成ツール
│   │   │   ├── git_scan.py
│   │   │   ├── backlog_scan.py
│   │   │   ├── generate_report.py
│   │   │   └── requirements.txt
│   │   ├── references/
│   │   │   └── assessment_schema.json     #   アセスメント結果 JSON スキーマ
│   │   └── assets/
│   │       ├── report_template.html       #   レポート HTML テンプレート
│   │       └── template_assessment.md     #   Markdown レポートテンプレート
│   └── dmbok-consult/
│       └── README.md                      #   壁打ち相談スキル
├── .cursor/skills/                        # Cursor 向けトリガー（薄いラッパー）
│   ├── dmbok-assess/SKILL.md
│   └── dmbok-consult/SKILL.md
├── output/                                # レポート出力先
│   └── sample_assessment_data.json        #   サンプルデータ（動作確認用）
```

## DMBOK 11 の知識領域

| # | 領域 | 概要 |
|---|------|------|
| 1 | データガバナンス | データマネジメント全体の統制・方針策定 |
| 2 | データアーキテクチャ | データ構造・フロー・統合の設計 |
| 3 | データモデリングとデザイン | 概念・論理・物理モデルの設計 |
| 4 | データストレージとオペレーション | データの保管・運用・保守 |
| 5 | データセキュリティ | データの機密性・完全性・可用性の保護 |
| 6 | データ統合と相互運用性 | システム間のデータ連携・変換 |
| 7 | ドキュメントとコンテンツ管理 | 非構造化データ・文書の管理 |
| 8 | 参照データとマスターデータ | 共通データの一元管理 |
| 9 | データウェアハウスと BI | 分析基盤・意思決定支援 |
| 10 | メタデータ管理 | データに関するデータの管理 |
| 11 | データ品質 | データの正確性・一貫性・適時性の確保 |

## 成熟度レベル

各領域はレベル1〜5で評価されます。

| レベル | 名称 | 概要 |
|--------|------|------|
| 1 | 初期 (Initial) | プロセスが未定義、属人的 |
| 2 | 反復可能 (Repeatable) | 基本的なプロセスが存在するが標準化されていない |
| 3 | 定義済み (Defined) | プロセスが標準化・文書化されている |
| 4 | 管理済み (Managed) | 定量的に測定・管理されている |
| 5 | 最適化 (Optimized) | 継続的に改善されている |

## カスタマイズ

### ナレッジベースの調整

`knowledge/` 配下の `.md` ファイルを編集することで、評価基準を組織の実情に合わせてカスタマイズできます。

- 評価観点のチェック項目を追加・変更
- 成熟度レベルの基準を調整
- Git/Backlog の確認ポイントを追加

### レポートデザインの調整

`skills/dmbok-assess/assets/report_template.html` を編集することで、レポートの見た目をカスタマイズできます。
