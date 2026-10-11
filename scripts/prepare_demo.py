"""Remove only identifiable test fixtures, with a backup; dry report by default.

This deliberately preserves automatic flag transitions, account preferences, private
check-ins and other data whose test provenance cannot be established from its value.
It does not import the application store, seed data, or contact an external service.
"""
import argparse
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / 'backend' / '.local' / 'guardian.sqlite3'
ANNOUNCEMENT_FIXTURES = frozenset(('Indoor PE browser verification', 'School review test'))
OBSERVATION_FIXTURE = re.compile(r'<script>fixture [0-9]{13}</script>\Z')
DEPENDENCIES = ('deliveries', 'plan_reviews', 'acknowledgments', 'schedule_changes')
TABLES = ('events', 'reports', 'history', *DEPENDENCIES)


def _object(value):
    try:
        result = json.loads(value)
        return result if isinstance(result, dict) else {}
    except (ValueError, TypeError):
        return {}


def _candidates(db):
    found = {table: [] for table in TABLES}
    event_ids = set()
    for row in db.execute('SELECT rowid, id, kind, body FROM events'):
        body = _object(row['body'])
        reasons = body.get('reasons')
        if (row['kind'] == 'admin-announcement' and body.get('mode') == 'demo'
                and isinstance(reasons, list) and len(reasons) == 1
                and isinstance(reasons[0], str) and reasons[0] in ANNOUNCEMENT_FIXTURES):
            found['events'].append(row['rowid'])
            event_ids.add(row['id'])
    for row in db.execute('SELECT rowid, note FROM reports'):
        if isinstance(row['note'], str) and OBSERVATION_FIXTURE.fullmatch(row['note']):
            found['reports'].append(row['rowid'])
    for table in DEPENDENCIES:
        for row in db.execute(f'SELECT rowid, event_id FROM {table}'):
            if row['event_id'] in event_ids:
                found[table].append(row['rowid'])
    for row in db.execute('SELECT rowid, body FROM history'):
        event_id = _object(row['body']).get('eventId')
        if isinstance(event_id, str) and event_id in event_ids:
            found['history'].append(row['rowid'])
    return found


def _delete_candidates(db, found):
    # Delete dependent records first even though the current schema has no event FK.
    for table in (*DEPENDENCIES, 'history', 'reports', 'events'):
        db.executemany(f'DELETE FROM {table} WHERE rowid=?', ((row_id,) for row_id in found[table]))


def prepare_demo(database=DEFAULT_DATABASE, *, apply=False, backup_directory=None):
    database = Path(database).resolve(strict=True)
    uri = database.as_uri() + ('?mode=rw' if apply else '?mode=ro')
    with closing(sqlite3.connect(uri, uri=True, timeout=10)) as db:
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        present = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not set(TABLES).issubset(present):
            raise ValueError('This is not a complete Air Guardian database; no changes made.')
        # Reserve the writer lock before collecting candidates. A separate read
        # connection can safely snapshot the committed database while it is held.
        db.execute('BEGIN IMMEDIATE' if apply else 'BEGIN')
        found = _candidates(db)
        result = {
            'mode': 'apply' if apply else 'dry-run',
            'database': str(database),
            'recordsBefore': {table: db.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in TABLES},
            'matched': {table: len(found[table]) for table in TABLES},
            'removed': {table: 0 for table in TABLES},
            'backup': None,
        }
        if apply and any(found.values()):
            backups = Path(backup_directory) if backup_directory else database.parent / 'backups'
            backups.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            backup = backups / f'{database.stem}-before-fixture-cleanup-{stamp}-{uuid4().hex[:8]}.sqlite3'
            with closing(sqlite3.connect(database.as_uri() + '?mode=ro', uri=True)) as source:
                with closing(sqlite3.connect(backup)) as destination:
                    source.backup(destination)
                    if destination.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise RuntimeError('Backup integrity check failed; no records removed.')
            result['backup'] = str(backup.resolve())
            _delete_candidates(db, found)
            result['removed'] = dict(result['matched'])
        db.commit()
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, default=DEFAULT_DATABASE)
    parser.add_argument('--apply', action='store_true', help='Back up and delete exact known fixture records.')
    args = parser.parse_args()
    try:
        result = prepare_demo(args.database, apply=args.apply)
    except (OSError, ValueError, sqlite3.Error, RuntimeError) as error:
        parser.exit(1, f'Demo preparation stopped: {error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
