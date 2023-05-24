from app import app, db
from app import GroupMember

with app.app_context():
    # Create group members
    group_member1 = GroupMember(user_id=2, group_id=2)
    
    # Add group members to the session
    db.session.add(group_member1)

    # Commit the changes to the database
    db.session.commit()

print("Group members added successfully!")
