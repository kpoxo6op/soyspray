"""Restore one node snapshot locally and verify its real content manifest."""

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', required=True)
    args = parser.parse_args()
    os.umask(0o077)
    root = Path(__file__).resolve().parents[2]
    recovery = Path.home() / '.config/soyspray/recovery'
    state = Path.home() / '.local/state/soyspray/restores/node-backup'
    output = state / datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    output.mkdir(parents=True, mode=0o700)
    report = {'status': 'failed', 'snapshot': args.snapshot, 'cleanup': 'pending'}
    try:
        values = subprocess.check_output([str(root / 'soyspray-venv/bin/ansible-vault'), 'view', '--vault-password-file', str(recovery / 'vault-password'), str(recovery / 'node-backup.vault.yml')], stderr=subprocess.PIPE)
        env = {**os.environ, **yaml.safe_load(values)['node_backup_credentials']}
        with tempfile.TemporaryDirectory(dir=output) as temporary:
            destination = Path(temporary)
            for command in (['check'], ['restore', args.snapshot, '--target', str(destination)]):
                subprocess.run([str(Path.home() / '.local/bin/restic'), *command], env=env, check=True, capture_output=True, timeout=3600)
            manifests = list(destination.rglob('content-manifest.json'))
            if len(manifests) != 1:
                raise ValueError('Expected one restored content manifest')
            manifest = json.loads(manifests[0].read_text())
            base = manifests[0].parent
            count = 0
            total = 0
            for item in manifest['files']:
                path = base / item['path']
                if not path.parent.resolve().is_relative_to(base.resolve()):
                    raise ValueError('Restored path escapes the snapshot')
                if item['type'] == 'symlink':
                    if not path.is_symlink() or os.readlink(path) != item['target']:
                        raise ValueError('Restored link differs')
                else:
                    with path.open('rb') as stream:
                        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                    if path.stat().st_size != item['bytes'] or digest != item['sha256']:
                        raise ValueError('Restored file differs from the backup manifest')
                    count += 1
                    total += item['bytes']
            db = sqlite3.connect(base / 'jellyfin/data/jellyfin.db')
            try:
                if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                    raise ValueError('Restored Jellyfin SQLite failed integrity check')
                tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
                report['sqlite_rows'] = {t: db.execute('SELECT count(*) FROM "' + t.replace('"', '""') + '"').fetchone()[0] for t in tables}
            finally:
                db.close()
            report.update(status='passed', verified_files=count, verified_bytes=total, recovery_point=manifest['started_at'])
    except Exception as error:
        report['cause'] = type(error).__name__ + ': ' + str(error)
    finally:
        report['cleanup'] = 'completed' if not list(output.iterdir()) else 'inspect remaining workspace'
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({'report': str(output / 'report.json'), **report}))
    return 0 if report['status'] == 'passed' and report['cleanup'] == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(run())
