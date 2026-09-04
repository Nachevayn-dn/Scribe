"""One-off: flag an existing account as a platform admin (MedicDesk operator
access — the /platform console). There's no self-serve way to become one, by
design.

Usage (from backend/, with the venv active):
    python -m scripts.grant_platform_admin you@example.com

The account must already exist (sign up your own clinic normally first,
then run this against that login email).
"""
import asyncio
import sys

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.user import User


async def main(email: str) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            print(f"No user found with email {email!r}. Sign up a clinic with this email first.")
            sys.exit(1)
        user.is_platform_admin = True
        await db.commit()
        print(f"{email} is now a platform admin. Log out and back in for it to take effect.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.grant_platform_admin you@example.com")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
