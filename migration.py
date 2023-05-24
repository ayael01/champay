from app import app, db
from app import User, Expense


def recreate_expenses():
    with app.app_context():
        expenses = Expense.query.all()
        for expense in expenses:
            db.session.delete(expense)
        db.session.commit()

        # Mapping of usernames to expenses
        user_expenses = {
            'Eli': 700.0,
            'Doron': 450.0,
            'Boaz': 200.0,
            'Ran': 1500.0,
            'Michael': 450.0
        }

        users = User.query.all()
        for user in users:
            username = user.username
            if username in user_expenses:
                expense = Expense(
                    description=f"Expense for {username}",
                    amount=user_expenses[username],
                    user=user
                )
                db.session.add(expense)
        db.session.commit()


recreate_expenses()

