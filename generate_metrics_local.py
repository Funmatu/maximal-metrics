import subprocess
import os
import shutil
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

# ==========================================
# ⚙️ 設定セクション
# ==========================================
WORKSPACE_DIR = "./github_workspace"
OUTPUT_SVG = "my_full_metrics.svg"

# 並列数の最適化
NETWORK_WORKERS = 32
ANALYSIS_WORKERS = os.cpu_count() or 4

# 言語定義とカラーコード
# Robotics系は視認性を高めるため、関連する色相（紫・青・橙）でグループ化
LANG_COLORS = {
    "Python": "#3572A5",
    "Rust": "#dea584",
    "JavaScript": "#f1e05a",
    "TypeScript": "#2b7489",
    "C++": "#f34b7d",
    "C++ Header": "#f34b7d",
    "C": "#555555",
    "C Header": "#555555",
    "Java": "#b07219",
    "Go": "#00ADD8",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Dart": "#00B4AB",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Zig": "#ec915c",
    "Lua": "#000080",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "Vue": "#2c3e50",
    "Svelte": "#ff3e00",
    "SCSS": "#c6538c",
    "GLSL": "#5686a5",
    "WGSL": "#3b8686",
    "HLSL": "#a5a510",
    "Cuda": "#3A4E3A",
    "ShaderLab": "#222c37",
    "WebAssembly": "#04133b",
    "Shell": "#89e051",
    "Dockerfile": "#384d54",
    "Makefile": "#427819",
    "CMake": "#064f8d",
    "YAML": "#cb171e",
    "TOML": "#9c4221",
    "JSON": "#292929",
    "HCL": "#844FBA",
    "Awk": "#c30e9b",
    "Markdown": "#083fa1",
    "TeX": "#3D6117",
    "XML": "#0060ac",
    "reStructuredText": "#141F1F",
    "Perl": "#0298c3",
    "Assembly": "#6E4C13",
    "Julia": "#a270ba",
    "R": "#198CE7",
    # --- 新規追加カラー ---
    "Robotics (Launch)": "#8e44ad",  # Deep Purple
    "Robotics (Xacro)": "#9b59b6",  # Purple
    "Robotics (URDF)": "#884ea0",  # Dark Purple
    "Robotics (ROS Msg)": "#2980b9",  # Strong Blue
    "Robotics (ROS Srv)": "#3498db",  # Blue
    "Robotics (ROS Action)": "#1abc9c",  # Teal
    "Robotics (SRDF)": "#16a085",  # Dark Teal
    "Robotics (Gazebo World)": "#d35400",  # Pumpkin
    "Robotics (Config)": "#e67e22",  # Carrot
    "Cython": "#f1c40f",  # Gold
    "Qt UI (XML)": "#41cd52",  # Qt Green
    "Qt Resource": "#2ecc71",  # Emerald
    "GraphQL": "#e10098",  # Brand Pink
    "Google Apps Script": "#4285f4",  # Google Blue
}
DEFAULT_COLOR = "#ededed"

# 集計対象ホワイトリスト
EXTENSIONS = {
    ".rs": "Rust",
    ".c": "C",
    ".h": "C Header",
    ".cpp": "C++",
    ".cxx": "C++",
    ".cc": "C++",
    ".hpp": "C++ Header",
    ".zig": "Zig",
    ".go": "Go",
    ".wat": "WebAssembly",
    ".s": "Assembly",
    ".asm": "Assembly",
    ".py": "Python",
    ".pyw": "Python",
    ".rb": "Ruby",
    ".lua": "Lua",
    ".pl": "Perl",
    ".pm": "Perl",
    ".awk": "Awk",
    ".jl": "Julia",
    ".r": "R",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "Sass",
    ".less": "Less",
    ".php": "PHP",
    ".java": "Java",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".dart": "Dart",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".glsl": "GLSL",
    ".vert": "GLSL",
    ".frag": "GLSL",
    ".geom": "GLSL",
    ".comp": "GLSL",
    ".wgsl": "WGSL",
    ".hlsl": "HLSL",
    ".shader": "ShaderLab",
    ".cu": "Cuda",
    ".cuh": "Cuda",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".xml": "XML",
    ".cmake": "CMake",
    ".dockerfile": "Dockerfile",
    ".tf": "HCL",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".tex": "TeX",
    ".rst": "reStructuredText",
    # --- Robotics / ROS / R&D Specific ---
    ".launch": "Robotics (Launch)",
    ".xacro": "Robotics (Xacro)",
    ".urdf": "Robotics (URDF)",
    ".msg": "Robotics (ROS Msg)",
    ".srv": "Robotics (ROS Srv)",
    ".action": "Robotics (ROS Action)",
    ".srdf": "Robotics (SRDF)",
    ".world": "Robotics (Gazebo World)",
    ".cfg": "Robotics (Config)",
    # --- Advanced Coding ---
    ".pyx": "Cython",
    ".ui": "Qt UI (XML)",
    ".qrc": "Qt Resource",
    # --- Web / Templates ---
    ".ejs": "JavaScript",
    ".graphql": "GraphQL",
    ".gs": "Google Apps Script",
    # --- PLC ---
    ".st": "Structured Text",
    ".plc": "Structured Text",
}

