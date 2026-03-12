#!/usr/bin/env python3
"""
DMBOK アセスメント結果から、リッチな HTML レポートと PDF を生成するツール。
Agent がスコアリング結果を JSON で出力し、本ツールで HTML/PDF に変換する。

使い方:
    python .claude/skills/dmbok-assess/scripts/generate_report.py output/assessment_data.json
    python .claude/skills/dmbok-assess/scripts/generate_report.py output/assessment_data.json --pdf
    python .claude/skills/dmbok-assess/scripts/generate_report.py output/assessment_data.json --out-dir output/

入力 JSON の形式は .claude/skills/dmbok-assess/references/assessment_schema.json を参照。
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from jinja2 import Template
except ImportError:
    print("Error: jinja2 が必要です。pip install jinja2 を実行してください。", file=sys.stderr)
    sys.exit(1)


SCORE_COLORS = {
    1: {"bg": "#fef2f2", "border": "#ef4444", "text": "#dc2626", "label": "初期"},
    2: {"bg": "#fff7ed", "border": "#f97316", "text": "#ea580c", "label": "反復可能"},
    3: {"bg": "#fefce8", "border": "#eab308", "text": "#ca8a04", "label": "定義済み"},
    4: {"bg": "#eff6ff", "border": "#3b82f6", "text": "#2563eb", "label": "管理済み"},
    5: {"bg": "#f0fdf4", "border": "#22c55e", "text": "#16a34a", "label": "最適化"},
}

DOMAIN_LABELS_SHORT = [
    "ガバナンス", "アーキテクチャ", "モデリング", "ストレージ/運用",
    "セキュリティ", "統合/相互運用", "ドキュメント", "マスターデータ",
    "DWH/BI", "メタデータ", "データ品質",
]


def load_template() -> str:
    template_path = Path(__file__).parent / "../assets/report_template.html"
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def enrich_data(data: dict) -> dict:
    """テンプレートに必要な派生データを追加する。"""
    scores = data.get("scores", [])

    for s in scores:
        score_val = s.get("score", 0)
        colors = SCORE_COLORS.get(score_val, SCORE_COLORS[1])
        s["color_bg"] = colors["bg"]
        s["color_border"] = colors["border"]
        s["color_text"] = colors["text"]
        s["level_label"] = s.get("level", colors["label"])
        s["score_pct"] = (score_val / 5) * 100

    score_values = [s.get("score", 0) for s in scores]
    avg = sum(score_values) / len(score_values) if score_values else 0
    data["average_score"] = round(avg, 1)
    data["score_values_json"] = json.dumps(score_values)
    data["domain_labels_json"] = json.dumps(DOMAIN_LABELS_SHORT, ensure_ascii=False)
    data["score_colors"] = SCORE_COLORS
    data["generation_time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    return data


def generate_html(data: dict) -> str:
    template_str = load_template()
    template = Template(template_str)
    enriched = enrich_data(data)
    return template.render(**enriched)


def generate_pdf(html_path: str, pdf_path: str):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Error: PDF生成には playwright が必要です。\n"
            "  pip install playwright\n"
            "  playwright install chromium",
            file=sys.stderr,
        )
        sys.exit(1)

    abs_html = os.path.abspath(html_path)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 840, "height": 1200})
        page.goto(f"file://{abs_html}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1500)
        page.pdf(
            path=pdf_path,
            format="A4",
            print_background=True,
            scale=0.74,
            margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"},
        )
        browser.close()

    print(f"PDF を {pdf_path} に出力しました。", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="DMBOK アセスメント結果の JSON から HTML/PDF レポートを生成する"
    )
    parser.add_argument("input_json", help="アセスメント結果の JSON ファイルパス")
    parser.add_argument("--pdf", action="store_true", help="PDF も生成する（要 playwright）")
    parser.add_argument("--out-dir", default=None, help="出力先ディレクトリ（デフォルト: 入力と同じ）")
    args = parser.parse_args()

    with open(args.input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    out_dir = args.out_dir or os.path.dirname(args.input_json) or "."
    os.makedirs(out_dir, exist_ok=True)

    base_name = Path(args.input_json).stem
    html_path = os.path.join(out_dir, f"{base_name}.html")

    html_content = generate_html(data)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML を {html_path} に出力しました。", file=sys.stderr)

    if args.pdf:
        pdf_path = os.path.join(out_dir, f"{base_name}.pdf")
        generate_pdf(html_path, pdf_path)


if __name__ == "__main__":
    main()
