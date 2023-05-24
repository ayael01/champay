from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://aya_el01:ccaa00@localhost/champay_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    password = db.Column(db.String(128))
    email = db.Column(db.String(120), index=True, unique=True)

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
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
            return redirect(url_for("dashboard"))
        else:
            flash("Unknown user or incorrect password.", "error")

    return render_template("homepage.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    message = session.pop("message", None)

    # Fetch all groups from the database
    groups = Group.query.all()

    if request.method == "POST":
        selected_group_id = int(request.form["group"])
        return redirect(url_for("group_expenses", group_id=selected_group_id))
    
    return render_template("dashboard.html", message=message, groups=groups)

@app.route("/group_expenses/<int:group_id>", methods=["GET", "POST"])
def group_expenses(group_id):
    username = session.get('username', 'Unknown')
    user = User.query.filter_by(username=username).first()
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

        # Check if the user is already a member of the group
        group_member = GroupMember.query.filter_by(user_id=user.id, group_id=group_id).first()

        if not group_member:
            # If the user is not a member, create a new group member object
            group_member = GroupMember(user_id=user.id, group_id=group_id)
            db.session.add(group_member)
            db.session.commit()

        flash("Expenses updated successfully!", "success")
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

    return render_template("group_expenses.html", group=group, group_expenses=group_expenses_list, username=username)



@app.route("/group_report/<int:group_id>")
def group_report(group_id):
    # Retrieve the group information by ID
    group = Group.query.get(group_id)

    # Fetch the group expenses from the database
    group_expenses = Expense.query.filter_by(group_id=group_id).all()

    # Generate the report
    report = generate_group_report(group, group_expenses)

    return render_template("group_report.html", group_id=group_id, report=report)

def generate_group_report(group, group_expenses):
    # Retrieve the group members
    group_members = GroupMember.query.filter_by(group_id=group.id).all()
    num_members = len(group_members)

    if num_members == 0:
        return "No members in the group."

    total_expenses = sum(expense.amount for expense in group_expenses)
    share = total_expenses / num_members

    report = f"Group: {group.name}\n\n"
    report += "Expenses:\n"

    for expense in group_expenses:
        user = User.query.get(expense.user_id)
        report += f"- {user.username}: {expense.amount}\n"

    report += f"\nTotal Expenses: {total_expenses}\n"
    report += f"Share per member: {share}\n\n"

    # Calculate the transfers and append to the report
    transfers = calculate_transfers(group_expenses, share)
    report += "Transfers:\n"

    for debtor, creditor, amount in transfers:
        report += f"- {debtor} should transfer {amount} to {creditor}\n"

    return report


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
