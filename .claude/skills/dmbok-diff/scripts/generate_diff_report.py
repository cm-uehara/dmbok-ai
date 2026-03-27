#!/usr/bin/env python3
"""
DMBOK アセスメント差分比較レポート生成ツール。
2つのアセスメント JSON を比較し、スコア推移・改善/悪化をハイライトした
HTML レポート（+ PDF）を生成する。

使い方:
    python .claude/skills/dmbok-diff/scripts/generate_diff_report.py output/assessment_before.json output/assessment_after.json
    python .claude/skills/dmbok-diff/scripts/generate_diff_report.py output/assessment_before.json output/assessment_after.json --pdf
    python .claude/skills/dmbok-diff/scripts/generate_diff_report.py output/assessment_before.json output/assessment_after.json --out-dir output/

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
    template_path = Path(__file__).parent / "../assets/diff_report_template.html"
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def get_colors(score: int) -> dict:
    return SCORE_COLORS.get(score, SCORE_COLORS[1])


def diff_lists(before_list: list, after_list: list) -> tuple:
    """2つのリストを比較し、(追加された項目, 削除された項目, 継続中の項目) を返す。

    完全一致だけでなく、部分一致も考慮して類似項目を検出する。
    """
    before_set = set(before_list)
    after_set = set(after_list)

    # 完全一致で分類
    exact_continuing = before_set & after_set
    candidates_removed = before_set - exact_continuing
    candidates_added = after_set - exact_continuing

    # 部分一致で追加の類似検出（短い方が長い方に含まれていれば類似とみなす）
    similar_pairs = []
    for b in list(candidates_removed):
        for a in list(candidates_added):
            b_norm = b.replace(" ", "").replace("　", "")
            a_norm = a.replace(" ", "").replace("　", "")
            # 一方が他方の部分文字列、または共通部分が十分長い
            if b_norm in a_norm or a_norm in b_norm:
                similar_pairs.append((b, a))
            elif len(set(b_norm) & set(a_norm)) / max(len(set(b_norm)), len(set(a_norm)), 1) > 0.7:
                similar_pairs.append((b, a))

    fuzzy_continuing_before = set()
    fuzzy_continuing_after = set()
    for b, a in similar_pairs:
        if b not in fuzzy_continuing_before and a not in fuzzy_continuing_after:
            fuzzy_continuing_before.add(b)
            fuzzy_continuing_after.add(a)

    added = list(candidates_added - fuzzy_continuing_after)
    removed = list(candidates_removed - fuzzy_continuing_before)
    continuing = list(exact_continuing) + list(fuzzy_continuing_after)

    return added, removed, continuing


def build_comparison(before: dict, after: dict) -> dict:
    """2つのアセスメント JSON を比較し、テンプレート用データを構築する。"""
    before_scores = {s["id"]: s for s in before.get("scores", [])}
    after_scores = {s["id"]: s for s in after.get("scores", [])}

    before_date = before.get("date", "不明")
    after_date = after.get("date", "不明")

    # 日付の前後を自動判定（after の方が古い場合はスワップ）
    if before_date > after_date:
        before, after = after, before
        before_scores, after_scores = after_scores, before_scores
        before_date, after_date = after_date, before_date

    before_values = []
    after_values = []
    domains = []
    improved_count = 0
    regressed_count = 0
    unchanged_count = 0

    for domain_id in range(1, 12):
        bs = before_scores.get(domain_id, {})
        as_ = after_scores.get(domain_id, {})

        b_score = bs.get("score", 0)
        a_score = as_.get("score", 0)
        delta = a_score - b_score

        before_values.append(b_score)
        after_values.append(a_score)

        b_colors = get_colors(b_score)
        a_colors = get_colors(a_score)

        # 課題と強みの差分
        new_strengths, lost_strengths, _ = diff_lists(
            bs.get("strengths", []), as_.get("strengths", [])
        )
        new_issues, resolved_issues, continuing_issues = diff_lists(
            bs.get("issues", []), as_.get("issues", [])
        )
        # diff_lists は (added, removed, continuing) を返す
        # issues の場合: added=新たな課題, removed=解消された課題

        # コメント生成
        if delta > 0:
            comment = f"レベル{b_score}({bs.get('level', '')}) → レベル{a_score}({as_.get('level', '')}) に改善"
            improved_count += 1
        elif delta < 0:
            comment = f"レベル{b_score}({bs.get('level', '')}) → レベル{a_score}({as_.get('level', '')}) に悪化"
            regressed_count += 1
        else:
            comment = f"レベル{a_score}({as_.get('level', '')}) を維持"
            unchanged_count += 1

        domains.append({
            "id": domain_id,
            "domain": as_.get("domain", bs.get("domain", f"領域{domain_id}")),
            "before_score": b_score,
            "after_score": a_score,
            "delta": delta,
            "comment": comment,
            "before_color_bg": b_colors["bg"],
            "before_color_border": b_colors["border"],
            "before_color_text": b_colors["text"],
            "after_color_bg": a_colors["bg"],
            "after_color_border": a_colors["border"],
            "after_color_text": a_colors["text"],
            "new_strengths": new_strengths,
            "lost_strengths": lost_strengths,
            "resolved_issues": resolved_issues,
            "new_issues": new_issues,
            "continuing_issues": continuing_issues,
        })

    before_avg = round(sum(before_values) / len(before_values), 1) if before_values else 0
    after_avg = round(sum(after_values) / len(after_values), 1) if after_values else 0
    avg_delta = round(after_avg - before_avg, 1)

    # ロードマップ進捗（前回のロードマップがある場合）
    roadmap_progress = []
    before_roadmap = before.get("roadmap", {})
    phase_map = {
        "short_term": "短期",
        "mid_term": "中期",
        "long_term": "長期",
    }
    for phase_key, phase_label in phase_map.items():
        items = before_roadmap.get(phase_key, [])
        for item in items:
            domain_name = item.get("domain", "")
            action = item.get("action", "")

            # 対応する領域のスコア変化から進捗を推定
            status = "not_started"
            note = ""
            for d in domains:
                if domain_name in d["domain"] or d["domain"] in domain_name:
                    if d["delta"] > 0:
                        status = "done"
                        note = f"スコアが {d['before_score']} → {d['after_score']} に改善"
                    elif d["resolved_issues"]:
                        status = "partial"
                        note = f"一部の課題が解消（スコアは {d['after_score']} で維持）"
                    else:
                        status = "not_started"
                        note = f"スコアに変化なし（{d['after_score']}）"
                    break

            roadmap_progress.append({
                "phase": phase_label,
                "domain": domain_name,
                "action": action,
                "status": status,
                "note": note,
            })

    # target はどちらか情報がある方を使用
    target = after.get("target", before.get("target", "不明"))

    return {
        "target": target,
        "before_date": before_date,
        "after_date": after_date,
        "before_avg": before_avg,
        "after_avg": after_avg,
        "avg_delta": avg_delta,
        "improved_count": improved_count,
        "regressed_count": regressed_count,
        "unchanged_count": unchanged_count,
        "domains": domains,
        "before_values_json": json.dumps(before_values),
        "after_values_json": json.dumps(after_values),
        "domain_labels_json": json.dumps(DOMAIN_LABELS_SHORT, ensure_ascii=False),
        "roadmap_progress": roadmap_progress if roadmap_progress else None,
        "generation_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def generate_html(before: dict, after: dict) -> str:
    template_str = load_template()
    template = Template(template_str)
    data = build_comparison(before, after)
    return template.render(**data)


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
        description="2つの DMBOK アセスメント結果を比較し、差分 HTML/PDF レポートを生成する"
    )
    parser.add_argument("before_json", help="前回のアセスメント結果 JSON ファイルパス")
    parser.add_argument("after_json", help="今回のアセスメント結果 JSON ファイルパス")
    parser.add_argument("--pdf", action="store_true", help="PDF も生成する（要 playwright）")
    parser.add_argument("--out-dir", default=None, help="出力先ディレクトリ（デフォルト: 入力と同じ）")
    args = parser.parse_args()

    with open(args.before_json, "r", encoding="utf-8") as f:
        before = json.load(f)
    with open(args.after_json, "r", encoding="utf-8") as f:
        after = json.load(f)

    # 日付を取得してファイル名に使用
    before_date = before.get("date", "unknown").replace("-", "")
    after_date = after.get("date", "unknown").replace("-", "")

    # 日付の前後を自動判定
    if before_date > after_date:
        before_date, after_date = after_date, before_date

    out_dir = args.out_dir or os.path.dirname(args.after_json) or "."
    os.makedirs(out_dir, exist_ok=True)

    base_name = f"diff_{before_date}_vs_{after_date}"
    html_path = os.path.join(out_dir, f"{base_name}.html")

    html_content = generate_html(before, after)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML を {html_path} に出力しました。", file=sys.stderr)

    if args.pdf:
        pdf_path = os.path.join(out_dir, f"{base_name}.pdf")
        generate_pdf(html_path, pdf_path)


if __name__ == "__main__":
    main()
