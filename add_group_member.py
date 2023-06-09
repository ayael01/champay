from app import app, db
from app import GroupMember, Expense, User, Group
from datetime import datetime

def add_group_member(user_id, group_id):
    with app.app_context():
        group_member = GroupMember.query.filter_by(user_id=user_id, group_id=group_id).first()

        if group_member:
            print("User is already a member of the group.")
            return

        # Create a new group member
        new_group_member = GroupMember(user_id=user_id, group_id=group_id)
        db.session.add(new_group_member)

        # Create initial group expense for the user
        user = db.session.get(User, user_id)
        group = db.session.get(Group, group_id)

        initial_expense = Expense(
            description="N/A",
            amount=0.0,
            user_id=user_id,
            group_id=group_id,
            approved=False,
            last_updated=None,  # Set to None initially
            user=user
        )
        db.session.add(initial_expense)

        db.session.commit()
        print("User added to the group and initial group expenses created successfully!")

# Usage example
if __name__ == "__main__":
    add_group_member(6, 2)
