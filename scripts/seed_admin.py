import argparse
import sys
import os

# Ensure project root is in sys.path when script is executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.enums import UserRole
from app.db.database import SessionLocal
from app.repository.user_repo import UserRepository


DEFAULT_ADMINS = [
    {
        "name": "System Admin",
        "email": "ppsdev6@gmail.com",
        "mobile": "+919876543210",
        "role": UserRole.ADMIN,
        "user_code": "USR-ADMIN01",
    },
    {
        "name": "System Admin",
        "email": "modaksubham866@gmail.com",
        "mobile": "+919876543211",
        "role": UserRole.ADMIN,
        "user_code": "USR-ADMIN02",
    },
]


def seed_admins(
    name: str | None = None,
    email: str | None = None,
    mobile: str | None = None,
    role: str = "ADMIN",
) -> None:
    """Seed default or custom admin/staff users into the database."""
    db = SessionLocal()
    user_repo = UserRepository(db)

    try:
        if name and email and mobile:
            targets = [
                {
                    "name": name,
                    "email": email,
                    "mobile": mobile,
                    "role": UserRole(role.upper()),
                    "user_code": None,
                }
            ]
        else:
            targets = DEFAULT_ADMINS

        created_count = 0
        skipped_count = 0

        for target in targets:
            existing = user_repo.get_by_email(target["email"])
            if existing:
                print(f"[SKIP] Admin user with email '{target['email']}' already exists (ID: {existing.id}, Role: {existing.role.value}).")
                skipped_count += 1
                continue

            user = user_repo.create_user(
                name=target["name"],
                email=target["email"],
                mobile=target["mobile"],
                role=target["role"],
                user_code=target.get("user_code"),
            )
            print(f"[CREATED] Success! Created {user.role.value} user: {user.name} ({user.email}) - Code: {user.user_code}")
            created_count += 1

        print(f"\nSeeding complete: {created_count} created, {skipped_count} skipped.")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Failed to seed admin users: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Admin/Staff users into database.")
    parser.add_argument("--name", type=str, help="Admin full name (e.g. 'John Doe')")
    parser.add_argument("--email", type=str, help="Admin email address")
    parser.add_argument("--mobile", type=str, help="Admin mobile number (e.g. '+919876543210')")
    parser.add_argument("--role", type=str, choices=["ADMIN", "STAFF"], default="ADMIN", help="Role for the admin user")

    args = parser.parse_args()
    seed_admins(
        name=args.name,
        email=args.email,
        mobile=args.mobile,
        role=args.role,
    )
