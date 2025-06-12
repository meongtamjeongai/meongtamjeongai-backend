import os
import argparse
from datetime import datetime
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

# --- CONFIGURATION ---
# LLM 컨텍스트에 불필요한 폴더/파일 패턴을 기본적으로 제외합니다.
# 경로 구분자는 슬래시(/)를 사용합니다.
ALWAYS_EXCLUDED_PATTERNS = {
    # General
    '.git', '.idea', '.vscode', 'venv', 'node_modules',

    # Flutter & Dart
    '.dart_tool', '.pub_cache', 'build',

    # Android
    'android/.gradle', 'android/app/build', 'android/app/.cxx',
    'android/app/src/main/res',

    # iOS
    'ios/Pods', 'ios/.symlinks', 'ios/Flutter/App.framework', 'ios/Flutter/Flutter.podspec',

    # Mac
    'macos/Flutter/ephemeral', 'DerivedData',

    # Windows
    'windows/flutter/ephemeral',
    'windows/runner/Debug', 'windows/runner/Profile', 'windows/runner/Release',
}

ALWAYS_EXCLUDED_FILES = {
    '.DS_Store', '.metadata', 'local.properties',
    'pubspec.lock', 'package-lock.json', 'yarn.lock',
}
# --- END CONFIGURATION ---

# 스크립트 파일 자체를 제외 목록에 동적으로 추가
try:
    script_name = os.path.basename(__file__)
    ALWAYS_EXCLUDED_FILES.add(script_name)
except NameError:
    # 대화형 환경 등에서 __file__ 변수가 없을 경우 대비
    ALWAYS_EXCLUDED_FILES.add('mktree.py')

def get_gitignore_spec(path):
    """지정된 경로와 상위 모든 경로에서 .gitignore 파일을 찾아 PathSpec 객체를 생성합니다."""
    spec_patterns = []
    current_path = os.path.abspath(path)
    # 루트 디렉토리까지 올라가면서 .gitignore를 찾습니다.
    while True:
        gitignore_path = os.path.join(current_path, '.gitignore')
        if os.path.isfile(gitignore_path):
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                # 주석이나 빈 줄을 제외하고 패턴을 읽습니다.
                patterns = [line for line in f.read().splitlines() if line.strip() and not line.startswith('#')]
                spec_patterns.extend(patterns)

        parent_path = os.path.dirname(current_path)
        # 시스템 루트에 도달하면 중지합니다.
        if parent_path == current_path:
            break
        current_path = parent_path
    
    # GitWildMatchPattern을 사용하여 gitignore 문법을 올바르게 해석합니다.
    return PathSpec.from_lines(GitWildMatchPattern, spec_patterns)

def is_binary(file_path):
    """파일이 바이너리인지 텍스트인지 간단하게 확인합니다."""
    try:
        with open(file_path, 'tr', encoding='utf-8') as f:
            f.read(1024) # 첫 1KB만 읽어서 확인
        return False
    except (UnicodeDecodeError, IOError):
        return True

def generate_tree_and_files(root_dir, spec, prefix=""):
    """디렉토리 트리를 생성하고 포함될 파일 목록을 반환합니다."""
    tree_output = ""
    file_list = []

    try:
        items = sorted(os.listdir(root_dir))
    except OSError as e:
        print(f"Error accessing {root_dir}: {e}")
        return "", []

    filtered_items = []
    # 프로젝트 루트를 기준으로 상대 경로를 계산하기 위해 시작 경로를 저장합니다.
    start_path = os.path.abspath(args.root_dir)

    for name in items:
        path = os.path.join(root_dir, name)
        # .gitignore 매칭을 위해 프로젝트 루트 기준 상대 경로로 변환
        rel_path_from_start = os.path.relpath(path, start=start_path)
        # OS와 상관없이 슬래시(/)를 사용하도록 정규화
        rel_path_norm = rel_path_from_start.replace(os.path.sep, '/')

        # 1. .gitignore 패턴에 매칭되는지 확인
        if spec.match_file(rel_path_norm):
            continue
        # 2. 기본 제외 폴더 패턴에 매칭되는지 확인
        if any(rel_path_norm.startswith(p) for p in ALWAYS_EXCLUDED_PATTERNS):
            continue
        # 3. 기본 제외 파일 목록에 포함되는지 확인
        if os.path.isfile(path) and name in ALWAYS_EXCLUDED_FILES:
            continue
        
        filtered_items.append(name)

    for i, name in enumerate(filtered_items):
        path = os.path.join(root_dir, name)
        is_current_last = (i == len(filtered_items) - 1)
        
        if os.path.isdir(path):
            connector = "└── " if is_current_last else "├── "
            tree_output += f"{prefix}{connector}{name}/\n"
            new_prefix = prefix + ("    " if is_current_last else "│   ")
            subtree, subfiles = generate_tree_and_files(path, spec, new_prefix)
            tree_output += subtree
            file_list.extend(subfiles)
        else: # 파일인 경우
            connector = "└── " if is_current_last else "├── "
            if is_binary(path):
                tree_output += f"{prefix}{connector}{name} [binary]\n"
            else:
                tree_output += f"{prefix}{connector}{name}\n"
                file_list.append(path)
    
    return tree_output, file_list

