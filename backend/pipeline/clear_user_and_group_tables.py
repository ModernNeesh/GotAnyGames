"""Clear user and group related tables from the PostgreSQL database.

Deletes rows from the following tables (in a safe order to respect FKs):
- group_membership
- user_ratings
- user_prefs
- groups
- users

Usage:
  python clear_user_and_group_tables.py [--dry-run] [--yes]

Options:
  --dry-run   Print row counts that would be deleted but don't perform deletions.
  --yes       Skip confirmation prompt.

The script reads the database URL from the `POSTGRES_URL` environment variable
and uses the project's `init_db()` helper to create the engine.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import sqlalchemy as sa

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
	sys.path.insert(0, str(BACKEND_DIR))

from app.models.db import init_db


def get_counts(conn, tables):
	counts = {}
	for t in tables:
		try:
			res = conn.execute(sa.text(f"SELECT COUNT(*) AS c FROM {t}"))
			counts[t] = int(res.scalar_one())
		except Exception:
			counts[t] = None
	return counts


def main(dry_run: bool, assume_yes: bool):
	engine, Base, Session = init_db()
	inspector = sa.inspect(engine)

	tables = [
		'group_membership',
		'user_ratings',
		'user_prefs',
		'groups',
		'users',
	]

	existing = [t for t in tables if inspector.has_table(t)]
	if not existing:
		print("No user/group tables found to clear.")
		return

	with engine.begin() as conn:
		before = get_counts(conn, existing)

	print("Row counts before:")
	for t in existing:
		print(f" - {t}: {before[t] if before[t] is not None else 'N/A'}")

	if dry_run:
		print("\nDry run: no changes made.")
		return

	if not assume_yes:
		reply = input('\nAre you sure you want to DELETE all rows from the tables above? (yes/no): ').strip().lower()
		if reply not in ('y', 'yes'):
			print('Aborting. No changes made.')
			return

	# Perform deletions in order that respects foreign keys
	with engine.begin() as conn:
		for t in existing:
			try:
				conn.execute(sa.text(f"DELETE FROM {t}"))
			except Exception as e:
				print(f"Failed to clear {t}: {e}")

		after = get_counts(conn, existing)

	print('\nRow counts after:')
	for t in existing:
		print(f" - {t}: {after[t] if after[t] is not None else 'N/A'}")


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Clear only user and group related tables.')
	parser.add_argument('--dry-run', action='store_true', help='Show counts without deleting')
	parser.add_argument('--yes', action='store_true', help='Skip confirmation prompt', default=True)
	args = parser.parse_args()

	main(dry_run=args.dry_run, assume_yes=args.yes)