# 拡張子ベースの強力な除外リスト（ノイズ除去）
IGNORE_EXTENSIONS = {
    ".ply",
    ".pcd",
    ".obj",
    ".stl",
    ".dae",  # 3D Data
    ".csv",
    ".tsv",
    ".txt",
    ".log",
    ".back",
    ".bak",
    ".old",
    ".inc",  # Text Data / Backups
    ".svg",
    ".eps",
    ".png",
    ".jpg",
    ".jpeg",  # Images
    ".ipynb",
    ".rviz",
    ".uxf",
    ".drawio",  # Tool Generated Configs
    ".geojson",
    ".map",
    ".seqmap",  # Map Data
    ".lock",
    ".dcf",
    ".back2",  # Lock files & Misc
}

SPECIAL_FILENAMES = {
    "Dockerfile": "Dockerfile",
    "CMakeLists.txt": "CMake",
    "Makefile": "Makefile",
    "Gnumakefile": "Makefile",
    "Jenkinsfile": "Groovy",
    "Rakefile": "Ruby",
    "Gemfile": "Ruby",
    "Cargo.toml": "TOML",
    "package.json": "JSON",
    "requirements.txt": "Pip Requirements",
}

IGNORE_PATTERNS = [
    "node_modules/",
    "venv/",
    "target/",
    ".git/",
    "dist/",
    "build/",
    "vendor/",
    "__pycache__/",
    ".idea/",
    ".vscode/",
    "coverage/",
    "jquery",
    ".min.js",
    ".min.css",
]

# ==========================================
# 🛠️ 処理ロジック
# ==========================================


def run_cmd(cmd, cwd=None):
    try:
        res = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="replace",
        )
        return res.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def fetch_all_repos():
    print("🚀 Fetching repository list via GitHub CLI...")
    cmd = ["gh", "repo", "list", "--limit", "3000", "--json", "name,sshUrl"]
    res = run_cmd(cmd)
    if not res:
        print("❌ Failed. Ensure 'gh auth login' is done.")
        return []
    return json.loads(res)


def sync_repo_task(repo):
    """
    【重要】--mirror を使用して全Refを同期する
    """
    repo_name = repo["name"]
    repo_path = os.path.join(WORKSPACE_DIR, repo_name + ".git")

    if os.path.exists(repo_path):
        run_cmd(["git", "remote", "update"], cwd=repo_path)
    else:
        run_cmd(["git", "clone", "--mirror", repo["sshUrl"], repo_path])

    return repo_name, repo_path


def count_lines_all_refs(repo_path):
    """全ローカルブランチを対象に集計"""
    stats = defaultdict(int)
    other_breakdown = defaultdict(int)

    res = run_cmd(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads/"],
        cwd=repo_path,
    )
    if not res:
        return stats, other_breakdown

    branches = res.split("\n")

    for branch in branches:
        if not branch:
            continue

        # git grep execution (-I でバイナリ除外)
        grep_res = run_cmd(["git", "grep", "-I", "-c", "", branch], cwd=repo_path)
        if not grep_res:
            continue

        for line in grep_res.split("\n"):
            try:
                rest, count_str = line.rsplit(":", 1)
                prefix = f"{branch}:"
                if rest.startswith(prefix):
                    file_path = rest[len(prefix) :]
                else:
                    continue

                # ディレクトリ除外パターン
                if any(ign in file_path for ign in IGNORE_PATTERNS):
                    continue

                # クォート等のゴミ除去（超重要）
                file_path = file_path.strip().strip('"').strip("'")
                filename = os.path.basename(file_path)
                _, ext = os.path.splitext(filename)
                ext_lower = ext.lower()

                # 拡張子ブラックリスト（ノイズ除去）
                if ext_lower in IGNORE_EXTENSIONS:
                    continue

                lang = None
                lines = int(count_str)

                # 1. 特殊ファイル名
                if filename in SPECIAL_FILENAMES:
                    lang = SPECIAL_FILENAMES[filename]
                # 2. 定義済み拡張子（ホワイトリスト）
                elif ext_lower in EXTENSIONS:
                    lang = EXTENSIONS[ext_lower]
                # 3. 未定義（Other）
                else:
                    # ここで `stats` には加算しない（グラフに出さない）
                    # ただし、確認用に `other_breakdown` には記録する
                    key = ext_lower if ext_lower else "(no extension)"
                    other_breakdown[key] += lines
                    continue

                if lang:
                    stats[lang] += lines

            except ValueError:
                continue

    return stats, other_breakdown


