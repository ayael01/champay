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
from boto3 import client
import base64
import uuid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pytz 



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
    timezone = db.Column(db.String(50), default='UTC')


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    group_members = db.relationship('GroupMember', backref='group')  # new line
    tasks = db.relationship('Task', backref='group', lazy=True)
    start_datetime = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    end_datetime = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    location = db.Column(db.String(200))

class GroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    weight = db.Column(db.Integer, default=1.0) 
    last_updated = db.Column(db.DateTime, default=None, onupdate=datetime.datetime.utcnow)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))
    amount = db.Column(db.Float)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    approved = db.Column(db.Boolean, default=False)
    last_updated = db.Column(db.DateTime, default=None, onupdate=datetime.datetime.utcnow)
    user = db.relationship('User', backref='expenses')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    text = db.Column(db.String(500))  # or use db.Text
    date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    user = db.relationship('User', backref='comments')
    group = db.relationship('Group', backref='comments')

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task = db.Column(db.String(500))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)



def log(username, message):
    logging.info(f"User: {username}, Action: {message}")


@app.route("/", methods=["GET", "POST"])
def homepage():
    session.pop('_flashes', None)   # Clear flashed messages

    if request.method == "POST":
        email = request.form["email"].lower()
        password = request.form["password"]
        timezone = request.form.get("timezone", "UTC")  # Default to UTC if not provided
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session["username"] = user.username
            session["email"] = user.email
            session["timezone"] = timezone  # Store the timezone in the session

            # Update the user's login status in the database
            user.is_logged_in = True
            user.timezone = timezone
            db.session.commit()

            log(user.email, f'Attempted to access {request.path} path')

            # Redirect to intended URL if it exists
            next_url = session.pop('next_url', None)
            if next_url:
                return redirect(next_url)
            else:
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

    if 'username' not in session:
        # Store the intended URL to redirect after login
        session['next_url'] = url_for('dashboard')
        return redirect(url_for('homepage'))
    
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
        return redirect(url_for("edit_group", group_id=selected_group_id))

    return render_template("dashboard.html", message=message, groups=groups, username=username)



@app.route("/group_expenses/<int:group_id>", methods=["GET", "POST"])
def group_expenses(group_id):

    if 'username' not in session:
        # Store the intended URL to redirect after login
        session['next_url'] = url_for('group_expenses', group_id=group_id)
        return redirect(url_for('homepage'))

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
    user_weight = GroupMember.query.filter_by(group_id=group_id, user_id=user.id).first().weight

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

        expense.last_updated = datetime.datetime.utcnow()

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
    user_timezone = pytz.timezone(user.timezone)
    for expense in group_expenses:
        expense_owner = User.query.filter_by(id=expense.user_id).first()
        member_weight = GroupMember.query.filter_by(group_id=group_id, user_id=expense.user_id).first().weight

        if expense.last_updated:  # Check if last_updated is not None
            # Convert the UTC time to user's local timezone
            utc_time = pytz.utc.localize(expense.last_updated)
            local_time = utc_time.astimezone(user_timezone)
        else:
            local_time = None

        group_expenses_list.append({
            "user": f"{expense_owner.username} ({member_weight})",
            "description": expense.description,
            "expenses": expense.amount,
            "last_updated": local_time  # This will be either in user's local timezone or None
        })




    # Check if all expenses are updated for the group
    all_expenses_updated = are_all_expenses_updated(group_id)

    return render_template("group_expenses.html", group=group, group_expenses=group_expenses_list, username=username, all_expenses_updated=all_expenses_updated, user_weight=user_weight)


def are_all_expenses_updated(group_id):
    # Count the number of group members
    num_members = GroupMember.query.filter_by(group_id=group_id).count()

    # Count the number of expenses updated by group members
    num_expenses_updated = Expense.query.filter_by(group_id=group_id).filter(Expense.last_updated != None).count()

    # Return whether all expenses are updated or not
    return num_expenses_updated == num_members



