#!/usr/bin/env python3
"""
Git リポジトリを DMBOK 観点で走査し、構造化された Markdown を出力するツール。
Cursor Agent / Claude Code から呼び出されることを想定。

使い方:
    python .claude/skills/dmbok-assess/scripts/git_scan.py /path/to/repo
    python .claude/skills/dmbok-assess/scripts/git_scan.py /path/to/repo --output output/scan_result.md
"""

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try:
    from git import Repo, InvalidGitRepositoryError
except ImportError:
    print("Error: gitpython が必要です。pip install gitpython を実行してください。", file=sys.stderr)
    sys.exit(1)


FILE_CATEGORIES = {
    "DDL・マイグレーション": {
        "patterns": ["*.sql", "*/migrations/*", "*/migrate/*", "*/schema/*", "*/ddl/*"],
        "extensions": {".sql"},
        "path_keywords": ["migration", "migrate", "schema", "ddl", "flyway", "liquibase", "alembic"],
    },
    "データモデル・ORM": {
        "patterns": ["*/models/*", "*/models.py", "*/entities/*", "*/entity/*"],
        "extensions": set(),
        "path_keywords": ["models", "entities", "entity", "orm"],
    },
    "API定義": {
        "patterns": ["*/openapi.*", "*/swagger.*", "*/api/*"],
        "extensions": set(),
        "path_keywords": ["openapi", "swagger", "api-spec", "graphql"],
        "file_keywords": ["openapi", "swagger"],
    },
    "テストコード": {
        "patterns": ["*/test*/*", "*/spec/*", "*_test.*", "test_*"],
        "extensions": set(),
        "path_keywords": ["test", "tests", "spec", "specs", "__tests__"],
    },
    "CI/CD設定": {
        "patterns": [
            ".github/workflows/*", ".gitlab-ci.yml", "Jenkinsfile",
            ".circleci/*", "azure-pipelines.yml", ".travis.yml",
        ],
        "extensions": set(),
        "path_keywords": ["workflows", ".circleci"],
        "filenames": {
            "Jenkinsfile", ".gitlab-ci.yml", "azure-pipelines.yml",
            ".travis.yml", "bitbucket-pipelines.yml",
        },
    },
    "IaC・インフラ定義": {
        "patterns": ["*.tf", "*.tfvars", "*/cloudformation/*", "docker-compose*"],
        "extensions": {".tf", ".tfvars"},
        "path_keywords": ["terraform", "cloudformation", "infrastructure", "infra"],
        "filenames": {"docker-compose.yml", "docker-compose.yaml", "Dockerfile"},
    },
    "設計書・ドキュメント": {
        "patterns": ["docs/*", "doc/*", "*.md", "*.rst", "*.adoc"],
        "extensions": {".md", ".rst", ".adoc"},
        "path_keywords": ["docs", "doc", "documentation", "wiki", "adr"],
    },
    "設定ファイル": {
        "patterns": ["*.yml", "*.yaml", "*.toml", "*.ini", "*.cfg", "*.conf"],
        "extensions": {".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf", ".json"},
        "filenames": {".env.example", ".env.sample", ".env.template"},
    },
    "データパイプライン": {
        "patterns": ["*/dags/*", "*/pipelines/*", "*/etl/*", "*/elt/*"],
        "extensions": set(),
        "path_keywords": ["dags", "pipeline", "pipelines", "etl", "elt", "airflow", "dbt"],
    },
    "データ品質・テスト": {
        "patterns": ["*/great_expectations/*", "*/dbt/tests/*"],
        "extensions": set(),
        "path_keywords": ["great_expectations", "data_quality", "dbt"],
        "filenames": {"schema.yml"},
    },
    "セキュリティ関連": {
        "patterns": ["SECURITY.md", "*/auth/*", "*/security/*"],
        "extensions": set(),
        "path_keywords": ["auth", "security", "encryption"],
        "filenames": {"SECURITY.md", ".gitignore", ".gitleaksignore"},
    },
}

KEY_FILES = {
    "README.md": "プロジェクト概要ドキュメント",
    "CONTRIBUTING.md": "コントリビューションガイド（開発プロセス）",
    "CHANGELOG.md": "変更履歴",
    "SECURITY.md": "セキュリティポリシー",
    "LICENSE": "ライセンス",
    ".gitignore": "Git除外設定",
    ".env.example": "環境変数テンプレート",
    ".env.sample": "環境変数テンプレート",
    "docker-compose.yml": "Docker構成定義",
    "docker-compose.yaml": "Docker構成定義",
    "Makefile": "ビルド・タスク定義",
    "pyproject.toml": "Python プロジェクト設定",
    "package.json": "Node.js プロジェクト設定",
}


def classify_file(filepath: str) -> list[str]:
    """ファイルパスをDMBOK関連カテゴリに分類する。"""
    categories = []
    path = Path(filepath)
    ext = path.suffix.lower()
    name = path.name
    parts_lower = filepath.lower()

    for category, rules in FILE_CATEGORIES.items():
        if ext in rules.get("extensions", set()):
            categories.append(category)
            continue
        if name in rules.get("filenames", set()):
            categories.append(category)
            continue
        if any(kw in parts_lower for kw in rules.get("path_keywords", [])):
            categories.append(category)
            continue
        if any(kw in name.lower() for kw in rules.get("file_keywords", [])):
            categories.append(category)
            continue

    return categories