def main():
    global args  # generate_tree_and_files에서 args를 참조할 수 있도록 전역 변수로 설정
    parser = argparse.ArgumentParser(description="Generate a directory tree and concatenate file contents, respecting .gitignore and optimized for various project types.")
    parser.add_argument("root_dir", nargs="?", default=".", help="The root directory to start from (default: current directory).")
    # 기본값을 None으로 설정하기 위해 default 인자 제거
    parser.add_argument("-o", "--output", help="The name of the output file. Defaults to '[root_dir_name]_output.txt'.")
    args = parser.parse_args()

    # --- [수정된 부분] ---
    # 출력 파일명이 지정되지 않은 경우, 루트 폴더명을 기반으로 자동 생성
    if args.output is None:
        # os.path.abspath를 통해 '.' 같은 상대 경로도 절대 경로로 변환 후 이름 추출
        root_name = os.path.basename(os.path.abspath(args.root_dir))
        # 폴더명이 비어있거나 현재 디렉토리를 의미하는 경우 'project'로 대체
        if not root_name or root_name == '.':
            root_name = 'project'
        args.output = f"{root_name}_output.txt"
    # --- [수정 끝] ---

    root_path = os.path.abspath(args.root_dir)
    if not os.path.isdir(root_path):
        print(f"Error: Directory not found at '{root_path}'")
        return

    print(f"🚀 Starting analysis from: {root_path}")
    gitignore_spec = get_gitignore_spec(root_path)

    print("🌳 Generating directory tree...")
    tree_structure, files_to_concat = generate_tree_and_files(root_path, gitignore_spec)

    print(f"📚 Concatenating {len(files_to_concat)} files...")
    concatenated_content_parts = []
    for f_path in files_to_concat:
        rel_path = os.path.relpath(f_path, root_path)
        concatenated_content_parts.append(f"--- START OF {rel_path.replace(os.path.sep, '/')} ---\n")
        try:
            with open(f_path, 'r', encoding='utf-8') as f:
                concatenated_content_parts.append(f.read())
        except Exception as e:
            concatenated_content_parts.append(f"Error reading file: {e}")
        concatenated_content_parts.append(f"\n--- END OF {rel_path.replace(os.path.sep, '/')} ---\n\n")

    concatenated_string = "".join(concatenated_content_parts)

    print("📊 Generating metadata summary...")
    file_count = len(files_to_concat)
    line_count = len(concatenated_string.splitlines())
    char_count = len(concatenated_string)
    approx_tokens = char_count // 4

    metadata_header = f"""# 📊 Project Analysis Summary

- **Root Directory**: {root_path}
- **Generated on**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **Total Files Included**: {file_count}
- **Total Lines of Content**: {line_count}
- **Total Characters**: {char_count}
- **Approximate Tokens**: {approx_tokens} (Note: A rough estimate, 1 token ≈ 4 chars)

---
"""

    print(f"💾 Writing output to {args.output}...")
    final_output = (
        f"{metadata_header}\n"
        f"# 🌳 Directory Tree\n\n"
        f"```\n{tree_structure}```\n\n"
        f"# 📚 Combined Code Files\n\n"
        f"{concatenated_string}"
    )

    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(final_output)

    print(f"\n✨ Done! Optimized project context saved to '{args.output}'.")

if __name__ == "__main__":
    main()