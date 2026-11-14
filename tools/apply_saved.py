import argparse
from pathlib import Path
import re
import shutil


def main():
    parser = argparse.ArgumentParser(
        description="vxxx_save.csv を vxxx.csv として上書き保存（リネーム）する"
    )
    parser.add_argument(
        "--root",
        type=str,
        default="result/parameter",
        help="探索ルートディレクトリ (デフォルト: result/parameter)",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="上書き前に元の vxxx.csv を vxxx_orig.csv としてバックアップする",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="実際には変更せず、対象ファイル数と処理内容のみ確認する",
    )
    args = parser.parse_args()

    root_path = Path(args.root)
    if not root_path.exists():
        print(f"[Error] ディレクトリが見つかりません: {root_path}")
        return

    save_files = sorted(
        p
        for p in root_path.glob("Obl-*_J2-*_Gas-*/out/v*_save.csv")
        if re.fullmatch(r"v\d{3}_save\.csv", p.name)
    )

    if not save_files:
        print(f"[Warning] 対象の vxxx_save.csv が見つかりませんでした: {root_path}")
        return

    print(
        f"Found {len(save_files)} save CSV files. "
        f"(backup={args.backup}, dry_run={args.dry_run})",
        flush=True,
    )

    replaced_count = 0
    skipped_empty = 0

    for idx, save_path in enumerate(save_files, start=1):
        if save_path.stat().st_size == 0:
            skipped_empty += 1
            print(f"[Skip (Empty)] {save_path.relative_to(root_path)}", flush=True)
            continue

        target_name = save_path.name.replace("_save.csv", ".csv")
        target_path = save_path.with_name(target_name)
        rel_save = save_path.relative_to(root_path)

        if not args.dry_run:
            if args.backup and target_path.exists():
                backup_name = target_path.name.replace(".csv", "_orig.csv")
                backup_path = target_path.with_name(backup_name)
                shutil.copy2(target_path, backup_path)

            # Windows環境でも既存ファイルを安全に上書きリネーム
            save_path.replace(target_path)

        replaced_count += 1
        print(
            f"[{idx:3d}/{len(save_files):3d}] {rel_save} -> {target_name}",
            flush=True,
        )

    print("-" * 60)
    print(f"Done! Replaced: {replaced_count}, Skipped (empty): {skipped_empty}")


if __name__ == "__main__":
    main()
