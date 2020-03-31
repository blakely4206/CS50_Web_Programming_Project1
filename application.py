import os, csv

from flask import Flask, session, request, jsonify, render_template
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from models import *

app = Flask(__name__)

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

GOODREADS_KEY = os.getenv("GOODREADS_KEY")

@app.route("/")
def index():
    return render_template("index.html")
    
@app.route("/login", methods=["POST"])
def login():
    id = request.form.get("user_name")
    password = request.form.get("password")
    
    rows = db.execute("SELECT * FROM users where id = :id and password = :password", {"id": id, "password": password})
    
    result = rows.fetchone()
    
    if result == None:
        return render_template("index.html", message="Invalid Login")
    else:
        session["user_id"] = id;
        return render_template("main.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/create", methods=["POST"])
def create():
    user_name = request.form.get("user_name")
    user_id = request.form.get("user_id")
    password = request.form.get("password")
    
    db.execute("INSERT INTO users values (:user_id, :user_name, :password)", {"user_id": user_id, "user_name": user_name, "password": password})
    db.execute("COMMIT")
    
    return render_template("index.html")
    
@app.route("/search_results", methods=["POST"])
def search():
    lookup = request.form.get("lookup")
    query = "%" + lookup + "%"
    rows = db.execute("SELECT * FROM books where isbn like :query or title like :query or author like :query;", {"query": query})
    
    results = rows.fetchall()

    return render_template("search.html", results=results)
    
@app.route("/search/<string:isbn>")
def result(isbn):
    book = db.execute("SELECT * FROM books where isbn = :isbn", {"isbn": isbn}).fetchone()
    
    import requests
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key" : GOODREADS_KEY, "isbns" : isbn}).json()
    good_review = {'average_review' : res['books'][0]['average_rating'], 'review_count' : res['books'][0]['work_ratings_count']}
    
    user_review = db.execute("Select * FROM reviews where isbn = :isbn and author = :author;", {"isbn": isbn, "author": session["user_id"]}).fetchone()

    if user_review == None:
        return render_template("result.html", book=book, good_review = good_review)
    else: 
        return render_template("review_result.html", book=book, good_review=good_review, user_review=user_review)
        
@app.route("/search/<string:isbn>", methods=["POST"])
def review(isbn):
    rating = request.form.get("stars")
    review = request.form.get("review_text")
    
    print(rating)
    print(review)
    db.execute("INSERT INTO reviews values (:isbn, :author, :rating, :review)", {"isbn": isbn, "author" : session["user_id"], "rating" : rating, "review" : review})
    
    book = db.execute("SELECT * FROM books where isbn = :isbn", {"isbn": isbn}).fetchone()
    import requests
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key" : GOODREADS_KEY, "isbns" : isbn}).json()
    good_review = {'average_review' : res['books'][0]['average_rating'], 'review_count' : res['books'][0]['work_ratings_count']}
    
    user_review = db.execute("Select * FROM reviews where isbn = :isbn and author = :author;", {"isbn": isbn, "author": session["user_id"]}).fetchone()

    return render_template("review_result.html", book=book, good_review=good_review, user_review=user_review)

@app.route("/api/<string:isbn>")
def book_api(isbn):
    book = db.execute("SELECT * FROM books where isbn = :isbn;", {"isbn": isbn}).fetchone()
    
    import requests
    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key" : GOODREADS_KEY, "isbns" : isbn}).json()
    
    if book is None:
        return jsonify({"error": "Invalid ISBN"}), 422

    return jsonify({
            "title": book['title'],
            "author": book['author'],
            "year": book['year'],
            "isbn": book['isbn'],
            "review_count": res['books'][0]['work_ratings_count'],
            "average_score": res['books'][0]['average_rating'] 
        })