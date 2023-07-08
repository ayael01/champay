from flask import Flask, render_template, request, session, flash, redirect, url_for, jsonify

from werkzeug.security import check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
from flask import render_template_string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Boolean
from flask import abort
import os
from sqlalchemy.exc import SQLAlchemyError
from pytz import timezone
import datetime
import group_expenses_tool as get
import logging

# Configure the logger
logging.basicConfig(
    filename='output.log', 
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)




app = Flask(__name__)
app.secret_key = 'your_secret_key'

if os.environ.get('CHAMPAY_ENV') == 'production':
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:postgres123456@champay-rds.crlez4n4tsbc.eu-north-1.rds.amazonaws.com/champay_db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://aya_el01:ccaa00@localhost/champay_db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

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


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    group_members = db.relationship('GroupMember', backref='group')  # new line


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


def log(username, message):
    logging.info(f"User: {username}, Action: {message}")


@app.route("/", methods=["GET", "POST"])
def homepage():
    session.pop('_flashes', None)   # Clear flashed messages

    if request.method == "POST":
        email = request.form["email"].lower()
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["username"] = user.username
            session["email"] = user.email

            # Update the user's login status in the database
            user.is_logged_in = True
            db.session.commit()

            log(user.email, f'Attempted to access {request.path} path')

            return redirect(url_for("dashboard"))
        else:
            log(email, 'Unknown user or incorrect password.')
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

        # Log the successful logout action
        log(user.email, f'Successfully logged out from {request.path} path')

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

    # Log that user has accessed dashboard
    log(user.email, f'Accessed {request.path} path')

    # Fetch the groups that the user is a member of
    group_memberships = GroupMember.query.filter_by(user_id=user.id).all()
    group_ids = [gm.group_id for gm in group_memberships]
    groups = Group.query.filter(Group.id.in_(group_ids)).all()

    if request.method == "POST":
        selected_group_id = int(request.form["group"])
        # Log group selection
        log(user.email, f'Selected group with id {selected_group_id} in {request.path} path')
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

    # Log the user's attempt to access group expenses
    log(user.email, f'Attempted to access {request.path} path')

    if request.method == "POST":
        description = request.form["description"]
        expenses = float(request.form["expenses"])  # Make sure expenses are treated as numbers

        # Block updates with expenses under zero
        if expenses < 0:
            flash("Expenses cannot be less than zero. Please enter a valid amount.", "error")
            return redirect(url_for("group_expenses", group_id=group_id))

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

        expense.last_updated = datetime.datetime.now(tz)

        try:
            db.session.commit()
            all_expenses_updated = are_all_expenses_updated(group_id)
            if all_expenses_updated:
                # If all expenses are updated, redirect to the report page
                flash(f"Expenses updated successfully! {description} - {expenses}", "success")
                # Log the successful update
                log(user.email, f'Successfully updated expenses on {request.path} path')
                return redirect(url_for("group_expenses", group_id=group_id))
            else:
                flash(f"Expenses updated successfully! {description} - {expenses}", "success")
                # Log the successful update
                log(user.email, f'Successfully updated expenses on {request.path} path')

        except SQLAlchemyError:
            db.session.rollback()
            flash("Failed to update expenses. Please try again.", "error")
            # Log the failed update
            log(user.email, f'Failed to update expenses on {request.path} path')

        return redirect(url_for("group_expenses", group_id=group_id))

    # Split the expenses into updated and not updated
    updated_expenses = Expense.query.filter(Expense.group_id == group_id, Expense.last_updated.isnot(None)).order_by(Expense.last_updated.desc()).all()
    not_updated_expenses = Expense.query.filter(Expense.group_id == group_id, Expense.last_updated.is_(None)).all()

    # Append not updated expenses to the list of updated ones
    group_expenses = updated_expenses + not_updated_expenses

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
    user = User.query.filter_by(username=username).first()
    
    # Log the user's attempt to access group report
    log(user.email if user else 'Unknown', f'Attempted to access {request.path} path')

    # Check if all expenses are updated for the group
    all_expenses_updated = are_all_expenses_updated(group_id)
    if not all_expenses_updated:
        flash("Cannot generate report. Not all users have updated their expenses.", "error")
        # Log the failed report generation
        log(user.email if user else 'Unknown', f'Failed to generate report on {request.path} path due to unupdated expenses')
        return redirect(url_for("group_expenses", group_id=group_id))

    # Check if the user is logged in
    if not username:
        abort(401)  # Unauthorized

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
    group_expenses = Expense.query.filter_by(group_id=group_id).order_by(Expense.last_updated.desc()).all()

    # Generate the report
    # Fetch the group members from the database
    group_members = GroupMember.query.filter_by(group_id=group_id).all()

    # Check if all members have the same weight
    weights = [member.weight for member in group_members]
    if len(set(weights)) == 1:  # The set operation will remove duplicate values
        # All members have the same weight, so generate a regular report
        report = generate_group_report(group, group_expenses)
    else:
        # Not all members have the same weight, so generate a weighted report
        report = generate_group_report_by_weight(group, group_expenses)

    # Log the successful report generation
    log(user.email, f'Successfully generated report on {request.path} path')

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


