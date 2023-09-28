from app import app, db
from werkzeug.security import generate_password_hash
from app import User

# Generate a hashed password
hashed_password = generate_password_hash('123456', method='sha256')

with app.app_context():   # Create an application context
    # Create a new user
    new_user = User(username='ExtraGm', email='extragm7@gmail.com', password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

print("User ExtraGm added successfully!")
