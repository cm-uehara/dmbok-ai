# DMBOK AI — データマネジメント成熟度診断システム

## システム構想

* Cursor / Claude Code のAIエージェントとして動作する
* DMBOKのナレッジベース（`knowledge/`）に基づき、対象環境を診断する
* Gitリポジトリの走査やbacklog-exporterによるBacklog情報抽出でデータを収集する
* 11の知識領域ごとに成熟度をスコアリングし、レポートを出力する
* データガバナンス推進の壁打ち・相談相手としても機能する

## プロジェクト構成

```
dmbok-ai/
├── AGENTS.md                          # このファイル（プロジェクト全体の指示）
├── knowledge/                         # DMBOKナレッジベース
│   ├── 00_overview.md                 # 全体像・スコアリング方針
│   ├── 01_data_governance.md          # データガバナンス
│   ├── 02_data_architecture.md        # データアーキテクチャ
│   ├── 03_data_modeling_and_design.md # データモデリングとデザイン
│   ├── 04_data_storage_and_operations.md # データストレージとオペレーション
│   ├── 05_data_security.md            # データセキュリティ
│   ├── 06_data_integration_and_interoperability.md # データ統合と相互運用性
│   ├── 07_document_and_content_management.md # ドキュメントとコンテンツ管理
│   ├── 08_reference_and_master_data.md # 参照データとマスターデータ
│   ├── 09_data_warehousing_and_bi.md  # DWHとBI
│   ├── 10_metadata_management.md      # メタデータ管理
│   └── 11_data_quality.md             # データ品質
├── tools/                             # データ収集・レポート生成ツール（Python CLI）
│   ├── git_scan.py                    # Gitリポジトリ走査
│   ├── backlog_scan.py                # Backlogエクスポートデータ走査
│   ├── generate_report.py             # HTML/PDFリッチレポート生成
│   ├── report_template.html           # レポートHTMLテンプレート
│   ├── assessment_schema.json         # アセスメント結果JSONスキーマ
│   └── requirements.txt               # Python依存パッケージ
├── .cursor/
│   ├── skills/
│   │   ├── dmbok-assess/SKILL.md      # DMBOK診断スキル
│   │   └── dmbok-consult/SKILL.md     # 壁打ち相談スキル
│   └── rules/
│       └── dmbok-scoring.mdc          # スコアリングルール
└── output/                            # レポート出力先
```

## 使い方

### DMBOK診断（アセスメント）

「このリポジトリをDMBOK診断して」のように依頼すると、dmbok-assess スキルが起動する。

1. ナレッジベース（`knowledge/`）を読み込み
2. 収集ツール（`tools/git_scan.py`, `tools/backlog_scan.py`）を実行
3. 11領域ごとにスコアリング
4. Markdownレポート + JSON を `output/` に出力
5. `tools/generate_report.py` でリッチ HTML/PDF レポートを生成

### 壁打ち・相談

「データガバナンスについて相談したい」のように依頼すると、dmbok-consult スキルが起動する。ナレッジベースに基づいて対話的にアドバイスする。

## Agentへの指示

* 日本語で応答すること
* `knowledge/` のファイルは評価の根拠として常に参照すること
* スコアリングは根拠に基づいて行い、推測でスコアを付けないこと
* レポートには具体的なファイルパスやドキュメント名を引用すること（Backlogのチケット番号は流動的なため記載不要。内容・傾向で言及する）
* 改善提案は現実的で段階的なものにすること