def generate_group_report_by_weight(group, group_expenses):
    # Retrieve the group members
    group_members = GroupMember.query.filter_by(group_id=group.id).all()
    total_weight = sum(member.weight for member in group_members)

    if total_weight == 0:
        return "No weights assigned in the group."

    total_expenses = sum(expense.amount for expense in group_expenses)
    weighted_share = total_expenses / total_weight

    group_expenses_list = []

    for expense in group_expenses:
        expense_owner = User.query.filter_by(id=expense.user_id).first()
        weight = GroupMember.query.filter_by(user_id=expense.user_id, group_id=group.id).first().weight  # Get weight
        formatted_last_updated = expense.last_updated.strftime('%Y-%m-%d %H:%M')
        group_expenses_list.append({
            "user": expense_owner.username,
            "description": expense.description,
            "amount": expense.amount,
            "weight": weight,  # Add weight to the dictionary
            "last_updated": formatted_last_updated
        })

    report_data = {
        'group_name': group.name,
        'group_expenses': group_expenses_list,
        'total_expenses': total_expenses,
        'share': weighted_share,
        'transfers': calculate_transfers_by_weight(group_expenses, weighted_share, group.id),
        'group_id': group.id,  # Pass group_id to the template
        'total_weight': total_weight  # Pass total_weight to the template
    }

    return render_template('group_report_template_by_weight.html', **report_data)


def calculate_transfers_by_weight(group_expenses, weighted_share, group_id):
    balances = {}

    for expense in group_expenses:
        user = User.query.get(expense.user_id)
        weight = GroupMember.query.filter_by(user_id=user.id, group_id=group_id).first().weight
        if user.username not in balances:
            balances[user.username] = 0
        balances[user.username] += expense.amount - (weighted_share * weight)

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



@app.route('/group_settings/<int:group_id>', methods=['GET', 'POST'])
def group_settings(group_id):
    username = session.get('username')
    
    # Log the user's attempt to access group settings
    log(username if username else 'Unknown', f'Attempted to access {request.path} path')
    
    if not username:
        abort(401)  # Unauthorized

    user = User.query.filter_by(username=username).first()

    if not user:
        abort(401)  # Unauthorized

    group_membership = GroupMember.query.filter_by(user_id=user.id, group_id=group_id).first()
    if not group_membership:
        abort(403)  # Forbidden

    group = Group.query.get(group_id)

    if request.method == "POST":
        weight = int(request.form["weight"])

        if weight < 1 or weight > 10:
            flash("Weight should be between 1 and 10. Please enter a valid weight.", "error")
            # Log the failed weight update due to invalid weight
            log(user.email, f'Failed to update weight on {request.path} path due to invalid weight')
            return redirect(url_for("group_settings", group_id=group_id))

        group_membership.weight = weight
        group_membership.last_updated = datetime.datetime.now(tz)

        try:
            db.session.commit()
            flash(f"Weight updated successfully! Your weight in the expenses is {weight}", "success")
            # Log the successful weight update
            log(user.email, f'Successfully updated weight on {request.path} path')

        except SQLAlchemyError:
            db.session.rollback()
            flash("Failed to update weight. Please try again.", "error")
            # Log the failed weight update due to a database error
            log(user.email, f'Failed to update weight on {request.path} path due to database error')

        return redirect(url_for("group_settings", group_id=group_id))

    updated_group_members = GroupMember.query.filter(GroupMember.last_updated.isnot(None), GroupMember.group_id==group_id).order_by(GroupMember.last_updated.desc()).all()
    not_updated_group_members = GroupMember.query.filter(GroupMember.last_updated.is_(None), GroupMember.group_id==group_id).all()

    group_members = updated_group_members + not_updated_group_members

    members = []
    for member in group_members:
        member_user = User.query.get(member.user_id)
        members.append({
            'username': member_user.username,
            'weight': member.weight,
            'last_updated': member.last_updated  # include last_updated information
        })

    return render_template('group_settings.html', group=group, members=members, username=username)



