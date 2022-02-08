from datetime import datetime
import os
import json
import requests
import flask_login

from flask import Flask, request, render_template, url_for, redirect, flash, session
from flask_session import Session
from flask_login import LoginManager, login_required
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker

from models import *

app = Flask(__name__)

global_user = {}


@app.context_processor
def inject_user():
  global global_user
  return dict(user=global_user)


# Check for environment variable
if not os.getenv("DATABASE_URL"):
  raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
  return db.query(User).filter(User.id == user_id).first()


@app.route("/")
def index():
  return render_template("index.html")


@app.route("/results", methods=["POST"])
def results():
  qry = request.form['search']
  books = db.execute(
      f"SELECT * FROM books WHERE isbn LIKE '%{qry}%' OR author LIKE '%{qry}%' OR title LIKE '%{qry}%'"
  ).fetchall()
  return render_template("results.html", books=books)


@app.route("/book/<isbn>", methods=["GET", "POST"])
def book(isbn):
  if request.method == "POST":
    content = request.form['content']
    rating = int(request.form['rating'])
    user_id = int(request.form['user_id'])
    book_id = request.form['book_id']
    date = datetime.utcnow()
    review = Review(content=content, rating=rating, date=date, user_id=user_id, book_id=book_id)
    db.add(review)
    db.commit()
  book_sql = text(f"SELECT * FROM books WHERE isbn='{isbn}'")
  res = json.loads(
      requests.get("https://www.googleapis.com/books/v1/volumes", params={
          "q": isbn
      }).text)
  google = {
      'count': res['items'][1]['volumeInfo']['ratingsCount'],
      'rating': res['items'][1]['volumeInfo']['averageRating'],
      'image': res['items'][1]['volumeInfo']['imageLinks']['thumbnail']
  }
  book = db.execute(book_sql).fetchone()
  review_sql = text(
      f"SELECT reviews.content, reviews.rating, reviews.date, users.username FROM reviews INNER JOIN users ON reviews.user_id=users.id"
  )
  reviews = db.execute(review_sql).fetchall()
  return render_template("book.html", book=book, google=google, reviews=reviews)


@app.route("/register", methods=["GET", "POST"])
def register():
  global global_user
  if request.method == "GET":
    return render_template("register.html")
  else:
    username = request.form['username']
    password = request.form['password']
    user = User(username=username)
    user.set_password(password)
    db.add(user)
    db.commit()
    flask_login.login_user(user)
    global_user = user
    flash('successfully signed up', 'success')
    return redirect(url_for('index'))


@app.route("/login", methods=["GET", "POST"])
def login():
  global global_user
  if request.method == "GET":
    return render_template("login.html")
  else:
    username = request.form['username']
    password = request.form['password']
    user = db.query(User).filter(User.username == username).first()
    if user.check_password(password):
      flask_login.login_user(user)
      flash('logged in', 'success')
      global_user = user
      return redirect(url_for('index'))
    else:
      flash('login failed', 'danger')
      return redirect(url_for('login'))


@app.route("/logout", methods=["POST"])
@login_required
def logout():
  global global_user
  flask_login.logout_user()
  global_user = {}
  flash('logged out', 'success')
  return redirect(url_for('index'))


@app.route("/api/<isbn>")
def api(isbn):
  book_sql = text(f"SELECT * FROM books WHERE isbn='{isbn}'")
  res = json.loads(
      requests.get("https://www.googleapis.com/books/v1/volumes", params={
          "q": isbn
      }).text)
  if res:
    google = {
        'title': res['items'][1]['volumeInfo']['title'],
        'author': res['items'][1]['volumeInfo']['authors'][0],
        'publishedDate': res['items'][1]['volumeInfo']['publishedDate'],
        'ISBN_10': res['items'][1]['volumeInfo']['industryIdentifiers'][0]['identifier'],
        'ISBN_13': res['items'][1]['volumeInfo']['industryIdentifiers'][1]['identifier'],
        'reviewCount': res['items'][1]['volumeInfo']['ratingsCount'],
        'averageRating': res['items'][1]['volumeInfo']['averageRating']
    }
    return json.dumps(google)
  else:
    return 