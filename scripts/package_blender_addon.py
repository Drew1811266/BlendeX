#!/usr/bin/env python3
import argparse
import pathlib
import sys
import zipfile
from typing import Iterable, List, Optional


ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codex_plugin.blendex_mcp.version import VERSION


EXCLUDED_PARTS = {"__pycache__", ".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def _is_packaged_file(path: pathlib.Path) -> bool:
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return False
    if path.suffix in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def _iter_files(source: pathlib.Path) -> Iterable[pathlib.Path]:
    return (path for path in sorted(source.rglob("*")) if _is_packaged_file(path))


def _write_tree(archive: zipfile.ZipFile, source: pathlib.Path, archive_root: str) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Package source does not exist: {source}")
    for path in _iter_files(source):
        archive.write(path, pathlib.Path(archive_root) / path.relative_to(source))


def build_package(output_dir: Optional[pathlib.Path] = None) -> pathlib.Path:
    if output_dir is None:
        output_dir = ROOT / "dist"
    output_dir.mkdir(parents=True, exist_ok=True)
    package_path = output_dir / f"blendex-{VERSION}-blender-addon.zip"
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        _write_tree(archive, ROOT / "blender_addon" / "blendex", "blendex")
        _write_tree(archive, ROOT / "src" / "blendex_protocol", "blendex_protocol")
    return package_path


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build the BlendeX local beta Blender add-on zip.")
    parser.add_argument(
        "--output-dir",
        type=pathlib.Path,
        default=ROOT / "dist",
        help="Directory where the zip package should be written.",
    )
    args = parser.parse_args(argv)
    package_path = build_package(args.output_dir)
    print(package_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