@app.route('/create_group', methods=['GET', 'POST'])
def create_group():
    if 'username' not in session:
        flash("Please login first.")
        log(session.get('email', 'Guest'), 'Attempted to access create_group without logging in')
        return redirect(url_for('homepage'))

    username = session['username']
    user = User.query.filter_by(username=username).first()
    email = user.email

    if request.method == 'POST':
        event_name = request.form.get('event-name')
        event_description = request.form.get('event-description')  # Add other fields as necessary

        # Check if the event name already exists in the database
        existing_group = Group.query.filter_by(name=event_name).first()
        if existing_group is not None:
            flash("Event name already taken. Please choose a different name.", "error")
            log(email, f'Attempted to create group with existing name: {event_name}')
            return redirect(url_for('dashboard'))

        session['event_name'] = event_name
        log(email, f'Successfully created group: {event_name}')

    log(email, f'Accessed create_group')
    return render_template('create_group.html', username=username, email=email, user_id=user.id, event_name=session.get('event_name'))






@app.route('/search_friends', methods=['POST'])
def search_friends():

    # Check if the user is logged in
    if 'username' not in session:
        return jsonify({"error": "You must be logged in to perform this action."}), 401

    # get the submitted email
    email = request.json.get('email')
    # search the database for a user with this email
    user = User.query.filter(User.email.ilike(email)).first()
    if user:
        # return the user details if found
        return jsonify(user=user.serialize()), 200
    else:
        # return an error message if not found
        return jsonify(error=f"User {email} not found"), 404
    

def create_group_expenses(group_name, member_ids):
    # Check if all user IDs are valid and exist in the database
    users = User.query.filter(User.id.in_(member_ids)).all()

    if len(users) != len(member_ids):
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

        return group.id, "Group expenses created successfully."

    except Exception as e:
        # Handle any exceptions that occur during group creation
        db.session.rollback()
        return None, f"Failed to create group expenses. Error: {str(e)}"

@app.route('/finalize_group', methods=['POST'])
def finalize_group():
    # Check if the user is logged in
    if 'username' not in session:
        log(session.get('email', 'Guest'), 'Attempted to access finalize_group without logging in')
        return jsonify({"error": "You must be logged in to perform this action."}), 401

    # Extracting data from the request body
    data = request.get_json()

    # Collecting required parameters
    group_name = data.get('groupName')
    member_ids = data.get('groupMembers')

    # Log the group creation attempt
    log(session['email'], f'Attempted to create group: {group_name} with members: {member_ids}')

    # Create the group using create_group_expenses function
    group_id, response_message = create_group_expenses(group_name, member_ids)

    # Check if the group creation was successful
    if "successfully" in response_message.lower():
        log(session['email'], f'Successfully created group: {group_name}')
        flash(f"Successfully created event {group_name}.", "success")
        return jsonify(success=True, group_id=group_id, message="Group created successfully.")
    else:
        log(session['email'], f'Failed to create group: {group_name}. Error: {response_message}')
        return jsonify(success=False, error=response_message)



@app.route('/edit_group/<int:group_id>', methods=['GET'])
def edit_group(group_id):
    if 'username' not in session:
        log(session.get('email', 'Guest'), 'Attempted to access edit_group without logging in')
        flash("Please login first.")
        return redirect(url_for('homepage'))

    group = Group.query.get(group_id)
    if not group:
        flash("Group not found.", "error")
        log(session['email'], f'Attempted to edit non-existing group with id: {group_id}')
        return redirect(url_for('dashboard'))

    # get current user's email based on the username stored in the session
    current_user = User.query.filter_by(username=session['username']).first()
    if current_user is None:
        flash("User not found.", "error")
        log(session['email'], f'User not found when attempting to edit group with id: {group_id}')
        return redirect(url_for('dashboard'))
    current_user_email = current_user.email

    # Check if the user is a member of the group
    group_membership = GroupMember.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not group_membership:
        flash("You are not a member of this group.", "error")
        log(current_user_email, f'Attempted to edit group {group_id} without being a member')
        return redirect(url_for('dashboard')) 

    group_members = [member.user.serialize() for member in group.group_members]
    log(current_user_email, f'Accessed edit_group for group {group_id}')
    return render_template('edit_group.html', group=group, group_id=group_id, group_name=group.name, group_members=group_members, username=session['username'], current_user_email=current_user_email)


