from app import app, Group, db
from uuid import uuid4

def update_existing_groups():
    with app.app_context():  # Adding the app context
        groups = Group.query.all()

        for group in groups:
            if group.ics_uid is None:
                group.ics_uid = str(uuid4())
                group.ics_sequence = 0
                group.is_scheduled = False

        db.session.commit()

if __name__ == '__main__':
    update_existing_groups()
