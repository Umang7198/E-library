
import os
from migrations.models import User, Section, Book, Issue  # Adjust the import path according to your project structure
import migrations.routes as routes
from migrations.config import app, db
from flask_migrate import Migrate
migrate = Migrate(app, db)



def add_librarians():
# Predefined librarian data
    librarians = [
        {"name": "admin", "email": "admin@gmail.com", "mobile": "1234567890", "username": "admin", "password": "Admin@123"},
        # Add more librarians as needed
    ]

    for librarian in librarians:
        if not User.query.filter_by(username=librarian['username']).first():
            new_librarian = User(
                name=librarian['name'],
                email=librarian['email'],
                mobile=librarian['mobile'],
                username=librarian['username'],
                password=librarian['password'],
                role='librarian'  # Assuming you've added a 'role' field to your User model
            )
            db.session.add(new_librarian)
    
    try:
        db.session.commit()
        print("Librarians added to the database.")
    except Exception as e:
        db.session.rollback()
        print(f"Error adding librarians: {e}")
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        add_librarians()
    app.run(host='0.0.0.0')