@app.route("/group_report/<int:group_id>")
def group_report(group_id):

    force_generate = request.args.get('force', 'false').lower() == 'true'

    username = session.get('username', 'Unknown')
    user = User.query.filter_by(username=username).first()
    
    # Log the user's attempt to access group report
    log(user.email if user else 'Unknown', f'Attempted to access {request.path} path')

    if not force_generate:
        # Check if all expenses are updated for the group
        all_expenses_updated = are_all_expenses_updated(group_id)
        if not all_expenses_updated:
            flash("Not all users have updated their expenses. Generate anyway?", "warning")
            # Log the failed report generation
            log(user.email if user else 'Unknown', f'Failed to generate report on {request.path} path due to unupdated expenses')
            return redirect(url_for("group_expenses", group_id=group_id))
    else:
        # Log that report generation was forced
        log(user.email if user else 'Unknown', f'Forced report generation on {request.path} path despite unupdated expenses')

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

    #for timezone conversion
    user_timezone = pytz.timezone(user.timezone if user else 'UTC')

    if len(set(weights)) == 1:  # The set operation will remove duplicate values
        # All members have the same weight, so generate a regular report
        report = generate_group_report(group, group_expenses, user_timezone)
    else:
        # Not all members have the same weight, so generate a weighted report
        report = generate_group_report_by_weight(group, group_expenses, user_timezone)

    # Log the successful report generation
    log(user.email, f'Successfully generated report on {request.path} path')

    return report




