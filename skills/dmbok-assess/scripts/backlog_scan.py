#!/usr/bin/env python3
"""
Backlog のエクスポートデータを DMBOK 観点で分析し、構造化された Markdown を出力するツール。
backlog-exporter の出力ディレクトリを入力として受け取る。

使い方:
    python skills/dmbok-assess/scripts/backlog_scan.py /path/to/backlog-export
    python skills/dmbok-assess/scripts/backlog_scan.py /path/to/backlog-export --output output/backlog_result.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None


DMBOK_KEYWORDS = {
    "データガバナンス": [
        "ガバナンス", "ポリシー", "標準", "規約", "ルール", "governance",
        "policy", "standard", "guideline", "コンプライアンス", "compliance",
    ],
    "データアーキテクチャ": [
        "アーキテクチャ", "設計", "構成", "architecture", "design",
        "インフラ", "infrastructure", "技術選定",
    ],
    "データモデリング": [
        "モデル", "テーブル", "スキーマ", "ER図", "DDL", "model", "schema",
        "データベース設計", "正規化", "カラム", "リレーション",
    ],
    "データストレージ・運用": [
        "バックアップ", "リストア", "運用", "メンテナンス", "パフォーマンス",
        "backup", "restore", "operation", "maintenance", "performance",
        "障害", "復旧", "DR", "災害",
    ],
    "データセキュリティ": [
        "セキュリティ", "権限", "認証", "認可", "暗号", "security",
        "authentication", "authorization", "encryption", "脆弱性",
        "アクセス制御", "個人情報", "漏洩",
    ],
    "データ統合": [
        "連携", "統合", "ETL", "ELT", "API", "インポート", "エクスポート",
        "integration", "sync", "同期", "バッチ", "パイプライン",
    ],
    "ドキュメント管理": [
        "ドキュメント", "文書", "マニュアル", "手順書", "仕様書",
        "document", "wiki", "ナレッジ", "knowledge",
    ],
    "マスターデータ": [
        "マスタ", "マスター", "master", "参照データ", "コード値",
        "区分", "master data", "MDM",
    ],
    "DWH・BI": [
        "DWH", "データウェアハウス", "BI", "レポート", "ダッシュボード",
        "分析", "warehouse", "analytics", "KPI", "可視化",
    ],
    "メタデータ": [
        "メタデータ", "データカタログ", "データ辞書", "用語", "定義",
        "metadata", "catalog", "glossary", "リネージ", "lineage",
    ],
    "データ品質": [
        "品質", "バリデーション", "検証", "テスト", "quality",
        "validation", "データクレンジング", "重複", "不整合", "欠損",
    ],
}


import re


def load_json_files(directory: str) -> list[dict]:
    """ディレクトリ内のJSONファイルを読み込む。"""
    results = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".json"):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                        if isinstance(data, list):
                            results.extend(data)
                        else:
                            results.append(data)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
    return results


def load_markdown_files(directory: str) -> list[dict]:
    """ディレクトリ内のMarkdownファイルをメタ情報として読み込む。"""
    results = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith(".md"):
                filepath = os.path.join(root, f)
                try:
                    with open(filepath, "r", encoding="utf-8") as fh:
                        content = fh.read()
                    results.append({
                        "path": filepath,
                        "name": f,
                        "content_preview": content[:500],
                        "size": len(content),
                    })
                except UnicodeDecodeError:
                    pass
    return results


def _extract_field(text: str, label: str) -> str:
    """Markdown の「- ラベル: 値」形式からフィールド値を抽出する。"""
    pattern = rf"^-\s*{re.escape(label)}:\s*(.+)$"
    m = re.search(pattern, text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def parse_issue_markdown(filepath: str) -> dict | None:
    """backlog-exporter が出力したチケット Markdown を構造化データにパースする。

    期待するフォーマット:
        # タイトル
        ## 基本情報
        - 課題キー: XXXX-NNN
        - ステータス: 完了
        - 優先度: 中
        - 担当者: XXX
        - 作成日時: ...
        - 更新日時: ...
        ## 詳細
        (本文)
    """
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            content = fh.read()
    except (UnicodeDecodeError, OSError):
        return None

    title_match = re.match(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else Path(filepath).stem

    issue_key = _extract_field(content, "課題キー")
    if not issue_key:
        return None

    status = _extract_field(content, "ステータス")
    priority = _extract_field(content, "優先度")
    assignee = _extract_field(content, "担当者")

    description = ""
    detail_match = re.search(r"^## 詳細\s*\n(.*?)(?=^## |\Z)", content, re.MULTILINE | re.DOTALL)
    if detail_match:
        description = detail_match.group(1).strip()

    return {
        "summary": title,
        "issueKey": issue_key,
        "status": {"name": status} if status else {"name": "不明"},
        "issueType": {"name": "課題"},
        "priority": priority,
        "assignee": assignee,
        "description": description,
        "source_file": filepath,
    }


def load_issue_markdowns(directory: str) -> list[dict]:
    """ディレクトリ内のチケット Markdown ファイルをパースして返す。"""
    results = []
    for root, _, files in os.walk(directory):
        for f in files:
            if not f.endswith(".md"):
                continue
            parsed = parse_issue_markdown(os.path.join(root, f))
            if parsed:
                results.append(parsed)
    return results


def classify_by_dmbok(text: str) -> list[str]:
    """テキスト内容をDMBOK領域に分類する。"""
    matched = []
    text_lower = text.lower()
    for domain, keywords in DMBOK_KEYWORDS.items():
        if any(kw.lower() in text_lower for kw in keywords):
            matched.append(domain)
    return matched


def analyze_issues(issues: list[dict]) -> dict:
    """チケット（課題）データを分析する。"""
    analysis = {
        "total": len(issues),
        "by_status": defaultdict(int),
        "by_type": defaultdict(int),
        "by_domain": defaultdict(list),
        "data_related": [],
    }

    for issue in issues:
        summary = issue.get("summary", issue.get("title", ""))
        description = issue.get("description", issue.get("body", ""))
        status = issue.get("status", {})
        if isinstance(status, dict):
            status = status.get("name", "不明")
        issue_type = issue.get("issueType", issue.get("type", {}))
        if isinstance(issue_type, dict):
            issue_type = issue_type.get("name", "不明")

        analysis["by_status"][str(status)] += 1
        analysis["by_type"][str(issue_type)] += 1

        combined_text = f"{summary} {description}"
        domains = classify_by_dmbok(combined_text)
        if domains:
            issue_info = {
                "key": issue.get("issueKey", issue.get("key", issue.get("id", "N/A"))),
                "summary": summary[:80],
                "domains": domains,
                "status": str(status),
            }
            analysis["data_related"].append(issue_info)
            for domain in domains:
                analysis["by_domain"][domain].append(issue_info)

    return analysis


def analyze_pages(pages: list[dict]) -> dict:
    """Wiki / Documents ページデータを分析する。"""
    analysis = {
        "total": len(pages),
        "by_domain": defaultdict(list),
        "pages": [],
    }

    for page in pages:
        name = page.get("name", page.get("title", Path(page.get("path", "")).stem))
        content = page.get("content", page.get("content_preview", ""))

        domains = classify_by_dmbok(f"{name} {content}")
        page_info = {"name": name, "domains": domains, "source": page.get("source", "不明")}
        analysis["pages"].append(page_info)
        for domain in domains:
            analysis["by_domain"][domain].append(page_info)

    return analysis


def find_dir(base: str, candidates: list[str]) -> str | None:
    """base 直下から候補名のディレクトリを探す。"""
    for name in candidates:
        path = os.path.join(base, name)
        if os.path.isdir(path):
            return path
    return None


def load_pages_from_dir(directory: str, source_label: str) -> list[dict]:
    """ディレクトリから Markdown / JSON ページを読み込み、source ラベルを付与する。"""
    pages = []
    for item in load_markdown_files(directory):
        item["source"] = source_label
        pages.append(item)
    for item in load_json_files(directory):
        if "name" in item or "title" in item or "content" in item:
            item["source"] = source_label
            pages.append(item)
    return pages


def scan_backlog_export(export_path: str) -> dict:
    """Backlogエクスポートディレクトリを走査する。"""
    result = {
        "export_path": os.path.abspath(export_path),
        "scan_date": datetime.now().isoformat(),
        "issues": {"total": 0, "analysis": {}},
        "documents": {"total": 0, "analysis": {}},
        "wiki": {"total": 0, "analysis": {}},
        "files_found": defaultdict(int),
    }

    for root, dirs, files in os.walk(export_path):
        for f in files:
            ext = Path(f).suffix.lower()
            result["files_found"][ext] += 1

    # チケット（issues）の検出 — JSON 形式と Markdown 形式の両方に対応
    issues = []

    issues_dir = find_dir(export_path, [
        "issues", "issue", "tickets", "チケット",
    ])

    # 1) JSON 形式のチケット
    json_search_dir = issues_dir or export_path
    all_json = load_json_files(json_search_dir)
    json_issues = [item for item in all_json if "summary" in item or "title" in item or "issueKey" in item]
    issues.extend(json_issues)

    # 2) Markdown 形式のチケット（backlog-exporter の出力形式）
    if issues_dir:
        md_issues = load_issue_markdowns(issues_dir)
        issues.extend(md_issues)

    if issues:
        result["issues"]["total"] = len(issues)
        result["issues"]["analysis"] = analyze_issues(issues)

    # Documents（Backlog の新しいドキュメント機能）
    docs_dir = find_dir(export_path, [
        "documents", "Documents", "docs", "Docs",
        "ドキュメント", "document", "Document",
    ])
    doc_pages = []
    if docs_dir:
        doc_pages = load_pages_from_dir(docs_dir, "Documents")
    if doc_pages:
        result["documents"]["total"] = len(doc_pages)
        result["documents"]["analysis"] = analyze_pages(doc_pages)

    # Wiki（従来のWiki機能）
    wiki_dir = find_dir(export_path, [
        "wiki", "Wiki", "pages", "Pages",
    ])
    wiki_pages = []
    if wiki_dir:
        wiki_pages = load_pages_from_dir(wiki_dir, "Wiki")
    if not wiki_pages and not doc_pages:
        all_md = load_markdown_files(export_path)
        wiki_pages = [p for p in all_md if "wiki" in p["path"].lower() or "document" in p["path"].lower()]
        for p in wiki_pages:
            p["source"] = "Wiki"
    if wiki_pages:
        result["wiki"]["total"] = len(wiki_pages)
        result["wiki"]["analysis"] = analyze_pages(wiki_pages)

    return result


def generate_report(data: dict) -> str:
    """走査結果をMarkdownレポートに変換する。"""
    lines = []
    lines.append("# Backlog エクスポートデータ走査結果")
    lines.append("")
    lines.append(f"- **エクスポートパス**: `{data['export_path']}`")
    lines.append(f"- **走査日時**: {data['scan_date']}")
    lines.append("")

    lines.append("## ファイル種別の分布")
    lines.append("")
    lines.append("| 拡張子 | ファイル数 |")
    lines.append("|--------|-----------|")
    for ext, count in sorted(data["files_found"].items(), key=lambda x: -x[1]):
        lines.append(f"| {ext or '(なし)'} | {count} |")
    lines.append("")

    issue_analysis = data["issues"].get("analysis", {})
    lines.append("## チケット分析")
    lines.append("")
    lines.append(f"- **総チケット数**: {data['issues']['total']}")
    lines.append("")

    if issue_analysis.get("by_status"):
        lines.append("### ステータス別")
        lines.append("")
        lines.append("| ステータス | 件数 |")
        lines.append("|-----------|------|")
        for status, count in sorted(issue_analysis["by_status"].items(), key=lambda x: -x[1]):
            lines.append(f"| {status} | {count} |")
        lines.append("")

    if issue_analysis.get("by_type"):
        lines.append("### 種別")
        lines.append("")
        lines.append("| 種別 | 件数 |")
        lines.append("|------|------|")
        for t, count in sorted(issue_analysis["by_type"].items(), key=lambda x: -x[1]):
            lines.append(f"| {t} | {count} |")
        lines.append("")

    lines.append("### DMBOK領域別の関連チケット")
    lines.append("")
    by_domain = issue_analysis.get("by_domain", {})
    if by_domain:
        for domain in DMBOK_KEYWORDS:
            domain_issues = by_domain.get(domain, [])
            lines.append(f"#### {domain} ({len(domain_issues)}件)")
            lines.append("")
            if domain_issues:
                for issue in domain_issues[:10]:
                    lines.append(f"- [{issue['key']}] {issue['summary']} (ステータス: {issue['status']})")
                if len(domain_issues) > 10:
                    lines.append(f"- ... 他 {len(domain_issues) - 10} 件")
            else:
                lines.append("関連チケットなし")
            lines.append("")
    else:
        lines.append("データ関連のチケットは検出されませんでした。")
        lines.append("")

    # Documents 分析
    doc_analysis = data.get("documents", {}).get("analysis", {})
    lines.append("## Documents 分析")
    lines.append("")
    lines.append(f"- **総ページ数**: {data.get('documents', {}).get('total', 0)}")
    lines.append("")

    doc_by_domain = doc_analysis.get("by_domain", {})
    if doc_by_domain:
        lines.append("### DMBOK領域別の Documents ページ")
        lines.append("")
        for domain in DMBOK_KEYWORDS:
            pages = doc_by_domain.get(domain, [])
            if pages:
                lines.append(f"#### {domain} ({len(pages)}件)")
                lines.append("")
                for page in pages[:10]:
                    lines.append(f"- {page['name']}")
                lines.append("")
    else:
        lines.append("Documents は検出されませんでした。")
        lines.append("")

    # Wiki 分析
    wiki_analysis = data["wiki"].get("analysis", {})
    lines.append("## Wiki 分析")
    lines.append("")
    lines.append(f"- **総ページ数**: {data['wiki']['total']}")
    lines.append("")

    wiki_by_domain = wiki_analysis.get("by_domain", {})
    if wiki_by_domain:
        lines.append("### DMBOK領域別の Wiki ページ")
        lines.append("")
        for domain in DMBOK_KEYWORDS:
            pages = wiki_by_domain.get(domain, [])
            if pages:
                lines.append(f"#### {domain} ({len(pages)}件)")
                lines.append("")
                for page in pages[:10]:
                    lines.append(f"- {page['name']}")
                lines.append("")
    else:
        lines.append("Wiki は検出されませんでした。")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Backlog エクスポートデータを DMBOK 観点で分析し、構造化レポートを出力する"
    )
    parser.add_argument("export_path", help="backlog-exporter の出力ディレクトリパス")
    parser.add_argument("--output", "-o", help="レポート出力先ファイルパス（省略時は標準出力）")
    args = parser.parse_args()

    if not os.path.isdir(args.export_path):
        print(f"Error: {args.export_path} はディレクトリではありません。", file=sys.stderr)
        sys.exit(1)

    data = scan_backlog_export(args.export_path)
    report = generate_report(data)

    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"レポートを {args.output} に出力しました。", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
