from flask import Flask, request, redirect, render_template, url_for,session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback_secret_key')

db = SQLAlchemy(app)

# Define the Section model
class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    books = db.relationship('Book', back_populates='section')


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(10), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    sections = db.relationship('Section', backref='librarian', lazy='dynamic')

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    # content = db.Column(db.Text, nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    section = db.relationship('Section', back_populates='books')
    # user_issued_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # ForeignKey to user table

@app.route('/')
def index():
    return render_template('index.html')

# Flask route for the main page that shows the form
@app.route('/add-section-form')
def add_section_form():
    if 'librarian_id' not in session:
        return redirect(url_for('librarian_login'))
    return render_template('add_section.html')

@app.route('/add-section', methods=['POST'])
def add_section():
    if 'librarian_id' in session:
        title = request.form.get('title')
        description = request.form.get('description')
        user_id = session['librarian_id']
        
        new_section = Section(title=title, description=description, date_created=datetime.utcnow(), user_id=user_id)
        db.session.add(new_section)
        db.session.commit()

        return redirect(url_for('librarian_dashboard'))
    return redirect(url_for('librarian_login')), 403

@app.route('/librarian_dashboard')
def librarian_dashboard():
    if 'librarian_id' in session:
        librarian_id = session['librarian_id']
        sections = Section.query.filter_by(user_id=librarian_id).all()
        return render_template('librarian_dashboard.html', sections=sections)
    return redirect(url_for('librarian_login')), 403


@app.route('/librarian_login', methods=['GET', 'POST'])
def librarian_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('pwd')
        librarian = User.query.filter_by(username=username, role='librarian').first()

        if librarian and librarian.password == password:
            session['librarian_id'] = librarian.id
            return redirect(url_for('librarian_dashboard'))
        else:
            # Handle login failure here
            pass
    return render_template('librarian_login.html')


@app.route('/logout')
def logout():
    session.pop('librarian_id', None)
    return redirect(url_for('index'))


@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['pwd']
        # Here you should add your logic to verify the username and password
        # For simplicity, this example will just redirect to another page
        return redirect(url_for('user_dashboard'))
    # If it's a GET request, just render the login page
    return render_template('user_login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        username = request.form.get('username')
        password = request.form.get('password')

        new_user = User(name=name, email=email, mobile=mobile, username=username, password=password)
        db.session.add(new_user)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            # Handle error, e.g., username or email already exists
            return "Error: " + str(e)  # For simplicity, just returning the error message

        # Redirect after successful registration
        return redirect(url_for('user_login'))
    return render_template('register.html')


def add_librarians():
    # Predefined librarian data
    librarians = [
        {"name": "umang", "email": "umang@gmail.com", "mobile": "1234567890", "username": "umang", "password": "umang"},
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
        
@app.route('/delete_section/<int:section_id>', methods=['POST'])
def delete_section(section_id):
    if 'librarian_id' in session:
        section = Section.query.get_or_404(section_id)
        if section.librarian.id == session['librarian_id']:
            db.session.delete(section)
            db.session.commit()
    return redirect(url_for('librarian_dashboard'))


@app.route('/section/<int:section_id>/add_book')
def add_book_form(section_id):
    # Your logic here to display the form
    return render_template('add_book.html', section_id=section_id)

# Add this route in your app.py
@app.route('/add_book', methods=['POST'])
def add_book():
    if 'librarian_id' not in session:
        return redirect(url_for('librarian_login'))

    title = request.form['title']
    author = request.form['author']
    # content = request.form['content']
    section_id = request.form['section_id']

    new_book = Book(title=title, author=author,  section_id=section_id)
    
    db.session.add(new_book)
    try:
        db.session.commit()
        return redirect(url_for('view_books', section_id=section_id))  # Ensure this redirect is in place
    except Exception as e:
        db.session.rollback()
        return str(e), 500  # Return an error if something goes wrong



@app.route('/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    if 'librarian_id' not in session:
        return redirect(url_for('librarian_login'))

    book_to_delete = Book.query.get_or_404(book_id)
    db.session.delete(book_to_delete)
    db.session.commit()

    return redirect(url_for('view_books', section_id=book_to_delete.section_id))



@app.route('/sections/<int:section_id>/books')
def view_books(section_id):
    if 'librarian_id' not in session:
        return redirect(url_for('librarian_login'))

    section = Section.query.get_or_404(section_id)
    books = Book.query.filter_by(section_id=section_id).all()
    return render_template('section_books.html', section=section, books=books)

# Create the database tables
with app.app_context():
    db.create_all()
    add_librarians()  # Call the function to add librarians

if __name__ == '__main__':
    app.run(debug=True)