def generate_group_report(group, group_expenses, user_timezone):

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
        
        # Convert the UTC time to user's local timezone
        if expense.last_updated:
            utc_time = pytz.utc.localize(expense.last_updated)
            local_time = utc_time.astimezone(user_timezone)
            formatted_last_updated = local_time.strftime('%Y-%m-%d %H:%M')
        else:
            formatted_last_updated = "Not updated"

        group_expenses_list.append({
            "user": expense_owner,
            "description": expense.description,
            "amount": expense.amount,  # Include amount directly
            "last_updated": formatted_last_updated
        })

    # Fetch the group comments
    group_comments = Comment.query.filter_by(group_id=group.id).all()
    retrospectives = {}
    for comment in group_comments:
        comment_owner = User.query.filter_by(id=comment.user_id).first()
        if comment_owner.username not in retrospectives:
            retrospectives[comment_owner.username] = []
        retrospectives[comment_owner.username].append(comment.text)

    report_data = {
        'group_name': group.name,
        'group_expenses': group_expenses_list,
        'total_expenses': total_expenses,
        'share': share,
        'transfers': calculate_transfers(group_expenses, share),
        'group_id': group.id,  # Pass group_id to the template
        'retrospectives': retrospectives  # Pass the comments to the template
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


def generate_group_report_by_weight(group, group_expenses, user_timezone):
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

        # Convert the UTC time to user's local timezone
        if expense.last_updated:
            utc_time = pytz.utc.localize(expense.last_updated)
            local_time = utc_time.astimezone(user_timezone)
            formatted_last_updated = local_time.strftime('%Y-%m-%d %H:%M')
        else:
            formatted_last_updated = "Not updated"

        group_expenses_list.append({
            "user": expense_owner.username,
            "description": expense.description,
            "amount": expense.amount,
            "weight": weight,  # Add weight to the dictionary
            "last_updated": formatted_last_updated
        })

    # Fetch the group comments
    group_comments = Comment.query.filter_by(group_id=group.id).all()
    retrospectives = {}
    for comment in group_comments:
        comment_owner = User.query.filter_by(id=comment.user_id).first()
        if comment_owner.username not in retrospectives:
            retrospectives[comment_owner.username] = []
        retrospectives[comment_owner.username].append(comment.text)

    report_data = {
        'group_name': group.name,
        'group_expenses': group_expenses_list,
        'total_expenses': total_expenses,
        'share': weighted_share,
        'transfers': calculate_transfers_by_weight(group_expenses, weighted_share, group.id),
        'group_id': group.id,  # Pass group_id to the template
        'total_weight': total_weight,  # Pass total_weight to the template
        'retrospectives': retrospectives  # Pass the comments to the template
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
        group_membership.last_updated = datetime.datetime.utcnow()

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
        log(email, f'Successfully entered to group creation: {event_name}')

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
        flash(f"Successfully created trip {group_name}.", "success")
        return jsonify(success=True, group_id=group_id, message="Group created successfully.")
    else:
        log(session['email'], f'Failed to create group: {group_name}. Error: {response_message}')
        return jsonify(success=False, error=response_message)



@app.route('/edit_group/<int:group_id>', methods=['GET'])
def edit_group(group_id):

    if 'username' not in session:
        # Store the intended URL to redirect after login
        session['next_url'] = url_for('edit_group', group_id=group_id)
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


@app.route('/group_retrospective/<int:group_id>', methods=['GET'])
def group_retrospective(group_id):
    
    if 'username' not in session:
        # Store the intended URL to redirect after login
        session['next_url'] = url_for('group_retrospective', group_id=group_id)
        return redirect(url_for('homepage'))
    
    # Retrieve the currently logged-in user
    username = session.get("username")
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify({"error": "User not found."}), 400

    # Get the email of the current user
    current_user_email = user.email

    # Log the attempt
    log(current_user_email, f'Attempting to retrospective in group {group_id}')
    
    # Check if the user is a member of the group
    group_membership = GroupMember.query.filter_by(user_id=user.id, group_id=group_id).first()
    if not group_membership:
        abort(403)  # Forbidden

    # Fetch group by id
    group = Group.query.get(group_id)

    # Check that group exists
    if not group:
        flash("Group not found.", "error")
        return redirect(url_for('dashboard'))

    # Fetch comments for this group
    group_comments = Comment.query.filter_by(group_id=group.id).all()

    return render_template('group_retrospective.html', username=session['username'], group=group, group_comments=group_comments)



    
@app.route('/add_comment', methods=['POST'])
def add_comment():
    if 'username' not in session:
        flash("Please login first.")
        return redirect(url_for('homepage'))

    # Assume you have a Comment model with fields 'user_id', 'group_id', 'text', and 'date'
    # Also, check that user is member of the group where he tries to add a comment.
    current_user = User.query.filter_by(username=session['username']).first()
    group_id = request.form.get('group_id')
    group_membership = GroupMember.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    
    if not group_membership:
        flash("You are not a member of this group.", "error")
        return redirect(url_for('dashboard'))

    comment_text = request.form.get('comment')
    if not comment_text:
        flash("Comment cannot be empty.", "error")
        return redirect(url_for("group_retrospective", group_id=group_id))

    comment = Comment(user_id=current_user.id, group_id=group_id, text=comment_text, date=datetime.datetime.now())
    db.session.add(comment)
    db.session.commit()

    return redirect(url_for("group_retrospective", group_id=group_id))


@app.route('/remove_comment', methods=['POST'])
def remove_comment():
    if 'username' not in session:
        return jsonify({ 'error': "Please login first.", 'category': "error" }), 400

    current_user = User.query.filter_by(username=session['username']).first()

    data = request.get_json()
    comment_id = data.get('comment_id')

    comment = Comment.query.filter_by(id=comment_id).first()

    if not comment:
        return jsonify({ 'error': "This comment does not exist.", 'category': "error" }), 400

    if comment.user_id != current_user.id:
        return jsonify({ 'error': "You cannot delete someone else's comment.", 'category': "error" }), 400

    db.session.delete(comment)
    db.session.commit()

    return jsonify({ 'message': "Your comment has been removed.", 'category': "success" }), 200


@app.route('/group_tasks/<int:group_id>')
def group_tasks(group_id):
    
    if 'username' not in session:
        # Store the intended URL to redirect after login
        session['next_url'] = url_for('group_tasks', group_id=group_id)
        return redirect(url_for('homepage'))
    
    current_user = User.query.filter_by(username=session['username']).first()
    
    if current_user is None:
        return "User not found.", 400

    # Get the email of the current user
    current_user_email = current_user.email
    
    log(current_user_email, f'Attempting to group_tasks in group {group_id}')
    
    new_group = request.args.get('new_group', default = False, type = bool)
    if new_group:
        flash("New group created successfully.", "success")

    group = Group.query.get(group_id)
    if group is None:
        # log the error
        return "Group not found.", 400

    group_membership = GroupMember.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not group_membership:
        # log the error
        return "You are not a member of this group.", 400

    return render_template('group_tasks.html', group=group, username=session['username'])


@app.route('/add_task', methods=['POST'])
def add_task():
    if 'username' not in session:
        return jsonify({"error": "You must be logged in to perform this action."}), 401

    current_user = User.query.filter_by(username=session['username']).first()
    if current_user is None:
        return jsonify({"error": "User not found."}), 400

    data = request.get_json()
    task_content = data.get('task')
    group_id = data.get('group_id')
    username = data.get('user')  # get username from request data

    user = User.query.filter_by(username=username).first()  # query User table to get User object
    if user is None:
        return jsonify({"error": "User not found."}), 400


    group = Group.query.get(group_id)
    if group is None:
        return jsonify({"error": "Group not found."}), 400

    # verify that both the current user and the selected user are members of the group
    current_user_membership = GroupMember.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    selected_user_membership = GroupMember.query.filter_by(user_id=user.id, group_id=group_id).first()
    if not current_user_membership or not selected_user_membership:
        return jsonify({"error": "You and the selected user must be members of this group."}), 400

    try:
        task = Task(task=task_content, group_id=group_id, user_id=user.id)  # assign task to selected user
        db.session.add(task)
        db.session.commit()

        return jsonify({"message": "Task added successfully.", "task": task_content, "task_id": task.id}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/get_group_users', methods=['POST'])
def get_group_users():
    if 'username' not in session:
        return jsonify({"error": "You must be logged in to perform this action."}), 401

    current_user = User.query.filter_by(username=session['username']).first()
    if current_user is None:
        return jsonify({"error": "User not found."}), 400

    data = request.get_json()
    group_id = data.get('group_id')

    group = Group.query.get(group_id)
    if group is None:
        return jsonify({"error": "Group not found."}), 400

    group_membership = GroupMember.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not group_membership:
        return jsonify({"error": "You are not a member of this group."}), 400

    try:
        group_members = GroupMember.query.filter_by(group_id=group_id).all()
        users = [member.user.serialize() for member in group_members]  # serialize the User objects to make them JSON serializable
        return jsonify({"users": users}), 200
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/get_tasks', methods=['POST'])
def get_tasks():
    if 'username' not in session:
        return jsonify({"error": "You must be logged in to perform this action."}), 401

    current_user = User.query.filter_by(username=session['username']).first()
    if current_user is None:
        return jsonify({"error": "User not found."}), 400

    data = request.get_json()
    group_id = data.get('group_id')

    group = Group.query.get(group_id)
    if group is None:
        return jsonify({"error": "Group not found."}), 400

    group_membership = GroupMember.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not group_membership:
        return jsonify({"error": "You are not a member of this group."}), 400

    try:
        tasks = Task.query.filter_by(group_id=group_id).all()
        tasks_serialized = [{"task": task.task, 
                             "user": task.user.username, 
                             "id": task.id, 
                             "is_member": task.user in [group_member.user for group_member in group.group_members]}
                            for task in tasks]
        return jsonify({"tasks": tasks_serialized}), 200
    except SQLAlchemyError as e:
        return jsonify({"error": str(e)}), 500

    

@app.route('/delete_task', methods=['POST'])
def delete_task():
    if 'username' not in session:
        return jsonify({"error": "You must be logged in to perform this action."}), 401

    current_user = User.query.filter_by(username=session['username']).first()
    if current_user is None:
        return jsonify({"error": "User not found."}), 400

    data = request.get_json()
    task_id = data.get('task_id')

    task = Task.query.get(task_id)
    if task is None:
        return jsonify({"error": "Task not found."}), 400

    # verify the task belongs to the current user or the current user is a member of the group of the task
    if task.user_id != current_user.id and not GroupMember.query.filter_by(user_id=current_user.id, group_id=task.group_id).first():
        return jsonify({"error": "You are not authorized to delete this task."}), 403

    try:
        db.session.delete(task)
        db.session.commit()
        return jsonify({"message": "Task deleted successfully."}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
@app.route("/get_non_member_users_with_tasks", methods=["POST"])
def get_non_member_users_with_tasks():
    data = request.get_json()
    group_id = data.get('group_id')

    # Query for tasks where the user is not a member of the group
    tasks = Task.query.filter_by(group_id=group_id).all()

    non_member_users = []
    for task in tasks:
        user = User.query.get(task.user_id)
        group_member = GroupMember.query.filter_by(user_id=user.id, group_id=group_id).first()
        if group_member is None and user not in non_member_users:
            non_member_users.append(user)

    return jsonify({"non_member_users": [user.serialize() for user in non_member_users]})


@app.route('/rename_group/<int:group_id>', methods=['POST'])
def rename_group(group_id):

    if not request.is_json:
        return jsonify({"error": "Request content type must be application/json."}), 415

    # Check if user is logged in
    if 'username' not in session:
        return jsonify({"error": "You must be logged in to perform this action."}), 401

    current_user = User.query.filter_by(username=session['username']).first()
    if current_user is None:
        return jsonify({"error": "User not found."}), 400

    data = request.get_json()
    new_name = data.get('newGroupName').strip()

    # Check if group with the new name already exists
    existing_group = Group.query.filter_by(name=new_name).first()
    if existing_group:
        return jsonify({"error": "A group with that name already exists."}), 400
    
    group = Group.query.get(group_id)
    if group is None:
        return jsonify({"error": "Group not found."}), 400

    # Verify that the current user is a member of the group
    current_user_membership = GroupMember.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not current_user_membership:
        return jsonify({"error": "You must be a member of this group to rename it."}), 400

    try:
        group.name = new_name
        db.session.commit()

        return jsonify({"message": "Group name updated successfully.", "new_name": new_name}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/send_task_notification', methods=['POST'])
def send_task_notification():
    if 'username' not in session:
        return jsonify({"error": "You must be logged in to perform this action."}), 401

    current_user = User.query.filter_by(username=session['username']).first()
    if current_user is None:
        return jsonify({"error": "User not found."}), 400

    data = request.get_json()
    group_id = data.get('group_id')
    recipient_user_id = data.get('user_id')

    group = Group.query.get(group_id)
    if group is None:
        return jsonify({"error": "Group not found."}), 400

    if recipient_user_id:
        user = User.query.get(recipient_user_id)
        if user is None:
            return jsonify({"error": "Recipient user not found."}), 400
        recipients = [user.email]
        greeting = f"Hello {user.username},"
    else:
        recipients = [gm.user.email for gm in group.group_members]
        greeting = "Hello everyone,"

    tasks = Task.query.filter_by(group_id=group_id).all()

    grouped_tasks = {}

    for t in tasks:
        if t.user.username not in grouped_tasks:
            grouped_tasks[t.user.username] = []
        grouped_tasks[t.user.username].append(t)

    tasks_html = ""
    for user, user_tasks in grouped_tasks.items():
        tasks_html += f'<div class="user-tasks"><h3>Tasks for {user}:</h3><ul>'
        for t in user_tasks:
            tasks_html += f"<li>{t.task}</li>"
        tasks_html += "</ul></div>"

        email_content = f"""
        <html>
            <head>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                    }}
                    .header {{
                        background-color: #4CAF50;
                        color: white;
                        padding: 10px 0;
                        text-align: center;
                    }}
                    .content {{
                        margin: 20px;
                    }}
                    .user-tasks {{
                        margin-top: 10px;
                    }}
                    .user-tasks h3 {{
                        color: #4CAF50;
                    }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>Tasks Summary for the Trip: {group.name}</h2>
                </div>
                <div class="content">
                    <p>{greeting}</p>
                    <p><strong>{current_user.username}</strong> wants to remind you of the following tasks:</p>
                    {tasks_html}
                    <p>Let's ensure everything is ready for our unforgettable adventure! 🚀 Should there be any questions about the tasks, feel free to ask.</p>
                    <p>Cheers to our impending escapade!</p>
                    <p>Warm regards,</p>
                    <p>Safe Travels and Happy Memories!</p>
                </div>
            </body>
        </html>
        """

    ses = client('ses', region_name='eu-north-1')

    try:
        response = ses.send_email(
            Source='no-reply@cham-pay.com',
            Destination={
                'ToAddresses': recipients,
            },
            Message={
                'Subject': {
                    'Data': 'Tasks Summary',
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Html': {
                        'Data': email_content,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        return jsonify({"message": "Notification sent successfully."}), 200

    except Exception as e:
        error_message = f"Error sending notification: {str(e)}"
        log(current_user.username, error_message)  
        return jsonify({"error": str(e)}), 500


@app.route('/set_trip_schedule/<int:group_id>', methods=['POST'])
def set_trip_schedule(group_id):
    if not request.is_json:
        return jsonify({"error": "Request content type must be application/json."}), 415

    # Check if user is logged in
    if 'username' not in session:
        return jsonify({"error": "You must be logged in to perform this action."}), 401

    current_user = User.query.filter_by(username=session['username']).first()
    if current_user is None:
        return jsonify({"error": "User not found."}), 400

    group = Group.query.get(group_id)
    if group is None:
        return jsonify({"error": "Group not found."}), 400

    # Verify that the current user is a member of the group
    current_user_membership = GroupMember.query.filter_by(user_id=current_user.id, group_id=group_id).first()
    if not current_user_membership:
        return jsonify({"error": "You must be a member of this group to set its schedule."}), 400

    data = request.get_json()
    start_date_str = data.get('startDate').split(' ')[0]
    start_time_str = data.get('startDate').split(' ')[1]
    end_date_str = data.get('endDate').split(' ')[0]
    end_time_str = data.get('endDate').split(' ')[1]
    location = data.get('location')

    # Fetch user's timezone from database
    user_timezone = pytz.timezone(current_user.timezone)

    try:
        # Convert string representations into date and time objects
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()

        # Adjust for time format
        try:
            start_time = datetime.datetime.strptime(start_time_str, "%H:%M:%S").time()
        except ValueError:
            start_time = datetime.datetime.strptime(start_time_str, "%H:%M").time()

        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()

        # Adjust for time format
        try:
            end_time = datetime.datetime.strptime(end_time_str, "%H:%M:%S").time()
        except ValueError:
            end_time = datetime.datetime.strptime(end_time_str, "%H:%M").time()

        # Combine the date and time into datetime objects
        local_start_datetime = user_timezone.localize(datetime.datetime.combine(start_date, start_time))
        local_end_datetime = user_timezone.localize(datetime.datetime.combine(end_date, end_time))

        # Convert datetime to UTC
        utc_start_datetime = local_start_datetime.astimezone(pytz.utc)
        utc_end_datetime = local_end_datetime.astimezone(pytz.utc)

        # Update the database
        group.start_datetime = utc_start_datetime
        group.end_datetime = utc_end_datetime
        group.location = location
        db.session.commit()

        return jsonify({"message": "Trip schedule updated successfully."}), 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@app.route('/get_trip_schedule/<int:group_id>', methods=['GET'])
def get_trip_schedule(group_id):
    group = Group.query.get(group_id)
    if group is None:
        return jsonify({"error": "Group not found."}), 400

    # Check if user is logged in
    if 'username' not in session:
        return jsonify({"error": "You must be logged in to view this information."}), 401

    current_user = User.query.filter_by(username=session['username']).first()
    if current_user is None:
        return jsonify({"error": "User not found."}), 400
    
    # Get user's timezone from database
    user_timezone = pytz.timezone(current_user.timezone)

    # Convert UTC datetime to user's timezone
    if group.start_datetime:
        localized_start_datetime = group.start_datetime.astimezone(user_timezone)
        start_date_str = localized_start_datetime.date().isoformat()
        start_time_str = localized_start_datetime.time().isoformat()
    else:
        start_date_str = "N/A"
        start_time_str = "N/A"

    if group.end_datetime:
        localized_end_datetime = group.end_datetime.astimezone(user_timezone)
        end_date_str = localized_end_datetime.date().isoformat()
        end_time_str = localized_end_datetime.time().isoformat()
    else:
        end_date_str = "N/A"
        end_time_str = "N/A"

    # Return group trip schedule details in user's timezone
    return jsonify({
        "startDate": start_date_str + ' ' + start_time_str,
        "endDate": end_date_str + ' ' + end_time_str,
        "location": group.location if group.location else "N/A"  # Ensuring there's no None for location
    }), 200



@app.route('/send_schedule_notification', methods=['POST'])
def send_schedule_notification():
    if 'username' not in session:
        return jsonify({"error": "You must be logged in to perform this action."}), 401

    current_user = User.query.filter_by(username=session['username']).first()
    if current_user is None:
        return jsonify({"error": "User not found."}), 400

    data = request.get_json()
    group_id = data.get('group_id')
    recipient_user_id = data.get('user_id')

    group = Group.query.get(group_id)
    if group is None:
        return jsonify({"error": "Group not found."}), 400

    if recipient_user_id:
        user = User.query.get(recipient_user_id)
        if user is None:
            return jsonify({"error": "Recipient user not found."}), 400
        greeting = f"Hello {user.username},"
        recipients = [user.email]
    else:
        greeting = "Hello everyone,"
        recipients = [gm.user.email for gm in group.group_members]

    # Fetching group details
    group_name = group.name
    start_datetime_utc = group.start_datetime
    end_datetime_utc = group.end_datetime
    location = group.location

    # Building the list of group members' names
    participants_list = [gm.user.username for gm in group.group_members]
    participants_html = ', '.join(participants_list)

    # Generating the data URI for the "Add To Calendar" feature
    start_date_str = start_datetime_utc.strftime('%Y%m%d')
    end_date_str = end_datetime_utc.strftime('%Y%m%d')
    start_time_str = start_datetime_utc.strftime('%H%M%S')
    end_time_str = end_datetime_utc.strftime('%H%M%S')

    # Generating html part according to curr user time zone
    user_timezone = pytz.timezone(current_user.timezone) 
    start_datetime_local = start_datetime_utc.astimezone(user_timezone)
    end_datetime_local = end_datetime_utc.astimezone(user_timezone)


    data_uri = generate_ics_data_uri(group_name, start_date_str, start_time_str, end_date_str, end_time_str, location)

    # Creating the email content based on the template
    email_content = f"""
    <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 0;
                    text-align: center;
                }}
                .content {{
                    margin: 20px;
                }}
                .trip-details {{
                    margin-top: 10px;
                }}
                .trip-details h3 {{
                    color: #4CAF50;
                }}
                ul {{
                    list-style-type: none;
                    padding: 0;
                }}
                li {{
                    margin-bottom: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>Updated Trip Settings for: {group_name}</h2>
            </div>
            <div class="content">
                <p>{greeting},</p>
                <p><strong>{current_user.username}</strong> has made some updates to the trip settings on Champay.</p>
                <div class="trip-details">
                    <h3>New Trip Details:</h3>
                    <ul>
                        <li><strong>Trip Name:</strong> {group_name}</li>
                        <li><strong>Start Date & Time:</strong> {start_datetime_local.strftime('%Y-%m-%d, %H:%M:%S %Z')}</li>
                        <li><strong>End Date & Time:</strong> {end_datetime_local.strftime('%Y-%m-%d, %H:%M:%S %Z')}</li>
                        <li><strong>Location:</strong> {location}</li>
                        <li><strong>Participants:</strong> {participants_html}</li>
                    </ul>
                </div>
                <p>Please review these updates and reach out to <strong>{current_user.username}</strong> or any other trip organizer if you have any questions or concerns. If there are any further changes, you will be notified promptly.</p>
                <p>We look forward to a memorable trip!</p>
                <p>Warm regards,</p>
                <p>Champay Team</p>
                <p></p>
                <p><a download="group_{group_id}_trip_{start_date_str}.ics" href="{data_uri}">Add To Calendar</a></p>
            </div>
        </body>
    </html>
    """

    # ...

    ses = client('ses', region_name='eu-north-1')
        
    email_subject = f'[Champay] Trip Settings Updated for "{group_name}"'
    mime_email = create_mime_email(email_subject, email_content, generate_ics_content(group_name, start_date_str, start_time_str, end_date_str, end_time_str, location), group_id, start_date_str)    

    try:
        response = ses.send_raw_email(
            Source='no-reply@cham-pay.com',
            Destinations=recipients,
            RawMessage={
                'Data': mime_email.as_string(),
            }
        )
        return jsonify({"message": "Schedule notification sent successfully."}), 200

    except Exception as e:
        error_message = f"Error sending schedule notification: {str(e)}"
        log(current_user.username, error_message)
        return jsonify({"error": str(e)}), 500



def generate_ics_data_uri(group_name, start_date, start_time, end_date, end_time, location):
    ics_content = generate_ics_content(group_name, start_date, start_time, end_date, end_time, location)
    encoded_ics_content = base64.b64encode(ics_content.encode()).decode()
    return f"data:text/calendar;base64,{encoded_ics_content}"


def format_time(time_str):
    # Ensure we have a string with length 6, like "150000"
    time_str = str(time_str).zfill(6)

    # Construct formatted time as "15:00:00"
    formatted_time = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:]}"
    
    return formatted_time


def generate_ics_content(group_name, start_date, start_time, end_date, end_time, location):
   # Ensure the time strings are in the right format
    start_time = format_time(start_time)
    end_time = format_time(end_time)

    # Combine and format date and time strings
    start_datetime = datetime.datetime.strptime(f"{start_date} {start_time}", '%Y%m%d %H:%M:%S').strftime('%Y%m%dT%H%M%SZ')
    end_datetime = datetime.datetime.strptime(f"{end_date} {end_time}", '%Y%m%d %H:%M:%S').strftime('%Y%m%dT%H%M%SZ')

    dtstamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    
    ics_content = f"""BEGIN:VCALENDAR\r
VERSION:2.0\r
PRODID:-//Champay//EN\r
METHOD:REQUEST\r
BEGIN:VEVENT\r
UID:{uuid.uuid4()}\r
DTSTART;VALUE=DATE-TIME:{start_datetime}\r
DTEND;VALUE=DATE-TIME:{end_datetime}\r
DTSTAMP;VALUE=DATE-TIME:{dtstamp}\r
SUMMARY:{group_name}\r
LOCATION:{location}\r
ORGANIZER;CN="Champay Team":MAILTO:no-reply@cham-pay.com\r
ATTENDEE;CN="Recipient Name":MAILTO:ayael01@gmail.com\r
END:VEVENT\r
END:VCALENDAR"""
    return ics_content



def create_mime_email(subject, body_html, ics_content, group_id, start_date):
    msg = MIMEMultipart()
    msg['Subject'] = subject

    # Attach the HTML body
    body = MIMEText(body_html, 'html')
    msg.attach(body)

    # Generate the custom filename
    ics_filename = f"group_{group_id}_trip_{start_date}.ics"

    # Attach the ICS content with the custom filename
    calendar_attachment = MIMEText(ics_content, 'calendar;method=REQUEST')
    calendar_attachment.add_header('Content-Disposition', 'attachment', filename=ics_filename)
    msg.attach(calendar_attachment)

    return msg



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

