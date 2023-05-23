from app import app, db
from app import Group

with app.app_context():   
    # Create new groups
    group1 = Group(name='On the fire at Ran house')
    group2 = Group(name='Family barbecue at Itzik house')
    group3 = Group(name='Happy Hour in Tel Aviv')
    
    # Add new groups to the session
    db.session.add(group1)
    db.session.add(group2)
    db.session.add(group3)
    
    # Commit the session to the database
    db.session.commit()

print("Groups added successfully!")