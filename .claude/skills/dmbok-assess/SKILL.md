---
name: dmbok-assess
description: DMBOK（データマネジメント知識体系）の11領域に基づいてGitリポジトリやBacklogプロジェクトのデータマネジメント成熟度を診断・スコアリングし、改善ロードマップを含むレポートを出力する。「DMBOK診断して」「成熟度を評価して」「リポジトリを分析して」と依頼されたときに使用する。データ管理の現状把握、リポジトリの品質チェック、Backlogプロジェクトの評価、アセスメントなど、データマネジメントの状態を可視化したい場面でも積極的に使用する。
---

# DMBOK アセスメント（診断・スコアリング）

## 概要

対象のGitリポジトリやBacklogエクスポートデータをDMBOKの11領域で診断し、成熟度スコアとレポートを出力する。

## 実行フロー

### Step 1: ナレッジベースの読み込み

まず以下を読み込んで評価基準を把握する:

- `knowledge/00_overview.md` — 全体像とスコアリング方針
- 診断に必要な領域の個別ファイル（`knowledge/01_data_governance.md` 〜 `knowledge/11_data_quality.md`）

### Step 2: データ収集（ツール実行）

対象に応じて収集ツールを実行し、全体像を把握する。

**Gitリポジトリの場合:**

```bash
python .claude/skills/dmbok-assess/scripts/git_scan.py /path/to/target-repo
```

**Backlogエクスポートの場合:**

```bash
python .claude/skills/dmbok-assess/scripts/backlog_scan.py /path/to/backlog-export
```

両方がある場合は両方実行する。ツール実行前に `pip install -r .claude/skills/dmbok-assess/scripts/requirements.txt` が必要な場合がある。

### Step 2.5: 深掘り調査（重要）

**収集ツールの出力はあくまでサマリである。スコアリングの精度を上げるために、以下のファイルを直接読んで中身を分析すること。ツール出力だけで評価を完了してはならない。**

#### Gitリポジトリの場合
ツール出力で検出されたファイルのうち、以下を優先的に読む:

- **DDL / マイグレーションファイル** — テーブル設計の品質、命名規則、制約の確認
- **README.md / docs/ 配下のドキュメント** — ドキュメントの充実度
- **CI/CD 設定ファイル** — 自動化・品質チェックの仕組み
- **API 定義ファイル** — データ連携の標準化
- **テストコード**（数ファイル） — データ品質テストの有無
- **設定ファイル / .env.example** — セキュリティ設定

#### Backlogエクスポートの場合

**最も重要なのは Documents（ドキュメント）である。** チケットはタスク管理の記録に過ぎないが、Documents にはテーブル定義・設計書・ER図・ポリシー文書など、データマネジメントの成熟度を直接反映する成果物が含まれる。

優先度の高い順に以下を読む:

1. **Documents の設計書・定義書**（最優先）— テーブル定義書、ER図、基本設計、詳細設計、要件定義など。文書の品質・網羅性・標準化の度合いを評価する
2. **Documents / Wiki のポリシー・標準文書** — 開発標準、命名規則、運用手順書など。ガバナンス・セキュリティの整備状況を評価する
3. **チケットの傾向** — チケットの内容は補助的な参考情報として使う。どの領域のタスクが多いか、課題管理の仕方がどの程度構造化されているかを見る

**読むべきファイルの目安**: Documents / Wiki から少なくとも 10〜20 ファイルは直接中身を確認する。ファイルが多い場合はディレクトリ構造を見て領域ごとに代表的なものをサンプリングする。

### Step 3: スコアリング

深掘り調査の結果とナレッジベースの評価観点を照合し、11領域それぞれについて以下を判定する:

1. **成熟度スコア（1〜5）** — `knowledge/` 内の各領域の「成熟度レベル定義」に基づく。複数のチェック項目が異なるレベルに該当する場合は、加重平均ではなく最も該当するレベルを選択する
2. **根拠** — スコアの判定理由（**直接読んだファイルの具体的な内容**を引用すること。ただし Backlog のチケット番号は流動的なためレポートに記載しない。チケットの内容・傾向で言及する）
3. **改善提案** — 次のレベルに到達するために必要な具体的アクション

### Step 4: レポート出力

**2段階で出力する: (1) Markdownレポート (2) リッチHTML/PDF レポート**

#### 4a. Markdownレポート

`output/assessment_YYYYMMDD.md` にMarkdown形式のレポートを出力する（従来通り）。

#### 4b. リッチレポート用 JSON の作成

スコアリング結果を `output/assessment_YYYYMMDD.json` に保存する。JSON の構造は `.claude/skills/dmbok-assess/references/assessment_schema.json` を読んで準拠すること。

#### 4c. HTML/PDF レポート生成

JSON を作成したら、以下のコマンドで HTML レポートを生成する:

```bash
python .claude/skills/dmbok-assess/scripts/generate_report.py output/assessment_YYYYMMDD.json --out-dir output/
```

PDF も生成する場合は `--pdf` フラグを付ける（要 playwright）:

```bash
python .claude/skills/dmbok-assess/scripts/generate_report.py output/assessment_YYYYMMDD.json --out-dir output/ --pdf
```

生成されるファイル:
- `output/assessment_YYYYMMDD.html` — レーダーチャート・カラーコード付きのリッチレポート
- `output/assessment_YYYYMMDD.pdf` — PDF版（`--pdf` 指定時）

## 注意事項

- レポートは日本語で記述する
- 情報が不足している領域は「情報不足のため評価困難」と明記し、無理にスコアを付けない
- リポジトリだけでは判断できない項目（組織体制、教育等）はその旨を記載する
- ユーザーに追加情報を確認しながら進めることを推奨
- PDF 生成には `pip install playwright && playwright install chromium` が必要
