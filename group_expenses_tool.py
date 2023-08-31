from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash
from datetime import datetime
import os
from sqlalchemy import func, select
from pytz import timezone
from pytz import timezone
import datetime


app = Flask(__name__)
app.secret_key = 'your_secret_key'
if os.environ.get('CHAMPAY_ENV') == 'production':
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres123456@champay-rds.crlez4n4tsbc.eu-north-1.rds.amazonaws.com/champay_db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://aya_el01:ccaa00@localhost/champay_db'
db = SQLAlchemy(app)

tz = timezone('Israel')  # Set timezone to Israel

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password = db.Column(db.String(128))
    email = db.Column(db.String(120), index=True, unique=True)
    is_logged_in = db.Column(db.Boolean, default=False)
    group_memberships = db.relationship("GroupMember", backref="user")
    def serialize(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email
            # add more fields as needed
        }
    tasks = db.relationship('Task', backref='user', lazy=True)


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    group_members = db.relationship('GroupMember', backref='group')  # new line
    tasks = db.relationship('Task', backref='group', lazy=True)


class GroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    weight = db.Column(db.Integer, default=1.0) 
    last_updated = db.Column(db.DateTime, default=None, onupdate=datetime.datetime.now(tz))


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    approved = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime, default=None, onupdate=datetime.datetime.now(tz))
    user = db.relationship('User', backref='expenses')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    text = db.Column(db.String(500))  # or use db.Text
    date = db.Column(db.DateTime, default=datetime.datetime.now(tz))
    user = db.relationship('User', backref='comments')
    group = db.relationship('Group', backref='comments')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(500))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

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

def list_groups():
    # List all groups
    groups = Group.query.all()
    print("Group IDs and their names:")
    for group in groups:
        print(f"{group.id}: {group.name}")

def delete_group_expenses(app, group_id):
    with app.app_context():
        group = Group.query.filter_by(id=group_id).first()
        if not group:
            return f"Group id {group_id} does not exist."

        try:
            # Delete all tasks related to the group
            Task.query.filter_by(group_id=group_id).delete()

            # Delete all comments related to the group
            Comment.query.filter_by(group_id=group_id).delete()

            # Continue with the previous deletion logic
            # Delete all expenses related to the group
            Expense.query.filter_by(group_id=group_id).delete()

            # Delete all memberships related to the group
            GroupMember.query.filter_by(group_id=group_id).delete()

            # Delete the group itself
            db.session.delete(group)

            db.session.commit()

            return f"Successfully deleted group id {group_id}."

        except Exception as e:
            db.session.rollback()
            return f"Failed to delete group id {group_id}. Error: {str(e)}"



if __name__ == "__main__":
    app.run(debug=True)
