"""Exercise the validator's CLI with small, independent CSV fixtures."""
import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'validate_data.py'
HEADER = 'id sportsbook event_id sport league home_team away_team market_type selection selection_type odds_american odds_decimal odds_probability line event_start_time is_live timestamp'.split()
ROW = ['price-1', 'book', 'event-1', 'soccer', 'league', '', '', 'total', 'Team', 'over', '-110', '1.9091', '0.5238', '', '2026-07-06T03:19:49Z', 'False', '2026-07-13T01:45:33.481436094Z']


class ValidatorTests(unittest.TestCase):
    def run_fixture(self, rows, header=HEADER):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.csv'
            with path.open('w', newline='') as stream:
                csv.writer(stream).writerows([header, *rows])
            return subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)

    def test_allows_nullable_teams_line_and_repeated_ids(self):
        row = ROW.copy()
        row[HEADER.index('line')] = '-1.5'
        row[HEADER.index('is_live')] = 'True'
        result = self.run_fixture([ROW, row])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('2 rows', result.stdout)

    def test_allows_iso_minute_precision_and_timezone_offsets(self):
        row = ROW.copy()
        row[HEADER.index('event_start_time')] = '2026-07-13T01:04Z'
        row[HEADER.index('timestamp')] = '2026-07-13T01:04:12+00:00'
        result = self.run_fixture([row])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_missing_or_renamed_headers(self):
        for header in (HEADER[:-1], ['wrong', *HEADER[1:]], [*HEADER[:-1], 'id']):
            with self.subTest(header=header):
                result = self.run_fixture([ROW], header)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('header', result.stderr)

    def test_rejects_short_and_long_rows(self):
        for row in (ROW[:-1], [*ROW, 'extra']):
            result = self.run_fixture([row])
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('columns', result.stderr)

    def test_rejects_empty_required_fields(self):
        for field in set(HEADER) - {'home_team', 'away_team', 'line'}:
            with self.subTest(field=field):
                row = ROW.copy()
                row[HEADER.index(field)] = ' '
                result = self.run_fixture([row])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(field, result.stderr)

    def test_rejects_invalid_typed_values(self):
        cases = {
            'odds_american': ['0', '99', '-99', '110.5', 'NaN', 'inf'],
            'odds_decimal': ['1', '-2', 'NaN', 'inf', 'abc'],
            'odds_probability': ['0', '1', '-0.1', '1.1', 'NaN', 'inf'],
            'line': ['NaN', '-inf', 'oops'],
            'event_start_time': ['2026-02-30T00:00:00Z', 'yesterday', '2026-07-06'],
            'timestamp': ['2026-13-01T00:00:00Z', '2026-07-13T99:00:00Z'],
            'is_live': ['yes', '0', 'unknown'],
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    row = ROW.copy()
                    row[HEADER.index(field)] = value
                    result = self.run_fixture([row])
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(field, result.stderr)
                    self.assertIn('fixture.csv:2:', result.stderr)

    def test_rejects_header_only_file(self):
        result = self.run_fixture([])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no data rows', result.stderr)

    def test_rejects_unterminated_csv_quotes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'broken.csv'
            path.write_text(','.join(HEADER) + '\n"unterminated')
            result = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('broken.csv', result.stderr)


if __name__ == '__main__':
    unittest.main()
