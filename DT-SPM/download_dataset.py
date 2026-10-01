#!/usr/bin/env python3
"""Download and verify the fixed R1 dataset, or install an existing local ZIP."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def safe_relative(name):
    rel = PurePosixPath(name)
    if (not name or '\\' in name or rel.is_absolute() or
            any(p in ('', '.', '..') for p in name.split('/')) or
            ':' in name or str(rel) != name):
        raise ValueError(f'Unsafe dataset path: {name!r}')
    return rel


def read_manifest(root, config):
    manifest = root / 'MANIFEST_data.sha256'
    if sha256(manifest) != config['manifest_sha256']:
        raise ValueError('MANIFEST_data.sha256 differs from the dataset configuration.')
    entries = {}
    for line in manifest.read_text(encoding='utf-8').splitlines():
        digest, name = line.split('  ', 1)
        safe_relative(name)
        if len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError(f'Invalid checksum for {name}')
        if name in entries:
            raise ValueError(f'Duplicate manifest entry: {name}')
        entries[name] = digest
    return entries


def destination(root, name):
    rel = safe_relative(name)
    path = root
    for component in rel.parts:
        path = path / component
        if path.is_symlink():
            raise ValueError(f'Dataset path crosses a symbolic link: {path}')
    return path


def check_files(root, entries):
    missing, changed = [], []
    for name, expected in entries.items():
        path = destination(root, name)
        if not path.exists():
            missing.append(name)
        elif not path.is_file() or sha256(path) != expected:
            changed.append(name)
    return missing, changed


def check_archive(path, config):
    if path.stat().st_size != config['bytes']:
        raise ValueError(f'Wrong archive size: {path.stat().st_size} bytes; '
                         f'expected {config["bytes"]}. Download the complete dataset ZIP.')
    actual = sha256(path)
    if actual != config['sha256']:
        raise ValueError(f'Archive checksum mismatch: {actual}. '
                         'Use the dataset version linked in README.md.')


def install_archive(archive, root, config, entries):
    """Validate the whole ZIP before installing missing files; retain identical files."""
    check_archive(archive, config)
    missing, changed = check_files(root, entries)
    if changed:
        raise ValueError('Existing dataset files differ; move them aside before retrying:\n' +
                         '\n'.join(changed))
    allowed = dict(entries)
    allowed['MANIFEST_data.sha256'] = config['manifest_sha256']
    prefix = config['archive_root'] + '/'
    with zipfile.ZipFile(archive) as source:
        members = {}
        for info in source.infolist():
            if not info.filename.startswith(prefix):
                raise ValueError(f'Unexpected archive root: {info.filename}')
            name = info.filename[len(prefix):]
            if info.is_dir():
                if name:
                    safe_relative(name.rstrip('/'))
                continue
            safe_relative(name)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError(f'Symbolic link in dataset ZIP: {name}')
            if name not in allowed or name in members:
                raise ValueError(f'Unexpected or duplicate archive member: {name}')
            destination(root, name)
            members[name] = info
        if set(members) != set(allowed):
            raise ValueError('The archive file list does not match MANIFEST_data.sha256.')
        # Verify all archive members before moving any file into place.
        with tempfile.TemporaryDirectory(prefix='.dataset-extract-', dir=root) as temp:
            staging = Path(temp)
            for name, info in members.items():
                digest = hashlib.sha256()
                target = staging / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open(info) as src, target.open('wb') as dst:
                    for block in iter(lambda: src.read(1024 * 1024), b''):
                        digest.update(block)
                        dst.write(block)
                if digest.hexdigest() != allowed[name]:
                    raise ValueError(f'Checksum mismatch inside ZIP: {name}')
            for name in missing:
                target = destination(root, name)
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    if not target.is_file() or sha256(target) != entries[name]:
                        raise ValueError(f'File changed during installation: {name}')
                else:
                    os.replace(staging / name, target)
    missing_after, changed_after = check_files(root, entries)
    if missing_after or changed_after:
        raise ValueError('Installed data failed verification; run verify_package.py --part data.')
    return len(missing)


def download_archive(root, config):
    try:
        import gdown
    except ImportError as exc:
        raise ValueError('Install the pinned environment first, or download the ZIP in '
                         'your browser and run: python download_dataset.py --archive PATH') from exc
    cache = root / 'downloads'
    cache.mkdir(exist_ok=True)
    archive = cache / config['filename']
    if archive.exists():
        check_archive(archive, config)
        return archive
    partial = archive.with_suffix('.zip.part')
    print(f'Downloading {config["filename"]} ({config["bytes"]:,} bytes)', flush=True)
    try:
        result = gdown.download(id=config['google_drive_file_id'], output=str(partial),
                                quiet=False, use_cookies=False, resume=False)
        if result is None or not partial.is_file():
            raise ValueError('Google Drive did not return the dataset ZIP.')
        check_archive(partial, config)
        os.replace(partial, archive)
    except Exception as exc:
        if partial.exists():
            partial.unlink()
        raise ValueError(f'Download failed: {exc}\nDownload in a browser from '
                         f'{config["url"]}\nThen run: python download_dataset.py '
                         '--archive /path/to/DT-SPM_R1_data_2026-09-30.zip') from exc
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', type=Path, help='Use a local ZIP instead of Google Drive.')
    parser.add_argument('--check', action='store_true', help='Verify installed data without downloading.')
    args = parser.parse_args()
    try:
        config = json.loads((ROOT / 'dataset_config.json').read_text())
        entries = read_manifest(ROOT, config)
        missing, changed = check_files(ROOT, entries)
        if changed:
            raise ValueError('Existing dataset files differ; move them aside before retrying:\n' +
                             '\n'.join(changed))
        if args.check:
            print(json.dumps({'files': len(entries), 'missing': missing,
                              'changed': changed, 'passed': not missing}, indent=2))
            return int(bool(missing))
        if not missing and args.archive is None:
            print(f'Dataset already installed: all {len(entries)} file checksums match.')
            return 0
        archive = args.archive.expanduser().resolve() if args.archive else download_archive(ROOT, config)
        count = install_archive(archive, ROOT, config, entries)
        print(f'Dataset verified: {len(entries)} files; {count} installed. Archive SHA-256 matches.')
        return 0
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
