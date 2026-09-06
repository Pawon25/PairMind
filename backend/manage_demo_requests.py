#!/usr/bin/env python
"""Review demo access requests submitted from the landing page.

Usage:
    python manage_demo_requests.py list [--all]
    python manage_demo_requests.py review <id>
"""
import argparse

from demo_requests_store import init_db, list_requests, mark_reviewed


def main():
    parser = argparse.ArgumentParser(description="Review PairMind demo access requests")
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list", help="List pending requests (or all with --all)")
    list_p.add_argument("--all", action="store_true", help="Include already-reviewed requests")

    review_p = sub.add_parser("review", help="Mark a request as reviewed")
    review_p.add_argument("id", type=int, help="Request id (shown in `list`)")

    args = parser.parse_args()
    init_db()

    if args.command == "list":
        rows = list_requests(include_reviewed=args.all)
        if not rows:
            print("No pending requests." if not args.all else "No requests yet.")
            return
        for row in rows:
            status = "reviewed" if row["reviewed"] else "pending"
            print(f"[{row['id']}] {status}  {row['created_at']}")
            print(f"    {row['name']} <{row['email']}>")
            if row["message"]:
                print(f"    {row['message']}")
            print()

    elif args.command == "review":
        mark_reviewed(args.id)
        print(f"Marked request {args.id} as reviewed.")


if __name__ == "__main__":
    main()
