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
    
    # Dummy data
    groups = [
        {'id': 1, 'name': "Group 1"},
        {'id': 2, 'name': "Group 2"},
        {'id': 3, 'name': "Group 3"},
    ]

    return render_template("dashboard.html", message=message, groups=groups)


@app.route("/group_expenses/<int:group_id>", methods=["GET", "POST"])
def group_expenses(group_id):
    username = session.get('username', 'Unknown')  # If 'username' doesn't exist in the session, 'Unknown' will be used
    if request.method == "POST":
        # Get the description, and expenses from the submitted form
        description = request.form["description"]
        expenses = request.form["expenses"]

        # Validate and process the expenses here
        # ...

        return redirect(url_for("group_expenses", group_id=group_id, username=username))

    # Dummy data
    group_expenses = [
        {"user": "User 1", "description": "Food", "expenses": 20.00, "approved": False},
        {"user": "User 2", "description": "Drinks", "expenses": 30.00, "approved": False},
        {"user": "User 3", "description": "Snacks", "expenses": 10.00, "approved": False},
    ]

    return render_template("group_expenses.html", group_id=group_id, group_expenses=group_expenses, username=username)


@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    return response


if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create database tables
    app.run(debug=True)
