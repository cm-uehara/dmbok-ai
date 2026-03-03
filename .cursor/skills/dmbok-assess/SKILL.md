---
name: dmbok-assess
description: DMBOK（データマネジメント知識体系）の11領域に基づいてGitリポジトリやBacklogプロジェクトを診断・スコアリングする。「DMBOK診断して」「データマネジメントの成熟度を評価して」「リポジトリを分析して」と依頼されたときに使用する。
---

# DMBOK アセスメント（診断・スコアリング）

## 概要

対象のGitリポジトリやBacklogエクスポートデータをDMBOKの11領域で診断し、成熟度スコアとレポートを出力する。

## 実行フロー

### Step 1: ナレッジベースの読み込み

まず以下を読み込んで評価基準を把握する:

- `knowledge/00_overview.md` — 全体像とスコアリング方針
- 診断に必要な領域の個別ファイル（`knowledge/01_data_governance.md` 〜 `knowledge/11_data_quality.md`）

### Step 2: データ収集

対象に応じて収集ツールを実行する。

**Gitリポジトリの場合:**

```bash
python tools/git_scan.py /path/to/target-repo
```

**Backlogエクスポートの場合:**

```bash
python tools/backlog_scan.py /path/to/backlog-export
```

両方がある場合は両方実行する。ツール実行前に `pip install -r tools/requirements.txt` が必要な場合がある。

### Step 3: スコアリング

収集結果とナレッジベースの評価観点を照合し、11領域それぞれについて以下を判定する:

1. **成熟度スコア（1〜5）** — `knowledge/` 内の各領域の「成熟度レベル定義」に基づく
2. **根拠** — スコアの判定理由（具体的なファイルやチケットを引用）
3. **改善提案** — 次のレベルに進むための具体的アクション

### Step 4: レポート出力

**2段階で出力する: (1) Markdownレポート (2) リッチHTML/PDF レポート**

#### 4a. Markdownレポート

`output/assessment_YYYYMMDD.md` にMarkdown形式のレポートを出力する（従来通り）。

#### 4b. リッチレポート用 JSON の作成

スコアリング結果を以下の JSON 形式で `output/assessment_YYYYMMDD.json` に保存する。
スキーマの詳細は `tools/assessment_schema.json` を参照。

```json
{
  "target": "リポジトリ名",
  "date": "YYYY-MM-DD",
  "data_sources": ["Git リポジトリ", "Backlog"],
  "executive_summary": "全体の要約...",
  "scores": [
    {
      "id": 1,
      "domain": "データガバナンス",
      "score": 3,
      "level": "定義済み",
      "findings": "主な所見（1行）",
      "strengths": ["強み1", "強み2"],
      "issues": ["課題1", "課題2"],
      "recommendations": ["改善提案1", "改善提案2"]
    }
  ],
  "roadmap": {
    "short_term": [{"priority": "高", "domain": "...", "action": "...", "impact": "..."}],
    "mid_term": [...],
    "long_term": [...]
  },
  "limitations": ["制約事項1", "制約事項2"]
}
```

#### 4c. HTML/PDF レポート生成

JSON を作成したら、以下のコマンドで HTML レポートを生成する:

```bash
python tools/generate_report.py output/assessment_YYYYMMDD.json --out-dir output/
```

PDF も生成する場合は `--pdf` フラグを付ける（要 playwright）:

```bash
python tools/generate_report.py output/assessment_YYYYMMDD.json --out-dir output/ --pdf
```

生成されるファイル:
- `output/assessment_YYYYMMDD.html` — レーダーチャート・カラーコード付きのリッチレポート
- `output/assessment_YYYYMMDD.pdf` — PDF版（`--pdf` 指定時）

## 注意事項

- 情報が不足している領域は「情報不足のため評価困難」と明記し、無理にスコアを付けない
- リポジトリだけでは判断できない項目（組織体制、教育等）はその旨を記載する
- ユーザーに追加情報を確認しながら進めることを推奨
- PDF 生成には `pip install playwright && playwright install chromium` が必要
