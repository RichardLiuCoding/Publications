"""Exercise checksum, extraction, conflict and repeat-install behavior with small ZIPs."""
from pathlib import Path
import hashlib
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from download_dataset import install_archive, read_manifest, sha256
from build_archives import code_files


class DatasetInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'code'
        self.root.mkdir()
        self.contents = {'data/raw.bin': b'measured-data', 'splits/test.csv': b'id,fold\n1,0\n'}
        self.manifest = ''.join(f'{hashlib.sha256(data).hexdigest()}  {name}\n'
                                for name, data in sorted(self.contents.items())).encode()
        (self.root / 'MANIFEST_data.sha256').write_bytes(self.manifest)
        self.archive = self.base / 'dataset.zip'
        self.config = {'archive_root': 'DT-SPM_R1',
                       'manifest_sha256': hashlib.sha256(self.manifest).hexdigest()}
        self.make_zip()
        self.entries = read_manifest(self.root, self.config)

    def make_zip(self, extra=None, replacements=None):
        contents = dict(self.contents)
        contents.update(replacements or {})
        with zipfile.ZipFile(self.archive, 'w') as archive:
            for name, data in contents.items():
                archive.writestr('DT-SPM_R1/' + name, data)
            archive.writestr('DT-SPM_R1/MANIFEST_data.sha256', self.manifest)
            if extra:
                archive.writestr(*extra)
        self.config.update(bytes=self.archive.stat().st_size, sha256=sha256(self.archive))

    def install(self):
        return install_archive(self.archive, self.root, self.config, self.entries)

    def test_install_and_repeat(self):
        (self.root / 'README.md').write_text('code documentation')
        self.assertEqual(self.install(), 2)
        self.assertEqual(self.install(), 0)
        self.assertEqual((self.root / 'data/raw.bin').read_bytes(), b'measured-data')
        self.assertEqual((self.root / 'README.md').read_text(), 'code documentation')

    def test_incomplete_archive_is_rejected(self):
        self.config['bytes'] += 1
        with self.assertRaisesRegex(ValueError, 'Wrong archive size'):
            self.install()
        self.assertFalse((self.root / 'data').exists())

    def test_wrong_archive_hash_writes_nothing(self):
        self.config['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            self.install()
        self.assertFalse((self.root / 'data').exists())

    def test_changed_local_data_is_preserved(self):
        (self.root / 'data').mkdir()
        (self.root / 'data/raw.bin').write_bytes(b'user-edit')
        with self.assertRaisesRegex(ValueError, 'Existing dataset files differ'):
            self.install()
        self.assertEqual((self.root / 'data/raw.bin').read_bytes(), b'user-edit')
        self.assertFalse((self.root / 'splits').exists())

    def test_zip_traversal_is_rejected_before_any_install(self):
        self.make_zip(extra=('DT-SPM_R1/../../outside.txt', b'bad'))
        with self.assertRaisesRegex(ValueError, 'Unsafe dataset path'):
            self.install()
        self.assertFalse((self.root / 'data').exists())
        self.assertFalse((self.base / 'outside.txt').exists())

    def test_bad_member_hash_is_rejected_before_any_install(self):
        self.make_zip(replacements={'splits/test.csv': b'changed'})
        with self.assertRaisesRegex(ValueError, 'Checksum mismatch inside ZIP'):
            self.install()
        self.assertFalse((self.root / 'data').exists())

    def test_unexpected_member_is_rejected(self):
        self.make_zip(extra=('DT-SPM_R1/run_reproduction.py', b'bad'))
        with self.assertRaisesRegex(ValueError, 'Unexpected or duplicate'):
            self.install()

    def test_symlink_destination_is_rejected(self):
        outside = self.base / 'outside'
        outside.mkdir()
        (self.root / 'data').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symbolic link'):
            self.install()
        self.assertFalse((outside / 'raw.bin').exists())

    def test_archive_builder_excludes_installed_data(self):
        self.install()
        (self.root / 'metadata').mkdir()
        (self.root / 'metadata/data_record_draft.json').write_text('{}')
        (self.root / 'dataset_config.json').write_text('{}')
        (self.root / 'downloads').mkdir()
        (self.root / 'downloads/data.zip').write_bytes(b'zip')
        (self.root / 'DT-SPM_colab').mkdir()
        (self.root / 'DT-SPM_colab/source.ipynb').write_text('{}')
        files = {p.relative_to(self.root).as_posix() for p in code_files(self.root)}
        self.assertEqual(files, {'MANIFEST_data.sha256', 'dataset_config.json',
                                 'DT-SPM_colab/source.ipynb'})


if __name__ == '__main__':
    unittest.main()
