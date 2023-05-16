from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your own secret key

@app.route("/", methods=["GET", "POST"])
def homepage():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Validate and process the login credentials here
        if email == "ayael01@gmail.com" and password == "123456":
            session["username"] = "Eli"  # Set the username in the session
            session["message"] = {"category": "success", "text": "Login successful!"}
            return redirect(url_for("dashboard"))
        else:
            session["message"] = {"category": "error", "text": "Invalid email or password."}

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



if __name__ == "__main__":
    app.run(debug=True)
