# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from migrations.config import db

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
    pdf_file = db.Column(db.String(200))
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    section = db.relationship('Section', back_populates='books')
    issues = db.relationship('Issue', backref='book', lazy='dynamic')

class Issue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    librarian_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  
    section_id = db.Column(db.Integer, db.ForeignKey('section.id'), nullable=False)
    date_issued = db.Column(db.DateTime, default=datetime.now, nullable=False)
    due_date = db.Column(db.DateTime, nullable=True)
    revoked = db.Column(db.Boolean, default=False, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='issued')
