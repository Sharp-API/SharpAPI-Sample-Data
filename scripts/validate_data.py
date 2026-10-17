#!/usr/bin/env python3
"""Validate the public CSV schema using only the Python standard library."""
import csv
from datetime import datetime
import math
from pathlib import Path
import re
import sys

HEADER = 'id sportsbook event_id sport league home_team away_team market_type selection selection_type odds_american odds_decimal odds_probability line event_start_time is_live timestamp'.split()
NULLABLE = {'home_team', 'away_team', 'line'}
ISO_TIMESTAMP = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})')


def validate_row(row):
    for field, value in row.items():
        if not value.strip() and field not in NULLABLE:
            raise ValueError(f'{field}: required value is empty')
    american = row['odds_american']
    if not re.fullmatch(r'[+-]?\d+', american) or abs(int(american)) < 100:
        raise ValueError('odds_american: expected integer <= -100 or >= 100')
    for field in ('odds_decimal', 'odds_probability', 'line'):
        if field == 'line' and not row[field].strip():
            continue
        try:
            number = float(row[field])
        except ValueError:
            raise ValueError(f'{field}: expected a number') from None
        if not math.isfinite(number):
            raise ValueError(f'{field}: expected a finite number')
        if field == 'odds_decimal' and number <= 1:
            raise ValueError(f'{field}: must be greater than 1')
        if field == 'odds_probability' and not 0 < number < 1:
            raise ValueError(f'{field}: must be between 0 and 1 (exclusive)')
    if row['is_live'] not in {'True', 'False'}:
        raise ValueError('is_live: expected True or False')
    for field in ('event_start_time', 'timestamp'):
        value = row[field]
        try:
            if not ISO_TIMESTAMP.fullmatch(value):
                raise ValueError()
            datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError(f'{field}: expected valid ISO 8601 timestamp with timezone') from None


def validate_file(path):
    with path.open(encoding='utf-8', newline='') as stream:
        reader = csv.reader(stream, strict=True)
        count = 0
        try:
            if next(reader, None) != HEADER:
                raise ValueError('header: must match the documented CSV columns in order')
            for values in reader:
                if len(values) != len(HEADER):
                    raise ValueError(f'columns: expected {len(HEADER)}, got {len(values)}')
                validate_row(dict(zip(HEADER, values)))
                count += 1
            if not count:
                raise ValueError('no data rows')
        except (ValueError, csv.Error) as error:
            raise ValueError(f'{path}:{reader.line_num}: {error}') from None
    return count


def main():
    paths = [Path(arg) for arg in sys.argv[1:]] if sys.argv[1:] else sorted(Path('data').glob('*.csv'))
    if not paths:
        print('No data/*.csv files found', file=sys.stderr)
        return 1
    total = 0
    for path in paths:
        try:
            count = validate_file(path)
        except (ValueError, OSError, UnicodeError) as error:
            print(error, file=sys.stderr)
            return 1
        total += count
        print(f'{path}: {count} rows valid')
    print(f'Validated {total} rows across {len(paths)} files')
    return 0


if __name__ == '__main__':
    sys.exit(main())