def generate_svg(total_stats, filename):
    print(f"🎨 Generating SVG: {filename}...")
    sorted_stats = sorted(total_stats.items(), key=lambda x: x[1], reverse=True)
    total_lines = sum(total_stats.values()) or 1

    width, header_height, bar_height, gap, padding = 500, 50, 25, 12, 20
    height = header_height + (len(sorted_stats) * (bar_height + gap)) + padding

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<style>text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }}</style>',
        f'<rect width="{width}" height="{height}" fill="white" rx="6" />',
        f'<text x="{padding}" y="30" font-weight="bold" font-size="18" fill="#24292e">Total Volume (All Branches)</text>',
        f'<line x1="{padding}" y1="45" x2="{width - padding}" y2="45" stroke="#e1e4e8" stroke-width="1"/>',
    ]

    y = header_height + 15
    for lang, count in sorted_stats:
        pct = count / total_lines
        bar_w = (width - 160) * pct
        color = LANG_COLORS.get(lang, DEFAULT_COLOR)

        svg.append(
            f'<text x="{padding}" y="{y + 16}" font-size="12" fill="#24292e">{lang}</text>'
        )
        svg.append(
            f'<rect x="110" y="{y}" width="{width - 150}" height="12" fill="#f6f8fa" rx="3" />'
        )
        if bar_w > 0:
            svg.append(
                f'<rect x="110" y="{y}" width="{max(bar_w, 2)}" height="12" fill="{color}" rx="3" />'
            )
        svg.append(
            f'<text x="{width - padding}" y="{y + 11}" font-size="11" fill="#586069" text-anchor="end">{count:,} ({pct:.1%})</text>'
        )
        y += bar_height + gap

    svg.append("</svg>")
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(svg))


def main():
    if not shutil.which("gh"):
        return print("❌ Error: GitHub CLI not installed.")

    os.makedirs(WORKSPACE_DIR, exist_ok=True)
    repos = fetch_all_repos()
    print(f"📦 Found {len(repos)} repositories.")

    print(f"🔄 Mirroring repositories (Workers: {NETWORK_WORKERS})...")
    with ThreadPoolExecutor(max_workers=NETWORK_WORKERS) as executor:
        futures = [executor.submit(sync_repo_task, r) for r in repos]
        for _ in as_completed(futures):
            pass

    print(f"🔍 Analyzing ALL branches (Workers: {ANALYSIS_WORKERS})...")
    total_stats = defaultdict(int)
    total_other_breakdown = defaultdict(int)

    with ThreadPoolExecutor(max_workers=ANALYSIS_WORKERS) as executor:
        future_to_repo = {
            executor.submit(
                count_lines_all_refs, os.path.join(WORKSPACE_DIR, r["name"] + ".git")
            ): r["name"]
            for r in repos
        }

        done = 0
        for future in as_completed(future_to_repo):
            try:
                stats, other_details = future.result()
                for l, c in stats.items():
                    total_stats[l] += c

                for ext, c in other_details.items():
                    total_other_breakdown[ext] += c

            except Exception as e:
                print(f"⚠️ Error: {e}")
            done += 1
            print(f"   [{done}/{len(repos)}] Analyzed...", end="\r")

    print("\n\n=== 📊 FINAL TOTALS (ALL BRANCHES - Valid Code Only) ===")
    for lang, count in sorted(total_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"{lang:<20}: {count:>12,}")

    # 集計からは除外されているが、何が捨てられたかを確認するためのログ
    print("\n\n=== 🗑️ IGNORED FILES (Noise / Not in Whitelist) ===")
    print("These are excluded from the stats above.")
    sorted_others = sorted(
        total_other_breakdown.items(), key=lambda x: x[1], reverse=True
    )
    for ext, count in sorted_others[:50]:
        print(f"{ext:<20}: {count:>12,}")

    generate_svg(total_stats, OUTPUT_SVG)
    print(f"\n✅ Done! Saved to {os.path.abspath(OUTPUT_SVG)}")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
