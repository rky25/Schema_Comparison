import sys
import os

# Ensure backend folder is visible
sys.path.append(os.getcwd())

from backend.database import SessionLocal, User

def list_users():
    db = SessionLocal()
    users = db.query(User).all()
    db.close()

    try:
        from rich.console import Console
        from rich.table import Table

        if not users:
            print("No users found.")
            return

        console = Console()
        table = Table(title="Registered Users (users.db)")

        table.add_column("ID", style="cyan", justify="right")
        table.add_column("Username", style="magenta")
        table.add_column("Email", style="green")

        for user in users:
            table.add_row(str(user.id), user.username, user.email)

        console.print(table)
        print(f"\nTotal Users: {len(users)}")
        print(f"Database Location: {os.path.abspath('users.db')}")

    except ImportError:
        # Fallback if rich is not installed
        print("Registered Users (users.db):")
        print("-" * 50)
        if not users:
            print("No users found.")
        for u in users:
            print(f"ID: {u.id:<4} | User: {u.username:<15} | Email: {u.email}")
        print("-" * 50)
        print(f"Total Users: {len(users)}")
        print(f"Database Location: {os.path.abspath('users.db')}")

if __name__ == "__main__":
    list_users()
