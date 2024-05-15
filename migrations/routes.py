from flask import Flask, request, redirect, render_template, url_for, session,abort
from apscheduler.schedulers.background import BackgroundScheduler
import atexit,os
from migrations.config import app,db
from migrations.models import User, Section, Book, Issue
from datetime import datetime,timedelta

ALLOWED_EXTENSIONS = {'pdf'}

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
        
        new_section = Section(title=title, description=description, date_created=datetime.now(), user_id=user_id)
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
        password = request.form['password']
        # Check the role of the user when logging in
        librarian = User.query.filter_by(username=username, role='librarian').first()

        if librarian and librarian.password == password:
            session['librarian_id'] = librarian.id
            return redirect(url_for('librarian_dashboard'))
        else:
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
        password = request.form['password']
        # Check the role of the user when logging in
        user = User.query.filter_by(username=username, role='user').first()

        if user and user.password == password:
            session['user_id'] = user.id
            return redirect(url_for('user_dashboard'))
        else:
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
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    issued_books = Issue.query.filter_by(user_id=user_id, status='issued').all()
    current_time = datetime.now()

    return render_template('user_mybooks.html', issued_books=issued_books,current_time=current_time)



        
@app.route('/delete_section/<int:section_id>', methods=['POST'])
def delete_section(section_id):
    if 'librarian_id' in session:
        section = Section.query.get_or_404(section_id)
        if section.books:
            return redirect(url_for('librarian_dashboard'))
        db.session.delete(section)
        db.session.commit()
    return redirect(url_for('librarian_dashboard'))

@app.route('/edit_section/<int:section_id>', methods=['GET'])
def edit_section_form(section_id):
    section = Section.query.get_or_404(section_id)
    return render_template('edit_section.html', section=section)

# Route to process the form submission and update the section
@app.route('/update_section/<int:section_id>', methods=['POST'])
def update_section(section_id):
    section = Section.query.get_or_404(section_id)
    section.title = request.form['title']
    section.description = request.form['description']
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
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
        file = request.files['pdf_file']

        if file and allowed_file(file.filename):
            file.save(os.path.join(app.config['UPLOADED_PDFS_DEST'], file.filename))

            new_book = Book(title=title, author=author,  section_id=section_id, pdf_file=file.filename)
            db.session.add(new_book)
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()

            return redirect(url_for('view_books', section_id=section_id))
        
     
    else:
        return render_template('add_book.html', section_id=section_id)




@app.route('/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    if 'librarian_id' not in session:
        return redirect(url_for('librarian_login'))
    
    book_to_delete = Book.query.get_or_404(book_id)
    
    # Check if there are any issues associated with the book
    issues = Issue.query.filter_by(book_id=book_id).all()
    
    if issues:
        #Cascade delete 
        for issue in issues:
            db.session.delete(issue)

    else:
        # If there are no associated issues, it's safe to delete the book
        db.session.delete(book_to_delete)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
    
    return redirect(url_for('view_books',section_id=book_to_delete.section_id))




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
            pass
        
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
    issue = Issue.query.filter_by(
        book_id=book.id, 
        user_id=session['user_id'], 
        status='issued'
    ).first()

    if not issue or issue.revoked or datetime.now() > issue.due_date:
        # Access is revoked either explicitly or due to overdue
        abort(403)

    # Serve the PDF as before
    pdf_url = url_for('static', filename=f'pdfs/{book.pdf_file}')
    return redirect(pdf_url)

    
@app.route('/return_book/<int:issue_id>', methods=['POST'])
def return_book(issue_id):
    # Get the issue by its ID
    issue = Issue.query.get_or_404(issue_id)
    
    # If not a librarian, check for a logged in user
    if 'user_id' in session and session['user_id'] == issue.user_id:
        # User logic here
        # A user can only return a book they have issued
        issue.status = 'returned'
        issue.return_date = datetime.now()
        db.session.delete(issue)

        db.session.commit()
        # Redirect to the user's view of their books
        return redirect(url_for('user_mybooks'))

    else:
        # If no valid session is found, redirect to the login page with a warning message
        return redirect(url_for('login'))  # Assuming 'login' is the route for the login page


@app.route('/monitor_books', methods=['GET'])
def monitor_books():
    if 'librarian_id' not in session:
        return redirect(url_for('librarian_login'))

    # Fetch only requests with 'requested' status
    requested_issues = Issue.query.filter_by(status='requested').all()
    return render_template('monitor_books.html', issues=requested_issues)


@app.route('/request_book/<int:book_id>', methods=['POST'])
def request_book(book_id):
    if 'user_id' not in session:
        return redirect(url_for('user_login'))

    user_id = session['user_id']
    current_requests_count = Issue.query.filter_by(user_id=user_id, status='requested').count()
    if current_requests_count >= 5:
        return redirect(url_for('user_dashboard'))  # Redirect them back to the dashboard

    book = Book.query.get_or_404(book_id)  # Make sure the book exists
    
    # Since each book belongs to a section, you can use the book's section_id
    section_id = book.section_id  # Assuming that each book has a section_id

    # Check if the book has already been requested or issued to prevent duplicate requests
    existing_issue = Issue.query.filter_by(book_id=book_id, user_id=user_id).first()
    if existing_issue:
        return redirect(url_for('user_dashboard'))

    # Create a new issue with the necessary section_id
    new_issue = Issue(user_id=user_id, book_id=book_id, section_id=section_id, status='requested', date_issued=datetime.now())
    db.session.add(new_issue)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()

    return redirect(url_for('user_dashboard'))


@app.route('/issue_book_to_user/<int:issue_id>', methods=['POST'])
def issue_book_to_user(issue_id):
    # Ensure the librarian is logged in
    if 'librarian_id' not in session:
        return redirect(url_for('librarian_login'))

    # Find the issue record and update it
    issue = Issue.query.get_or_404(issue_id)
    issue.status = 'issued'
    issue.date_issued = datetime.now()
    issue.librarian_id = session['librarian_id']  # Set the librarian who issued the book
    issue.due_date = issue.date_issued + timedelta(days=7)  # Set the due date to 7 days from today
    db.session.commit()

    return redirect(url_for('monitor_books'))


def revoke_overdue_books():
    overdue_issues = Issue.query.filter(
        Issue.due_date < datetime.now(), 
        Issue.status == 'issued',
        Issue.revoked == False  # Make sure we don't process already revoked issues
    ).all()
    
    for issue in overdue_issues:
        issue.revoked = True
    db.session.commit()

# Initialize the scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(func=revoke_overdue_books, trigger='interval', days=1)
scheduler.start()

# Shut down the scheduler when exiting the app
atexit.register(lambda: scheduler.shutdown(wait=False))

