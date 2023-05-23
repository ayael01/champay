from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # Import Flask-Migrate


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your own secret key

# Add these lines
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://aya_el01:ccaa00@localhost/champay_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Initialize Flask-Migrate after db

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

@app.route("/", methods=["GET", "POST"])
def homepage():
    session.pop('_flashes', None)  # Ensure old flashes are removed
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session["username"] = user.username
            session["email"] = user.email
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Unknown user or incorrect password.", "error")
    return render_template("homepage.html")


@app.route("/dashboard")
def dashboard():
    message = session.pop("message", None)

    # Fetch all groups from the database
    groups = Group.query.all()

    return render_template("dashboard.html", message=message, groups=groups)


@app.route("/group_expenses/<int:group_id>", methods=["GET", "POST"])
def group_expenses(group_id):
    username = session.get('username', 'Unknown')  # If 'username' doesn't exist in the session, 'Unknown' will be used
    user = User.query.filter_by(username=username).first()

    if request.method == "POST":
        description = request.form["description"]
        expenses = request.form["expenses"]

        # Check if the user already has expenses for the given group
        expense = Expense.query.filter_by(user_id=user.id, group_id=group_id).first()

        if expense:
            # Update the existing expense
            expense.description = description
            expense.amount = expenses
        else:
            # Create a new expense
            expense = Expense(description=description, amount=expenses, user_id=user.id, group_id=group_id)
            db.session.add(expense)

        db.session.commit()

        flash("Expenses updated successfully!", "success")
        return redirect(url_for("group_expenses", group_id=group_id))

    group_expenses = Expense.query.filter_by(group_id=group_id).all()
    group_expenses_list = []

    for expense in group_expenses:
        expense_owner = User.query.filter_by(id=expense.user_id).first()
        group_expenses_list.append({"user": expense_owner.username, 
                                    "description": expense.description, 
                                    "expenses": expense.amount, 
                                    "approved": expense.approved})

    return render_template("group_expenses.html", group_id=group_id, group_expenses=group_expenses_list, username=username)




@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    return response


if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)
