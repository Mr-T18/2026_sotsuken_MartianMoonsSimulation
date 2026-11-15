import argparse
import os
from pathlib import Path
import re

# 階層を問わず除外するディレクトリ名
DEFAULT_IGNORE_DIRS = {
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}

# プロジェクトルートからの相対パスで除外するディレクトリ
# ※ "result/ideal" は除外せず奥まで探索する
DEFAULT_IGNORE_REL_PATHS = {
    "result/parameter",
    "result/gas-drag",
    "result/bulge",
    "result/gas-drag_result_type",
}


def replace_midium(name: str, ignore_case: bool = False) -> str:
    if ignore_case:
        return re.sub(r"midium", "Medium", name, flags=re.IGNORECASE)
    return name.replace("Midium", "Medium")


def collect_rename_targets(
    root_path: Path,
    self_path: Path,
    ignore_dirs: set[str],
    ignore_rel_paths: set[str],
    ignore_case: bool = False,
) -> list[tuple[Path, Path]]:
    """
    ボトムアップ（深い階層から浅い階層）の順でリネーム対象 (old_path, new_path) を収集する。
    """
    targets: list[tuple[Path, Path]] = []

    for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
        current_dir = Path(dirpath)

        # 除外ディレクトリを探索対象から外す（topdown=True なので配下の走査もスキップされる）
        filtered_dirnames = []
        for d in dirnames:
            if d in ignore_dirs:
                continue
            rel_posix = (current_dir / d).relative_to(root_path).as_posix()
            if rel_posix in ignore_rel_paths:
                continue
            filtered_dirnames.append(d)
        dirnames[:] = filtered_dirnames

        # ファイルをチェック
        for fname in filenames:
            old_p = current_dir / fname
            if old_p.resolve() == self_path:
                continue
            new_fname = replace_midium(fname, ignore_case=ignore_case)
            if new_fname != fname:
                targets.append((old_p, current_dir / new_fname))

        # サブディレクトリをチェック
        for dname in dirnames:
            old_p = current_dir / dname
            new_dname = replace_midium(dname, ignore_case=ignore_case)
            if new_dname != dname:
                targets.append((old_p, current_dir / new_dname))

    # 深い階層から順に処理されるよう、パスの深さ（parts数）の降順でソート
    # 同じ深さの場合はファイル（not is_dir()）を先に処理する
    targets.sort(
        key=lambda pair: (len(pair[0].parts), not pair[0].is_dir()), reverse=True
    )
    return targets


def main():
    parser = argparse.ArgumentParser(
        description='ディレクトリ名・ファイル名の "Midium" を "Medium" に安全にリネームする'
    )
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="プロジェクトルートディレクトリ (デフォルト: カレントディレクトリ '.')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際にはリネームせず、対象の一覧と件数のみ確認する",
    )
    parser.add_argument(
        "--ignore-case",
        action="store_true",
        help='大文字小文字を区別せず "midium" / "MIDIUM" なども "Medium" に置換する',
    )
    args = parser.parse_args()

    root_path = Path(args.root).resolve()
    if not root_path.exists() or not root_path.is_dir():
        print(f"[Error] 有効なディレクトリが見つかりません: {root_path}")
        return

    self_path = Path(__file__).resolve()
    targets = collect_rename_targets(
        root_path=root_path,
        self_path=self_path,
        ignore_dirs=DEFAULT_IGNORE_DIRS,
        ignore_rel_paths=DEFAULT_IGNORE_REL_PATHS,
        ignore_case=args.ignore_case,
    )

    if not targets:
        print(
            f'[Info] リネーム対象（"Midium" を含む名前）は見つかりませんでした: {root_path}'
        )
        return

    print(f"Root: {root_path}")
    print(
        f"Found {len(targets)} target(s). (dry_run={args.dry_run}, ignore_case={args.ignore_case})"
    )
    print("-" * 60, flush=True)

    renamed_count = 0
    skipped_exists = 0
    error_count = 0

    for idx, (old_path, new_path) in enumerate(targets, start=1):
        rel_old = old_path.relative_to(root_path)
        rel_new = new_path.relative_to(root_path)
        kind = "DIR " if old_path.is_dir() else "FILE"

        # すでにリネーム先と同名の別ファイル・別ディレクトリが存在する場合は上書き・破損防止のためスキップ
        same_entry = False
        if new_path.exists():
            try:
                same_entry = old_path.samefile(new_path)
            except OSError:
                same_entry = False

        if new_path.exists() and not same_entry:
            skipped_exists += 1
            print(
                f"[Skip (Exists)] [{kind}] {rel_old} -> {rel_new.name} (既に同名が存在します)",
                flush=True,
            )
            continue

        if args.dry_run:
            renamed_count += 1
            print(
                f"[{idx:4d}/{len(targets):4d}] [DRY] [{kind}] {rel_old} -> {rel_new.name}",
                flush=True,
            )
            continue

        try:
            old_path.rename(new_path)
            renamed_count += 1
            print(
                f"[{idx:4d}/{len(targets):4d}] [OK ] [{kind}] {rel_old} -> {rel_new.name}",
                flush=True,
            )
        except OSError as e:
            error_count += 1
            print(
                f"[Error] [{kind}] {rel_old} -> {rel_new.name} ({e})",
                flush=True,
            )

    print("-" * 60)
    print(
        f"Done! Renamed: {renamed_count}, Skipped (exists): {skipped_exists}, Errors: {error_count}"
    )


if __name__ == "__main__":
    main()
