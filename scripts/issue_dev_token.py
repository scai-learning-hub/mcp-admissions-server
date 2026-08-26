"""Issue signed development JWTs for learner, counsellor, and auditor.

Usage:
  python scripts/issue_dev_token.py --role learner --subject learner-1
  python scripts/issue_dev_token.py --role counsellor --subject counsellor-1
  python scripts/issue_dev_token.py --role auditor --subject auditor-1
  python scripts/issue_dev_token.py --new-key   # generate a new signing key
"""

from __future__ import annotations

import argparse
import secrets

from packages.shared.tokens import Role, issue_token


SCOPES_BY_ROLE: dict[Role, list[str]] = {
    Role.LEARNER: ["catalog:read", "fees:quote", "lead:create:self"],
    Role.COUNSELLOR: ["catalog:read", "fees:quote", "lead:read:assigned", "lead:update:assigned"],
    Role.AUDITOR: [],
    Role.ADMIN: [],
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue a dev JWT")
    parser.add_argument("--role", choices=[r.value for r in Role], required=False)
    parser.add_argument("--subject", default="demo")
    parser.add_argument("--client-id", default=None)
    parser.add_argument("--new-key", action="store_true", help="Print a fresh random signing key and exit")
    parser.add_argument("--ttl", type=int, default=3600)
    args = parser.parse_args()

    if args.new_key:
        print(secrets.token_hex(32))
        return

    if not args.role:
        parser.error("--role is required unless --new-key is used")

    role = Role(args.role)
    client_id = args.client_id or f"{role.value}-client"
    token = issue_token(
        subject=args.subject,
        role=role,
        client_id=client_id,
        scopes=SCOPES_BY_ROLE[role],
        expires_in_seconds=args.ttl,
    )
    print(token)


if __name__ == "__main__":
    main()