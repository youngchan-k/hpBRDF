import argparse
import sys
from pathlib import Path, PurePosixPath
from typing import Sequence

from huggingface_hub import HfApi, hf_hub_download, snapshot_download

DATASET_REPO_ID = "yunseongmoon/Hyperspectral-Polarimetric-BRDF"
DATASET_REPO_TYPE = "dataset"
MATERIAL_SUFFIX = ".hpbrdf"
DEFAULT_OUTPUT_DIR = Path("data")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=("List or download hyperspectral polarimetric BRDF materials from " "Hugging Face."))
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--list", action="store_true", help="List remote .hpbrdf materials without downloading.")
    selection.add_argument("--all", action="store_true", help="Download the full dataset (~182 GB) into the output directory.")
    selection.add_argument(
        "--material",
        action="extend",
        nargs="+",
        metavar="NAME",
        help=("Download one or more materials by filename or basename. " "Pass multiple names after one flag or repeat the flag."),
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory where downloaded files will be stored. Default: %(default)s")
    return parser


def fetch_available_materials() -> list[str]:
    repo_files = HfApi().list_repo_files(repo_id=DATASET_REPO_ID, repo_type=DATASET_REPO_TYPE)
    return sorted(
        (p for p in repo_files if PurePosixPath(p).parent == PurePosixPath(".") and PurePosixPath(p).suffix.casefold() == MATERIAL_SUFFIX),
        key=str.casefold,
    )


def normalize_material_names(requested: Sequence[str], available: Sequence[str]) -> list[str]:
    available_by_name = {name.casefold(): name for name in available}
    normalized: list[str] = []
    missing: list[str] = []

    for item in requested:
        candidate = item.strip()
        if not candidate:
            continue
        if not candidate.casefold().endswith(MATERIAL_SUFFIX):
            candidate = f"{candidate}{MATERIAL_SUFFIX}"

        resolved = available_by_name.get(candidate.casefold())
        if resolved is None:
            missing.append(item)
        elif resolved not in normalized:
            normalized.append(resolved)

    if missing:
        available_text = "\n".join(f"  - {name}" for name in available)
        raise ValueError(f"Unknown material name(s): {', '.join(missing)}\n" f"Available materials:\n{available_text}")

    return normalized


def download_selected_materials(materials: Sequence[str], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []

    for material in materials:
        print(f"Downloading {material}...")
        local_path = Path(
            hf_hub_download(
                repo_id=DATASET_REPO_ID,
                filename=material,
                repo_type=DATASET_REPO_TYPE,
                local_dir=output_dir,
            )
        )
        downloaded.append(local_path)
        print(f"Saved {material} to {local_path}")

    return downloaded


def download_full_dataset(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = Path(
        snapshot_download(
            repo_id=DATASET_REPO_ID,
            repo_type=DATASET_REPO_TYPE,
            local_dir=output_dir,
            allow_patterns=[f"*{MATERIAL_SUFFIX}"],
        )
    )
    print(f"Downloaded the full dataset to {snapshot_path}")
    return snapshot_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.list:
            materials = fetch_available_materials()
            print(f"Available materials in {DATASET_REPO_ID}:")
            print("\n".join(f"{index}. {material}" for index, material in enumerate(materials, start=1)))
            return 0

        if args.all:
            download_full_dataset(args.output_dir)
            return 0

        available = fetch_available_materials()
        selected = normalize_material_names(args.material or [], available)
        download_selected_materials(selected, args.output_dir)
        return 0
    except ValueError as exc:
        parser.error(str(exc))
    except OSError as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    main()
