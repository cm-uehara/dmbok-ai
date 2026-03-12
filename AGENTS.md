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
├── CLAUDE.md                          # Claude Code 向け指示
├── skills/                            # スキル本体（環境非依存）
│   ├── dmbok-assess/                  # DMBOK診断スキル
│   │   ├── README.md                  # スキルの指示本体
│   │   ├── scripts/                   # データ収集・レポート生成ツール
│   │   │   ├── git_scan.py            # Gitリポジトリ走査
│   │   │   ├── backlog_scan.py        # Backlogエクスポートデータ走査
│   │   │   ├── generate_report.py     # HTML/PDFリッチレポート生成
│   │   │   └── requirements.txt       # Python依存パッケージ
│   │   ├── references/
│   │   │   └── assessment_schema.json # アセスメント結果JSONスキーマ
│   │   └── assets/
│   │       ├── report_template.html   # レポートHTMLテンプレート
│   │       └── template_assessment.md # Markdownレポートテンプレート
│   └── dmbok-consult/
│       └── README.md                  # 壁打ち相談スキル
├── .cursor/skills/                    # Cursor 向けトリガー（薄いラッパー）
│   ├── dmbok-assess/SKILL.md
│   └── dmbok-consult/SKILL.md
└── output/                            # レポート出力先
```

## 使い方

* **DMBOK診断**: 「このリポジトリをDMBOK診断して」→ dmbok-assess スキルが実行フローを案内する
* **壁打ち・相談**: 「データガバナンスについて相談したい」→ dmbok-consult スキルが対話的にアドバイスする

## Agentへの指示

* 日本語で応答すること
* `knowledge/` のファイルは評価の根拠として常に参照すること
* スコアリングは根拠に基づいて行い、推測でスコアを付けないこと
* レポートには具体的なファイルパスやドキュメント名を引用すること（Backlogのチケット番号は流動的なため記載不要。内容・傾向で言及する）
* 改善提案は現実的で段階的なものにすること
