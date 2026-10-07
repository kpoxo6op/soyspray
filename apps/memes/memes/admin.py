"""Local operator commands. Invite tokens are printed only once."""

import argparse
import os

from .store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=os.environ.get("MEMES_DATA", "/data"))
    sub = parser.add_subparsers(dest="command", required=True)
    invite = sub.add_parser("invite")
    invite.add_argument("--name", required=True)
    invite.add_argument("--origin", default="https://memes.soyspray.vip")
    for command in ("exclude", "delete"):
        sub.add_parser(command).add_argument("--user-id", required=True, type=int)
    args = parser.parse_args()
    store = Store(args.data)
    if args.command == "invite":
        print(args.origin.rstrip("/") + "/t/" + store.invite(args.name))
    else:
        with store.transaction() as db:
            if args.command == "exclude":
                db.execute("UPDATE tester SET excluded=1 WHERE user_id=?", (args.user_id,))
            else:
                db.execute("DELETE FROM tester WHERE user_id=?", (args.user_id,))
            if db.execute("SELECT changes()").fetchone()[0] != 1:
                raise SystemExit("Unknown tester")
        if args.command == "delete":
            with store.connect() as db:
                db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        print(args.command + " completed")


if __name__ == "__main__":
    main()
