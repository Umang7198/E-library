from migrations.config import app, db
from migrations.models import User, Section, Book, Issue  # Ensure you import all your models
from app import add_librarians
with app.app_context():
    db.create_all()
    add_librarians()
    print("Database tables created")