def scan_repo(repo_path: str) -> dict:
    """リポジトリを走査し、DMBOK観点の情報を収集する。"""
    try:
        repo = Repo(repo_path)
    except InvalidGitRepositoryError:
        print(f"Error: {repo_path} は有効なGitリポジトリではありません。", file=sys.stderr)
        sys.exit(1)

    result = {
        "repo_path": os.path.abspath(repo_path),
        "scan_date": datetime.now().isoformat(),
        "total_files": 0,
        "categorized_files": defaultdict(list),
        "key_files": {},
        "directory_structure": [],
        "languages": defaultdict(int),
        "recent_commits": [],
        "env_leaked": False,
        "has_secrets_in_code": False,
    }

    all_files = []
    for item in repo.tree().traverse():
        if item.type == "blob":
            all_files.append(item.path)

    result["total_files"] = len(all_files)

    top_dirs = set()
    for f in all_files:
        parts = Path(f).parts
        if len(parts) > 1:
            top_dirs.add(parts[0])
    result["directory_structure"] = sorted(top_dirs)

    lang_ext_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".java": "Java", ".go": "Go", ".rb": "Ruby", ".rs": "Rust",
        ".sql": "SQL", ".sh": "Shell", ".yml": "YAML", ".yaml": "YAML",
        ".json": "JSON", ".md": "Markdown", ".tf": "Terraform",
    }
    for f in all_files:
        ext = Path(f).suffix.lower()
        if ext in lang_ext_map:
            result["languages"][lang_ext_map[ext]] += 1

    for f in all_files:
        name = Path(f).name
        if name in KEY_FILES:
            result["key_files"][name] = KEY_FILES[name]

    for f in all_files:
        categories = classify_file(f)
        for cat in categories:
            result["categorized_files"][cat].append(f)

    if ".env" in [Path(f).name for f in all_files]:
        result["env_leaked"] = True

    for commit in repo.iter_commits(max_count=20):
        result["recent_commits"].append({
            "hash": commit.hexsha[:8],
            "message": commit.message.strip().split("\n")[0],
            "date": commit.committed_datetime.isoformat(),
            "author": str(commit.author),
        })

    return result


def generate_report(data: dict) -> str:
    """走査結果をMarkdownレポートに変換する。"""
    lines = []
    lines.append(f"# Git リポジトリ走査結果")
    lines.append("")
    lines.append(f"- **リポジトリ**: `{data['repo_path']}`")
    lines.append(f"- **走査日時**: {data['scan_date']}")
    lines.append(f"- **総ファイル数**: {data['total_files']}")
    lines.append("")

    lines.append("## ディレクトリ構造（トップレベル）")
    lines.append("")
    for d in data["directory_structure"]:
        lines.append(f"- `{d}/`")
    lines.append("")

    lines.append("## 言語・ファイル種別の分布")
    lines.append("")
    lines.append("| 言語/種別 | ファイル数 |")
    lines.append("|-----------|-----------|")
    for lang, count in sorted(data["languages"].items(), key=lambda x: -x[1]):
        lines.append(f"| {lang} | {count} |")
    lines.append("")

    lines.append("## 重要ファイルの存在チェック")
    lines.append("")
    for name, desc in KEY_FILES.items():
        exists = "あり" if name in data["key_files"] else "**なし**"
        lines.append(f"- `{name}`: {exists} ({desc})")
    lines.append("")

    if data["env_leaked"]:
        lines.append("> **WARNING**: `.env` ファイルがリポジトリにコミットされています。セキュリティリスクがあります。")
        lines.append("")

    lines.append("## DMBOK関連カテゴリ別ファイル一覧")
    lines.append("")
    for category in FILE_CATEGORIES:
        files = data["categorized_files"].get(category, [])
        lines.append(f"### {category}")
        lines.append("")
        if files:
            lines.append(f"**{len(files)}件** のファイルを検出:")
            lines.append("")
            display_files = files[:20]
            for f in display_files:
                lines.append(f"- `{f}`")
            if len(files) > 20:
                lines.append(f"- ... 他 {len(files) - 20} 件")
        else:
            lines.append("検出なし")
        lines.append("")

    lines.append("## 直近のコミット履歴（最大20件）")
    lines.append("")
    lines.append("| 日時 | ハッシュ | 作者 | メッセージ |")
    lines.append("|------|---------|------|-----------|")
    for commit in data["recent_commits"]:
        date = commit["date"][:10]
        lines.append(f"| {date} | `{commit['hash']}` | {commit['author']} | {commit['message'][:60]} |")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Git リポジトリを DMBOK 観点で走査し、構造化レポートを出力する"
    )
    parser.add_argument("repo_path", help="走査対象の Git リポジトリパス")
    parser.add_argument("--output", "-o", help="レポート出力先ファイルパス（省略時は標準出力）")
    args = parser.parse_args()

    if not os.path.isdir(args.repo_path):
        print(f"Error: {args.repo_path} はディレクトリではありません。", file=sys.stderr)
        sys.exit(1)

    data = scan_repo(args.repo_path)
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
