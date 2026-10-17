import contextlib
import io
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from engagetrace.__main__ import main
from engagetrace.importer import ImportErrorDetail, REQUIRED, import_dataset


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / 'inputs'
        shutil.copytree(Path(__file__).parents[1] / 'examples/oulad-synthetic', self.inputs)
        self.db = self.root / 'store.sqlite3'

    def run_import(self, **kwargs):
        return import_dataset(self.inputs, self.db, **kwargs)

    def count(self, table):
        if not self.db.exists():
            return 0
        with sqlite3.connect(self.db) as con:
            return con.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]

    def test_valid_import_persistence_and_projection(self):
        summary = self.run_import()
        self.assertEqual(summary['status'], 'STAGED')
        self.assertEqual(summary['total_staged_rows'], 6)
        self.assertFalse(summary['already_imported'])
        for table, count in [('dataset_versions', 1), ('source_files', 3), ('source_records', 6)]:
            self.assertEqual(self.count(table), count)
        with sqlite3.connect(self.db) as con:
            row = con.execute("SELECT fields_json FROM source_records WHERE filename='studentVle.csv' LIMIT 1").fetchone()[0]
            self.assertEqual(set(json.loads(row)), set(REQUIRED['studentVle.csv']))
            self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(), [])
        self.assertTrue(all(len(f['checksum']) == 64 for f in summary['files']))

    def test_repeat_import(self):
        first, second = self.run_import(), self.run_import()
        self.assertEqual(first['dataset_version_id'], second['dataset_version_id'])
        self.assertEqual(first['imported_at'], second['imported_at'])
        self.assertTrue(second['already_imported'])
        self.assertEqual(self.count('source_records'), 6)

    def test_path_independent_identity_and_changed_content(self):
        first = self.run_import()
        moved = self.root / 'moved'
        shutil.copytree(self.inputs, moved)
        copy = import_dataset(moved, self.root / 'second.db')
        self.assertEqual(first['dataset_version_id'], copy['dataset_version_id'])
        path = self.inputs / 'studentVle.csv'
        path.write_text(path.read_text().replace(',0,10', ',0,11'))
        self.assertNotEqual(first['dataset_version_id'], self.run_import()['dataset_version_id'])
        self.assertEqual(self.count('dataset_versions'), 2)

    def test_missing_column_in_each_file(self):
        for name in REQUIRED:
            with self.subTest(name=name):
                path = self.inputs / name
                original = path.read_text()
                path.write_text(original.replace('code_module', 'wrong_column', 1))
                with self.assertRaisesRegex(ImportErrorDetail, 'missing required columns: code_module'):
                    self.run_import()
                self.assertFalse(self.db.exists())
                path.write_text(original)

    def test_missing_file(self):
        (self.inputs / 'studentRegistration.csv').unlink()
        with self.assertRaisesRegex(ImportErrorDetail, 'Missing required CSV file: studentRegistration.csv'):
            self.run_import()

    def test_late_failure_rolls_back(self):
        with (self.inputs / 'studentVle.csv').open('a') as f:
            f.write('too,few,fields\n')
        with self.assertRaisesRegex(ImportErrorDetail, 'malformed record'):
            self.run_import()
        for table in ['dataset_versions', 'source_files', 'source_records']:
            self.assertEqual(self.count(table), 0)

    def test_failure_preserves_existing_dataset(self):
        first = self.run_import()
        with (self.inputs / 'studentVle.csv').open('a') as f:
            f.write('too,few,fields\n')
        with self.assertRaises(ImportErrorDetail):
            self.run_import()
        self.assertEqual(self.count('dataset_versions'), 1)
        self.assertEqual(self.count('source_records'), 6)
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute('SELECT dataset_version_id FROM dataset_versions').fetchone()[0], first['dataset_version_id'])

    def test_existing_research_database_is_preserved(self):
        schema = Path(__file__).parent / 'fixtures/legacy_schema.sql'
        with sqlite3.connect(self.db) as con:
            con.executescript(schema.read_text())
            con.execute("INSERT INTO courses VALUES ('DEMO_2026J', 'DEMO', '2026J', 28)")
            con.execute("INSERT INTO students VALUES ('1001', 'DEMO_2026J', NULL)")
            con.execute("INSERT INTO weekly_activity VALUES ('1001', 'DEMO_2026J', 1, 10)")
        summary = self.run_import()
        self.assertEqual(summary['total_staged_rows'], 6)
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute('SELECT * FROM weekly_activity').fetchall(),
                             [('1001', 'DEMO_2026J', 1, 10)])
            self.assertEqual(con.execute('SELECT COUNT(*) FROM detection_runs').fetchone()[0], 0)
            self.assertEqual(con.execute('PRAGMA foreign_key_check').fetchall(), [])
        with (self.inputs / 'studentVle.csv').open('a') as stream:
            stream.write('too,few,fields\n')
        with self.assertRaises(ImportErrorDetail):
            self.run_import()
        self.assertEqual(self.count('dataset_versions'), 1)
        with sqlite3.connect(self.db) as con:
            self.assertEqual(con.execute('SELECT clicks FROM weekly_activity').fetchone()[0], 10)

    def test_bom(self):
        path = self.inputs / 'courses.csv'
        path.write_bytes(b'\xef\xbb\xbf' + path.read_bytes())
        self.assertEqual(self.run_import()['total_staged_rows'], 6)

    def test_empty_file_and_header_only(self):
        path = self.inputs / 'studentVle.csv'
        original = path.read_text()
        for content, message in [('', 'empty file'), (original.splitlines()[0] + '\n', 'no data records')]:
            with self.subTest(message=message):
                path.write_text(content)
                with self.assertRaisesRegex(ImportErrorDetail, message):
                    self.run_import()

    def test_duplicate_header_and_bad_encoding(self):
        path = self.inputs / 'courses.csv'
        path.write_text('code_module,code_module,module_presentation_length\nDEMO,2026J,28\n')
        with self.assertRaisesRegex(ImportErrorDetail, 'duplicate or blank'):
            self.run_import()
        path.write_bytes(b'\xff\xfe\xff')
        with self.assertRaisesRegex(ImportErrorDetail, 'Import failed'):
            self.run_import()

    def test_limits(self):
        with (self.inputs / 'studentVle.csv').open('ab') as f:
            f.write(b'x' * (1024 * 1024))
        with self.assertRaisesRegex(ImportErrorDetail, 'exceeds the configured'):
            self.run_import(max_file_mb=1)
        with self.assertRaisesRegex(ImportErrorDetail, 'positive integer'):
            self.run_import(max_file_mb=0)

    def test_cli(self):
        args = ['import', '--input-dir', str(self.inputs), '--database', str(self.db)]
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(args), 0)
        self.assertEqual(json.loads(output.getvalue())['total_staged_rows'], 6)
        (self.inputs / 'courses.csv').unlink()
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            self.assertEqual(main(args), 2)
        self.assertIn('Missing required CSV file', error.getvalue())
        self.assertNotIn('Traceback', error.getvalue())


if __name__ == '__main__':
    unittest.main()
