# config.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
app = Flask(__name__, template_folder="../templates",static_folder="../static")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOADED_PDFS_DEST'] = 'static/pdfs'
if not os.path.exists(app.config['UPLOADED_PDFS_DEST']):
    os.makedirs(app.config['UPLOADED_PDFS_DEST'])
app.config['SECRET_KEY'] = 'secret'

db = SQLAlchemy(app)
