from flask import Flask, request, redirect, render_template, url_for,session,flash,send_from_directory, abort,session 
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback_secret_key')
app.config['UPLOADED_PDFS_DEST'] = 'static/pdfs'
ALLOWED_EXTENSIONS = {'pdf'}
db = SQLAlchemy(app)

# Define the Section model
class Section(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now, nullable=False)
    description = db.Column(db.String(500), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    books = db.relationship('Book', back_populates='section')
    issues = db.relationship('Issue', backref='section', lazy='dynamic')


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    mobile = db.Column(db.String(10), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    sections = db.relationship('Section', backref='librarian', lazy='dynamic')
    issues = db.relationship('Issue', foreign_keys="[Issue.user_id]", backref='user', lazy='dynamic')
    librarian_actions = db.relationship('Issue', foreign_keys="[Issue.librarian_id]", backref='librarian', lazy='dynamic')

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    pages = db.Column(db.Integer)  # Add this line for the number of pages
    pdf_file = db.Column(db.String(200))
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    section = db.relationship('Section', back_populates='books')
    issues = db.relationship('Issue', backref='book', lazy='dynamic')

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    librarian_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Assuming librarians are also users

    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    date_issued = db.Column(db.DateTime, default=datetime.now, nullable=False)
    due_date = db.Column(db.DateTime, nullable=True)
    # return_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='issued')


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

@app.route('/librarian_dashboard', methods=['GET', 'POST'])
def librarian_dashboard():
    if 'librarian_id' not in session:
        return redirect(url_for('librarian_login'))

    librarian_id = session['librarian_id']
    query = request.args.get('query')  # Get the search query from URL parameters for GET request

    if query:
        # Filter sections by title containing the search query
        sections = Section.query.filter(Section.user_id == librarian_id, Section.title.contains(query)).all()
    else:
        sections = Section.query.filter_by(user_id=librarian_id).all()

    # Within your librarian_dashboard route
    return render_template('librarian_dashboard.html', sections=sections)




@app.route('/librarian_login', methods=['GET', 'POST'])
def librarian_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['pwd']
        # Check the role of the user when logging in
        librarian = User.query.filter_by(username=username, role='librarian').first()

        if librarian and librarian.password == password:
            session['librarian_id'] = librarian.id
            return redirect(url_for('librarian_dashboard'))
        else:
            flash('Invalid username or password, or wrong role', 'danger')
            return render_template('librarian_login.html')

    # If it's a GET request, just render the login page
    return render_template('librarian_login.html')



@app.route('/logout')
def logout():
    session.clear()  # This will remove everything from the session
    return redirect(url_for('index'))


@app.route('/user_login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['pwd']
        # Check the role of the user when logging in
        user = User.query.filter_by(username=username, role='user').first()

        if user and user.password == password:
            session['user_id'] = user.id
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password, or wrong role', 'danger')
            return render_template('user_login.html')

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

@app.route('/user_dashboard', methods=['GET'])
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    query = request.args.get('query')  # Get the search query from URL parameters for GET request

    # Retrieve the IDs of books the user has already requested or has been issued
    user_issues = Issue.query.filter_by(user_id=user_id).all()
    requested_book_ids = [issue.book_id for issue in user_issues if issue.status == 'requested']
    issued_book_ids = [issue.book_id for issue in user_issues if issue.status == 'issued']

    # Filter books by search query if provided
    if query:
        books = Book.query.filter(Book.title.contains(query)).all()
    else:
        books = Book.query.all()

    # Pass the list of requested and issued book IDs and all books to the template
    return render_template(
        'user_dashboard.html',
        books=books,
        requested_book_ids=requested_book_ids,
        issued_book_ids=issued_book_ids
    )




@app.route('/user_mybooks', methods=['GET'])
def user_mybooks():
    if 'user_id' not in session:
        flash('Please log in to view your books.', 'warning')
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    issued_books = Issue.query.filter_by(user_id=user_id, status='issued').all()

    return render_template('user_mybooks.html', issued_books=issued_books)


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

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Add this route in your app.py
@app.route('/section/<int:section_id>/add_book', methods=['GET', 'POST'])
def add_book(section_id):
    if 'librarian_id' not in session:
        return redirect(url_for('librarian_login'))

    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        pages = request.form.get('pages', type=int)  # Get pages as an integer
        file = request.files['pdf_file']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOADED_PDFS_DEST'], filename))

            new_book = Book(title=title, author=author, pages=pages, section_id=section_id, pdf_file=filename)
            db.session.add(new_book)
            try:
                db.session.commit()
                flash('Book added successfully.', 'success')
            except Exception as e:
                db.session.rollback()
                flash('Error adding book: ' + str(e), 'danger')

            return redirect(url_for('view_books', section_id=section_id))
        else:
            flash('Invalid file type. Only PDFs are allowed.', 'danger')
        new_book = Book(title=title, author=author,pages=pages, section_id=section_id)
        db.session.add(new_book)
        try:
            db.session.commit()
            return redirect(url_for('view_books', section_id=section_id))
        except Exception as e:
            db.session.rollback()
            return str(e), 500
    else:
        return render_template('add_book.html', section_id=section_id)




@app.route('/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    if 'librarian_id' not in session:
        flash('Please log in as a librarian to delete books.', 'warning')
        return redirect(url_for('librarian_login'))
    
    book_to_delete = Book.query.get_or_404(book_id)
    
    # Check if there are any issues associated with the book
    issues = Issue.query.filter_by(book_id=book_id).all()
    
    if issues:
        # Option 1: Prevent deletion and inform the user
        # flash('This book cannot be deleted because it has associated issues.', 'danger')
        # return redirect(url_for('librarian_dashboard'))
    
        # Option 2: Cascade delete (Dangerous: you will lose the issues data)
        for issue in issues:
            db.session.delete(issue)
        db.session.delete(book_to_delete)

        # Option 3: Reassign or update the issues before deleting the book
        # for issue in issues:
        #     issue.book_id = None  # or some other logic to handle the orphaned issue
        #     db.session.commit()

    else:
        # If there are no associated issues, it's safe to delete the book
        db.session.delete(book_to_delete)
    
    try:
        db.session.commit()
        flash('Book deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(str(e), 'danger')  # This will display the actual error to the user.
    
    return redirect(url_for('librarian_dashboard'))




@app.route('/sections/<int:section_id>/books', methods=['GET', 'POST'])
def view_books(section_id):
    if 'librarian_id' not in session:
        return redirect(url_for('librarian_login'))

    section = Section.query.get_or_404(section_id)
    query = request.args.get('query')
    user_id = request.args.get('user_id')
    book_id = request.args.get('book_id')
    
    selected_issue = None
    if user_id and book_id:
        try:
            user_id = int(user_id)
            book_id = int(book_id)
            selected_issue = Issue.query.filter_by(book_id=book_id, user_id=user_id, status='issued').first()
        except ValueError:
            flash('Invalid user or book selection.', 'warning')

    if query:
        books = Book.query.filter(Book.section_id == section_id, Book.title.contains(query)).all()
    else:
        books = Book.query.filter_by(section_id=section_id).all()

    return render_template('section_books.html', section=section, books=books, selected_issue=selected_issue)


@app.route('/books/pdf/<int:book_id>')
def serve_pdf(book_id):
    if 'user_id' not in session:
        # User is not logged in
        abort(403)

    book = Book.query.get(book_id)
    issue = Issue.query.filter_by(book_id=book.id, user_id=session['user_id'], status='issued').first()

    if not issue:
        # The book hasn't been issued to the user
        abort(403)

    # Assuming your PDFs are stored in 'static/pdfs/' and 'pdf_filename' contains the filename of the PDF
    pdf_url = url_for('static', filename=f'pdfs/{book.pdf_file}')
    return redirect(pdf_url)

@app.route('/issue_book/<int:book_id>', methods=['GET', 'POST'])
def issue_book(book_id):
    if 'librarian_id' not in session:
        return redirect(url_for('librarian_login'))

    book = Book.query.get_or_404(book_id)
    if request.method == 'POST':
        librarian_id = session.get('librarian_id')
        user_id = request.form.get('user_id')

    # Create or update the Issue record
        issue = Issue(book_id=book_id, user_id=user_id, librarian_id=librarian_id, status='issued')
        db.session.add(issue)
        db.session.commit()
        return redirect(url_for('view_books', section_id=book.section_id))
    else:
        # For a GET request, render the confirmation page
        return render_template('book_issue.html', book=book, book_id=book_id, section_id=book.section_id)


    
@app.route('/return_book/<int:issue_id>', methods=['POST'])
def return_book(issue_id):
    # Get the issue by its ID
    issue = Issue.query.get_or_404(issue_id)

    # Check if a librarian is logged in
    if 'librarian_id' in session:
        # Librarian logic here
        # A librarian can process the return regardless of the user who issued the book
        issue.status = 'returned'
        issue.return_date = datetime.now()
        db.session.commit()
        flash('Book return processed.', 'success')
        # Redirect to librarian's view, which shows all books
        return redirect(url_for('librarian_dashboard'))

    # If not a librarian, check for a logged in user
    elif 'user_id' in session and session['user_id'] == issue.user_id:
        # User logic here
        # A user can only return a book they have issued
        issue.status = 'returned'
        issue.return_date = datetime.now()
        db.session.delete(issue)

        db.session.commit()
        flash('Book returned successfully.', 'success')
        # Redirect to the user's view of their books
        return redirect(url_for('user_mybooks'))

    else:
        # If no valid session is found, redirect to the login page with a warning message
        flash('You are not authorized to perform this action.', 'warning')
        return redirect(url_for('login'))  # Assuming 'login' is the route for the login page


@app.route('/issue_books_to_user/<int:user_id>', methods=['GET', 'POST'])
def issue_books_to_user(user_id):
    # Display form to select books and issue them to the user
    if request.method == 'POST':
        book_ids = request.form.getlist('book_ids')  # Expected a list of book IDs from the form
        for book_id in book_ids:
            new_issue = Issue(user_id=user_id, book_id=book_id)
            db.session.add(new_issue)
        db.session.commit()
        return redirect(url_for('some_route_after_issuing'))  # Redirect as appropriate
    else:
        books = Book.query.all()  # Or filter as necessary
        return render_template('issue_books_to_user.html', books=books, user_id=user_id)

@app.route('/revoke_book_access/<int:book_id>', methods=['POST'])
def revoke_book_access(book_id):
    issue = Issue.query.filter_by(book_id=book_id).first()
    if issue:
        issue.revoked = True  # Assuming there is a 'revoked' field in the Issue model
        db.session.commit()
    return redirect(url_for('some_route_after_revoking'))  # Redirect as appropriate

@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    if request.method == 'POST':
        book.title = request.form['title']
        book.author = request.form['author']
        book.content = request.form['content']
        # Update other fields as necessary
        db.session.commit()
        return redirect(url_for('view_books', section_id=book.section_id))
    return render_template('edit_book.html', book=book)

@app.route('/assign_book/<int:book_id>', methods=['POST'])
def assign_book(book_id):
    book = Book.query.get_or_404(book_id)
    book.section_id = request.form['section_id']  # New section ID from the form
    db.session.commit()
    return redirect(url_for('view_books', section_id=book.section_id))

@app.route('/monitor_books', methods=['GET'])
def monitor_books():
    if 'librarian_id' not in session:
        flash('You need to login as a librarian!', 'warning')
        return redirect(url_for('librarian_login'))

    # Fetch only requests with 'requested' status
    requested_issues = Issue.query.filter_by(status='requested').all()
    return render_template('monitor_books.html', issues=requested_issues)



@app.route('/section/<int:section_id>/add_book', methods=['GET'])
def add_book_form(section_id):
    if 'librarian_id' not in session:
        return redirect(url_for('librarian_login'))
    
    # Assuming you pass necessary data to your template, if any.
    return render_template('add_book.html', section_id=section_id)

@app.route('/request_book/<int:book_id>', methods=['POST'])
def request_book(book_id):
    if 'user_id' not in session:
        flash('You need to log in first!', 'warning')
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    current_requests_count = Issue.query.filter_by(user_id=user_id, status='requested').count()
    if current_requests_count >= 5:
        flash('You cannot request more than 5 e-books.', 'warning')
        return redirect(url_for('user_dashboard'))  # Redirect them back to the dashboard

    book = Book.query.get_or_404(book_id)  # Make sure the book exists
    
    # Since each book belongs to a section, you can use the book's section_id
    section_id = book.section_id  # Assuming that each book has a section_id

    # Check if the book has already been requested or issued to prevent duplicate requests
    existing_issue = Issue.query.filter_by(book_id=book_id, user_id=user_id).first()
    if existing_issue:
        flash('You have already requested or issued this book.', 'info')
        return redirect(url_for('user_dashboard'))

    # Create a new issue with the necessary section_id
    new_issue = Issue(user_id=user_id, book_id=book_id, section_id=section_id, status='requested', date_issued=datetime.now())
    db.session.add(new_issue)
    try:
        db.session.commit()
        flash('Your request has been sent to the librarian.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while processing your request. Please try again.', 'danger')

    return redirect(url_for('user_dashboard'))



@app.route('/view_requests', methods=['GET'])
def view_requests():
    if 'librarian_id' not in session:
        flash('You need to login as a librarian!', 'warning')
        return redirect(url_for('librarian_login'))

    # Fetch only requests with 'requested' status
    requested_issues = Issue.query.filter_by(status='requested').all()
    return render_template('view_requests.html', issues=requested_issues)

@app.route('/approve_request/<int:issue_id>', methods=['POST'])
def approve_request(issue_id):
    if 'librarian_id' not in session:
        flash('You must be logged in as a librarian to approve requests.', 'danger')
        return redirect(url_for('librarian_login'))
    
    issue = Issue.query.get_or_404(issue_id)
    issue.status = 'issued'
    # Set date_issued and optionally due_date if you want
    issue.date_issued = datetime.now()
    issue.due_date = datetime.now() + timedelta(days=14)  # e.g., 2 weeks from now
    db.session.commit()
    flash('Book issue approved.', 'success')
    return redirect(url_for('librarian_dashboard'))

@app.route('/revoke_request/<int:issue_id>', methods=['POST'])
def revoke_request(issue_id):
    if 'librarian_id' not in session:
        return redirect(url_for('librarian_login'))
    
    issue = Issue.query.get_or_404(issue_id)
    issue.status = 'revoked'  # Update status to 'revoked'
    db.session.commit()
    # Add logic for what should happen when a book is revoked
    flash('Book access revoked.', 'success')
    return redirect(url_for('view_requests'))

from datetime import datetime, timedelta

@app.route('/issue_book_to_user/<int:issue_id>', methods=['POST'])
def issue_book_to_user(issue_id):
    # Ensure the librarian is logged in
    if 'librarian_id' not in session:
        flash('Please log in as a librarian.', 'warning')
        return redirect(url_for('librarian_login'))

    # Find the issue record and update it
    issue = Issue.query.get_or_404(issue_id)
    issue.status = 'issued'
    issue.date_issued = datetime.utcnow()
    issue.due_date = issue.date_issued + timedelta(days=7)  # Set the due date to 7 days from today
    db.session.commit()
    flash('Book issued successfully.', 'success')

    return redirect(url_for('monitor_books'))


def revoke_overdue_books():
    overdue_issues = Issue.query.filter(Issue.due_date < datetime.now(), Issue.status == 'issued').all()
    for issue in overdue_issues:
        issue.status = 'overdue'
    db.session.commit()

scheduler = BackgroundScheduler()
scheduler.add_job(func=revoke_overdue_books, trigger='interval', days=1)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown(wait=False))




# Create the database tables
with app.app_context():
    db.create_all()
    add_librarians()  # Call the function to add librarians

if __name__ == '__main__':
    app.run(debug=True)
