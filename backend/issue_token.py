#!/usr/bin/env python
"""Manage demo access tokens.

Usage:
    python issue_token.py issue --note "linkedin-jane" [--expires-days 7] [--uses 3]
    python issue_token.py list
"""
import argparse

from auth.tokens import init_db, issue_token, list_tokens


def main():
    parser = argparse.ArgumentParser(description="Manage PairMind demo access tokens")
    sub = parser.add_subparsers(dest="command", required=True)

    issue_p = sub.add_parser("issue", help="Issue a new token")
    issue_p.add_argument("--note", required=True, help="Who this token is for (e.g. 'linkedin-jane')")
    issue_p.add_argument("--expires-days", type=int, default=7, help="Days until expiry (default: 7)")
    issue_p.add_argument("--uses", type=int, default=3, help="Negotiations allowed before exhaustion (default: 3)")

    sub.add_parser("list", help="List all issued tokens and their status")

    args = parser.parse_args()
    init_db()

    if args.command == "issue":
        token = issue_token(args.note, expires_days=args.expires_days, uses=args.uses)
        print(f"Issued token for '{args.note}' (expires in {args.expires_days}d, {args.uses} negotiations):")
        print(token)

    elif args.command == "list":
        rows = list_tokens()
        if not rows:
            print("No tokens issued yet.")
            return
        for row in rows:
            print(f"{row['token']}  note={row['note']!r}  uses_remaining={row['uses_remaining']}  "
                  f"expires_at={row['expires_at']}  created_at={row['created_at']}")


if __name__ == "__main__":
    main()
