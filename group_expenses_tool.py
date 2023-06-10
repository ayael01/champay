from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://aya_el01:ccaa00@localhost/champay_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password = db.Column(db.String(128))
    email = db.Column(db.String(120), index=True, unique=True)
    is_logged_in = db.Column(db.Boolean, default=False)
    group_memberships = db.relationship("GroupMember", backref="user")


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)

class GroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    approved = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime, default=None, onupdate=datetime.utcnow)
    user = db.relationship('User', backref='expenses')


def create_group_expenses(app, group_name, user_ids):
    with app.app_context():
        # Check if all user IDs are valid and exist in the database
        users = User.query.filter(User.id.in_(user_ids)).all()

        if len(users) != len(user_ids):
            # Some user IDs are invalid or not found
            return "Invalid user IDs. Please check the user IDs and try again."

        try:
            # Create the group
            group = Group(name=group_name)
            db.session.add(group)
            db.session.commit()

            # Create the group memberships
            for user in users:
                group_member = GroupMember(user_id=user.id, group_id=group.id)
                db.session.add(group_member)

                # Create the initial expense for the user
                initial_expense = Expense(
                    description="N/A",
                    amount=0.0,
                    user_id=user.id,
                    group_id=group.id,
                    approved=False,
                    last_updated=None,  # Set to None initially
                    user=user
                )
                db.session.add(initial_expense)

            db.session.commit()

            return "Group expenses created successfully."

        except Exception as e:
            # Handle any exceptions that occur during group creation
            db.session.rollback()
            return f"Failed to create group expenses. Error: {str(e)}"




if __name__ == "__main__":
    app.run(debug=True)
