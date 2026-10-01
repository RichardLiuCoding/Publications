#!/usr/bin/env python3
"""Refresh code checksums and build a code-only ZIP for Publications/DT-SPM.

The dataset manifest and dataset ZIP remain fixed. This command never uploads.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parent
CODE_DIRS = {'codes', 'revision_2026-09', 'environment', 'metadata', 'tests', 'DT-SPM_colab'}
IGNORE = {'__pycache__', '.ipynb_checkpoints', '.git', '.venv'}
DATA_METADATA = {'array_inventory.json', 'data_record_draft.json',
                 'figure_sources.csv', 'submission_tables.json'}
GENERATED = {'MANIFEST.sha256', 'MANIFEST_code.sha256', 'metadata/package_file_list.csv'}


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def code_files(root):
    result = []
    for item in root.iterdir():
        if item.is_symlink():
            continue
        if item.is_file() and (item.suffix in {'.py', '.md', '.txt', '.cff', '.json', '.ipynb'}
                               or item.name in {'.gitignore', 'MANIFEST_data.sha256'}):
            result.append(item)
        elif item.is_dir() and item.name in CODE_DIRS:
            for path in item.rglob('*'):
                rel = path.relative_to(root)
                if (path.is_file() and not path.is_symlink() and
                        not any(p in IGNORE for p in rel.parts) and
                        path.name != '.DS_Store' and path.suffix not in {'.pyc', '.nbc', '.nbi'} and
                        not (item.name == 'metadata' and path.name in DATA_METADATA)):
                    result.append(path)
    for path in result:
        if path.stat().st_size > 10 * 1024 * 1024:
            raise ValueError(f'Unexpected file over 10 MiB in code package: {path}')
    return sorted(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=ROOT / 'dist')
    parser.add_argument('--manifests-only', action='store_true')
    args = parser.parse_args()
    config = json.loads((ROOT / 'dataset_config.json').read_text())
    if sha(ROOT / 'MANIFEST_data.sha256') != config['manifest_sha256']:
        raise ValueError('Dataset manifest has changed. Retain the original archive manifest.')
    files = [p for p in code_files(ROOT) if p.relative_to(ROOT).as_posix() not in GENERATED]
    with (ROOT / 'metadata/package_file_list.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['path', 'archive', 'bytes', 'sha256'])
        writer.writeheader()
        writer.writerows({'path': p.relative_to(ROOT).as_posix(), 'archive': 'github-code',
                          'bytes': p.stat().st_size, 'sha256': sha(p)} for p in files)
    files.append(ROOT / 'metadata/package_file_list.csv')
    entries = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    data = {}
    for line in (ROOT / 'MANIFEST_data.sha256').read_text().splitlines():
        digest, name = line.split('  ', 1)
        data[name] = digest
        if name in entries and entries[name] != digest:
            raise ValueError(f'File shared with fixed dataset was changed: {name}')
    for name, records in [('MANIFEST_code.sha256', entries),
                          ('MANIFEST.sha256', {**entries, **data})]:
        (ROOT / name).write_text(''.join(f'{digest}  {path}\n'
                                       for path, digest in sorted(records.items())))
    if args.manifests_only:
        print(f'Checksums written: {len(entries)} code files, {len(data)} dataset files.')
        return
    args.out_dir.mkdir(parents=True, exist_ok=True)
    target = args.out_dir / 'DT-SPM_GitHub_R1_2026-09-30.zip'
    files += [ROOT / 'MANIFEST_code.sha256', ROOT / 'MANIFEST.sha256']
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(files):
            info = zipfile.ZipInfo('DT-SPM/' + path.relative_to(ROOT).as_posix(),
                                   date_time=(2026, 9, 30, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(target) as archive:
        failed = archive.testzip()
        if failed:
            raise ValueError(f'ZIP integrity failure: {failed}')
    record = {'file': target.name, 'bytes': target.stat().st_size, 'sha256': sha(target),
              'files': len(files), 'archive_root': 'DT-SPM',
              'dataset_url': config['url'], 'dataset_sha256': config['sha256']}
    (args.out_dir / 'SHA256SUMS.txt').write_text(f'{record["sha256"]}  {target.name}\n')
    (args.out_dir / 'archive_inventory.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