@app.route("/add_user_to_group", methods=["POST"])
def add_user_to_group():
    # Check if the user is logged in
    if 'username' not in session:
        log(session.get('email', 'Guest'), 'Attempted to access add_user_to_group without logging in')
        return jsonify({"error": "You must be logged in to perform this action."}), 401

    data = request.get_json()
    email = data.get('email')
    group_id = data.get('group_id')

    # Log the attempt to add a user to a group
    log(session['email'], f'Attempted to add user {email} to group {group_id}')

    # Check if the user exists
    user = User.query.filter_by(email=email).first()
    if user is None:
        return jsonify({"error": "User not found."}), 400

    # Check if the user is already part of the group
    existing_group_member = GroupMember.query.filter_by(user_id=user.id, group_id=group_id).first()
    if existing_group_member is not None:
        log(session['email'], f'Attempted to add user {email} who is already a member of group {group_id}')
        return jsonify({"error": "User is already part of the group."}), 400

    try:
        # Add the user to the group
        group_member = GroupMember(user_id=user.id, group_id=group_id)
        db.session.add(group_member)

        # Add an initial expense for the user
        initial_expense = Expense(
            description="N/A",
            amount=0.0,
            user_id=user.id,
            group_id=group_id,
            approved=False,
            last_updated=None,  # Set to None initially
            user=user
        )
        db.session.add(initial_expense)
        db.session.commit()

        log(session['email'], f'Successfully added user {email} to group {group_id}')
        return jsonify({"message": "User added to group successfully."}), 200

    except Exception as e:
        db.session.rollback()
        log(session['email'], f'Failed to add user {email} to group {group_id}. Error: {str(e)}')
        return jsonify({"error": f"Failed to add user to group. Error: {str(e)}"}), 500



@app.route("/remove_user_from_group", methods=["POST"])
def remove_user_from_group():
    current_user_email = session.get('email', 'Guest')  # retrieve current user email, or set to 'Guest' if not logged in

    # Check if the user is logged in
    if 'username' not in session:
        log(current_user_email, 'Attempted to access remove_user_from_group without logging in')
        return jsonify({"error": "You must be logged in to perform this action."}), 401

    data = request.get_json()
    email = data.get('email')
    group_id = data.get('group_id')

    log(current_user_email, f'Attempting to remove user with email {email} from group {group_id}')

    group = Group.query.get(group_id)  # Retrieve the group data by id
    users_in_group = group.group_members  # Get all users in the group

    if len(users_in_group) <= 1:
        # If there's only one user in the group, return an error message
        log(current_user_email, 'Attempted to remove the only user from a group')
        return jsonify({'error': 'Cannot remove the user as a group cannot be empty.'}), 400

    # Check if the user exists
    user = User.query.filter_by(email=email).first()
    if user is None:
        log(current_user_email, f'User with email {email} not found')
        return jsonify({"error": "User not found."}), 400

    # Check if the user is part of the group
    existing_group_member = GroupMember.query.filter_by(user_id=user.id, group_id=group_id).first()
    if existing_group_member is None:
        log(current_user_email, f'User with email {email} is not part of group {group_id}')
        return jsonify({"error": "User is not part of the group."}), 400

    try:
        # Remove the user from the group
        db.session.delete(existing_group_member)

        # Remove the user's expenses from the group
        expenses = Expense.query.filter_by(user_id=user.id, group_id=group_id).all()
        for expense in expenses:
            db.session.delete(expense)

        db.session.commit()

        log(current_user_email, f'Successfully removed user with email {email} from group {group_id}')
        return jsonify({"message": "User removed from group successfully."}), 200

    except Exception as e:
        db.session.rollback()
        log(current_user_email, f'Failed to remove user with email {email} from group {group_id}. Error: {str(e)}')
        return jsonify({"error": f"Failed to remove user from group. Error: {str(e)}"}), 500



@app.route('/previous_friends', methods=['GET'])
def previous_friends():
    # Check if user is logged in
    if 'username' not in session:
        return jsonify({'message': 'Not logged in.'}), 401

    # Get current user
    current_user = User.query.filter_by(username=session['username']).first()

    # If the user doesn't exist, return an error
    if current_user is None:
        return jsonify({'message': 'User not found.'}), 404

    current_user_groups = GroupMember.query.filter_by(user_id=current_user.id).all()
    group_ids = [gm.group_id for gm in current_user_groups]

    # Query distinct users who are a part of these groups but not the current user
    group_members = GroupMember.query.filter(GroupMember.group_id.in_(group_ids), GroupMember.user_id != current_user.id).distinct(GroupMember.user_id).all()

    friends = [gm.user for gm in group_members]

    return jsonify({
        'friends': [{'email': friend.email} for friend in friends]
    }), 200


@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    return response

if __name__ == "__main__":
    with app.app_context():
        db.create_all() # Create database tables
    
    if os.environ.get('CHAMPAY_ENV') == 'production':
        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        app.run(debug=True)

