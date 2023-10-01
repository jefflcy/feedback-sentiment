from datetime import timedelta
from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from os import path
from socket import gethostname
from wordcloud import WordCloud, STOPWORDS
import pandas as pd
import sqlite3
from transformers import pipeline

################################# CONFIG #################################

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///feedbacks.db"
app.config["SECRET_KEY"] = "some_secret_key"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
db = SQLAlchemy(app)

################################# MODELS #################################


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500), nullable=False)
    sentiment = db.Column(db.String(50), nullable=True)
    initiative_id = db.Column(
        db.Integer, db.ForeignKey("initiative.id"), nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    initiative = db.relationship("Initiative", back_populates="feedbacks")


class Initiative(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    dsc = db.Column(db.String(500), nullable=False)
    feedbacks = db.relationship("Feedback", back_populates="initiative")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    feedbacks = db.relationship("Feedback", backref="user", lazy=True)


################################# HELPER FUNCTIONS #################################


def wordcloud(initiative_id):
    sql_query = "SELECT content FROM feedback WHERE initiative_id=" + str(initiative_id)
    cnx = sqlite3.connect("instance/feedbacks.db")
    df = pd.read_sql_query(sql_query, cnx)

    comment_words = ""
    stopwords = set(STOPWORDS)

    # iterate through the csv file
    for val in df.content:
        # typecaste each val to string
        val = str(val)

        # split the value
        tokens = val.split()

        # Converts each token into lowercase
        for i in range(len(tokens)):
            tokens[i] = tokens[i].lower()

        comment_words += " ".join(tokens) + " "

    wordcloud = WordCloud(
        width=800,
        height=800,
        background_color="white",
        stopwords=stopwords,
        min_font_size=10,
    ).generate(comment_words)

    wordcloud.to_file("static/images/" + str(initiative_id) + ".jpg")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


################################# PAGES #################################


@app.route("/")
def index():
    initiatives = Initiative.query.all()
    initiatives.reverse()
    logged_in = "user_id" in session
    if not logged_in:
        initiatives = []
        role = False
    else:
        role = session["role"]
    return render_template(
        "index.html", initiatives=initiatives, logged_in=logged_in, role=role
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    logged_in = "user_id" in session
    if logged_in:
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            session["logged_in"] = True
            session["username"] = user.username
            session["role"] = user.role
            session["user_id"] = user.id  # Storing the user's ID in the session
            return redirect(url_for("index"))
        else:
            error = "Invalid credentials. Please try again."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/add_initiative", methods=["GET", "POST"])
@login_required
def add_initiative():
    # Check if the logged-in user is 'hr'
    if session["role"] != "HR":
        flash("Unauthorized! Only HR can add initiatives.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name")
        dsc = request.form.get("dsc")
        new_initiative = Initiative(name=name, dsc=dsc)
        db.session.add(new_initiative)
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("add_initiative.html")


@app.route("/initiative/<int:initiative_id>")
@login_required
def feedback_page(initiative_id):
    initiative = Initiative.query.get_or_404(initiative_id)
    feedbacks = Feedback.query.filter_by(initiative_id=initiative.id).all()
    return render_template(
        "feedback_page.html",
        feedbacks=feedbacks,
        initiative=initiative,
        user_role=session["role"],
    )


@app.route("/submit_feedback/<int:initiative_id>", methods=["POST"])
@login_required
def submit_feedback(initiative_id):
    content = request.form.get("content")

    # Analyze the sentiment of the feedback.
    sentiment_pipeline = pipeline(model="distilbert-base-uncased-finetuned-sst-2-english")
    analysis = sentiment_pipeline([content])[0]
    if (analysis.get("label") == 'POSITIVE' and analysis.get("score") > 0.6):
        sentiment = "positive"
    elif (analysis.get("label") == 'NEGATIVE' and analysis.get("score") > 0.6):
        sentiment = "negative"
    else:
        sentiment = "neutral"

    new_feedback = Feedback(
        sentiment=sentiment,
        content=content,
        initiative_id=initiative_id,
        user_id=session["user_id"],
    )
    db.session.add(new_feedback)
    db.session.commit()

    wordcloud(initiative_id)
    flash("Feedback submitted successfully!", "success")
    return redirect(url_for("feedback_page", initiative_id=initiative_id))


if __name__ == "__main__":
    with app.app_context():
        db.drop_all()  # remember to remove when prod
        db.create_all()
        if not User.query.filter_by(
            username="hr"
        ).first():  # if username="hr" not present means fresh db
            hr = User(username="hr", password="123456", role="HR")
            employee = User(username="employee", password="123456", role="Employee")
            db.session.add(hr)
            db.session.add(employee)
            db.session.commit()
        app.run(debug=True)
