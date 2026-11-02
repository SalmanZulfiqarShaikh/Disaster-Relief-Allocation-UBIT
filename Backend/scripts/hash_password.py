
from __future__ import annotations

import getpass
import secrets
import sys


def main(argv: list[str] | None = None) -> int:
    from core.auth import hash_password

    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    print("This prints two lines for your .env. The password is not stored.\n")

    password = getpass.getpass("Password: ")
    if not password:
        print("Nothing entered. Stopping.", file=sys.stderr)
        return 1

    if password != getpass.getpass("Again: "):
        print("The two did not match. Stopping.", file=sys.stderr)
        return 1

    if len(password) < 12:
        print(
            f"\nNote: that is {len(password)} characters. Anything reachable "
            "from the internet deserves 12 or more.\n",
            file=sys.stderr,
        )

    print("\nAdd these to Backend/.env:\n")
    print(f"ADMIN_PASSWORD_HASH={hash_password(password)}")
    print(f"SESSION_SECRET={secrets.token_urlsafe(48)}")
    print("\nAnd set ADMIN_EMAIL to the address you will log in with.")
    print("Changing SESSION_SECRET signs everyone out, which is how you")
    print("revoke a session before it expires.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
