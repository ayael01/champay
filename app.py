from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from flask import render_template_string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Boolean
from flask import abort
import os


app = Flask(__name__)
app.secret_key = 'your_secret_key'

if os.environ.get('CHAMPAY_ENV') == 'production':
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres123456@champay-rds.crlez4n4tsbc.eu-north-1.rds.amazonaws.com/champay_db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://aya_el01:ccaa00@localhost/champay_db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

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



@app.route("/", methods=["GET", "POST"])
def homepage():
    session.pop('_flashes', None)   # Clear flashed messages

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["username"] = user.username
            session["email"] = user.email

            # Update the user's login status in the database
            user.is_logged_in = True
            db.session.commit()

            return redirect(url_for("dashboard"))
        else:
            flash("Unknown user or incorrect password.", "error")

    return render_template("homepage.html", username=session.get("username"))


@app.route("/logout")
def logout():
    # Retrieve the currently logged-in user
    username = session.get("username")
    user = User.query.filter_by(username=username).first()

    if user:
        # Update the user's login status in the database
        user.is_logged_in = False
        db.session.commit()

    # Clear the session data
    session.clear()

    # Redirect the user to the homepage or any other desired page
    return redirect(url_for("homepage"))


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    message = session.pop("message", None)

    # Retrieve the currently logged-in user
    username = session.get("username")
    user = User.query.filter_by(username=username).first()

    # Check if the user is found
    if not user:
        return redirect(url_for("homepage"))  # Redirect to login page

    # Fetch the groups that the user is a member of
    group_memberships = GroupMember.query.filter_by(user_id=user.id).all()
    group_ids = [gm.group_id for gm in group_memberships]
    groups = Group.query.filter(Group.id.in_(group_ids)).all()

    if request.method == "POST":
        selected_group_id = int(request.form["group"])
        return redirect(url_for("group_expenses", group_id=selected_group_id))

    return render_template("dashboard.html", message=message, groups=groups, username=username)


@app.route("/group_expenses/<int:group_id>", methods=["GET", "POST"])
def group_expenses(group_id):
    username = session.get('username', 'Unknown')

    # Check if the user is logged in
    if not username:
        abort(401)  # Unauthorized

    user = User.query.filter_by(username=username).first()

    # Check if the user is found
    if not user:
        abort(401)  # Unauthorized

    # Check if the user is a member of the group
    group_membership = GroupMember.query.filter_by(user_id=user.id, group_id=group_id).first()
    if not group_membership:
        abort(403)  # Forbidden

    group = Group.query.get(group_id)

    if request.method == "POST":
        description = request.form["description"]
        expenses = request.form["expenses"]

        # Check if the user already has an expense in the group
        expense = Expense.query.filter_by(user_id=user.id, group_id=group_id).first()

        if expense:
            # If an expense exists, update its description and amount
            expense.description = description
            expense.amount = expenses
        else:
            # If no expense exists, create a new one
            expense = Expense(
                description=description,
                amount=expenses,
                user_id=user.id,
                group_id=group_id
            )
            db.session.add(expense)

        expense.last_updated = datetime.utcnow()
        db.session.commit()

        # Check if all expenses are updated for the group
        all_expenses_updated = are_all_expenses_updated(group_id)

        if all_expenses_updated:
            # If all expenses are updated, redirect to the report page
            # flash("Expenses updated successfully!", "success")
            return redirect(url_for("group_expenses", group_id=group_id))


        # flash("Expenses updated successfully!", "success")
        return redirect(url_for("group_expenses", group_id=group_id))

    group_expenses = Expense.query.filter_by(group_id=group_id).all()
    group_expenses_list = []

    for expense in group_expenses:
        expense_owner = User.query.filter_by(id=expense.user_id).first()
        group_expenses_list.append({
            "user": expense_owner.username,
            "description": expense.description,
            "expenses": expense.amount,
            "last_updated": expense.last_updated
        })

    # Check if all expenses are updated for the group
    all_expenses_updated = are_all_expenses_updated(group_id)

    return render_template("group_expenses.html", group=group, group_expenses=group_expenses_list, username=username, all_expenses_updated=all_expenses_updated)


def are_all_expenses_updated(group_id):
    # Count the number of group members
    num_members = GroupMember.query.filter_by(group_id=group_id).count()

    # Count the number of expenses updated by group members
    num_expenses_updated = Expense.query.filter_by(group_id=group_id).filter(Expense.last_updated != None).count()

    # Return whether all expenses are updated or not
    return num_expenses_updated == num_members



@app.route("/group_report/<int:group_id>")
def group_report(group_id):

    username = session.get('username', 'Unknown')

    # Check if the user is logged in
    if not username:
        abort(401)  # Unauthorized

    user = User.query.filter_by(username=username).first()

    # Check if the user is found
    if not user:
        abort(401)  # Unauthorized

    # Check if the user is a member of the group
    group_membership = GroupMember.query.filter_by(user_id=user.id, group_id=group_id).first()
    if not group_membership:
        abort(403)  # Forbidden
    # Retrieve the group information by ID
    group = Group.query.get(group_id)

    # Fetch the group expenses from the database
    group_expenses = Expense.query.filter_by(group_id=group_id).all()

    # Generate the report
    report = generate_group_report(group, group_expenses)

    return report


def generate_group_report(group, group_expenses):
    # Retrieve the group members
    group_members = GroupMember.query.filter_by(group_id=group.id).all()
    num_members = len(group_members)

    if num_members == 0:
        return "No members in the group."

    total_expenses = sum(expense.amount for expense in group_expenses)
    share = total_expenses / num_members

    group_expenses_list = []

    for expense in group_expenses:
        expense_owner = User.query.filter_by(id=expense.user_id).first()
        formatted_last_updated = expense.last_updated.strftime('%Y-%m-%d %H:%M')
        group_expenses_list.append({
            "user": expense_owner,
            "description": expense.description,
            "amount": expense.amount,  # Include amount directly
            "last_updated": formatted_last_updated
        })

    report_data = {
        'group_name': group.name,
        'group_expenses': group_expenses_list,
        'total_expenses': total_expenses,
        'share': share,
        'transfers': calculate_transfers(group_expenses, share),
        'group_id': group.id  # Pass group_id to the template
    }

    return render_template('group_report_template.html', **report_data)





def calculate_transfers(group_expenses, share):
    balances = {}

    for expense in group_expenses:
        user = User.query.get(expense.user_id)
        if user.username not in balances:
            balances[user.username] = 0
        balances[user.username] += expense.amount - share

    transfers = []

    while len(balances) > 1:
        debtor = min(balances, key=balances.get)
        creditor = max(balances, key=balances.get)
        amount = min(abs(balances[debtor]), balances[creditor])
        
        if amount == 0:
            break  # Skip transfers with transfer amount of 0.0

        balances[debtor] += amount
        balances[creditor] -= amount

        if balances[creditor] == 0:
            del balances[creditor]

        transfers.append((debtor, creditor, amount))

    return transfers




@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    return response

if __name__ == "__main__":
    with app.app_context():
        db.create_all() # Create database tables
    app.run(debug=True)
