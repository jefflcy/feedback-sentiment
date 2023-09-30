from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from textblob import TextBlob
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import pandas as pd
from os import path
import os
import sqlite3

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///feedbacks.db"
app.config["SECRET_KEY"] = "some_secret_key"
db = SQLAlchemy(app)


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    sentiment = db.Column(db.String(10), nullable=True)


class Initiative(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    feedbacks = db.relationship("Feedback", back_populates="initiative")


def wordcloud():
    cnx = sqlite3.connect('instance/feedbacks.db')
    df = pd.read_sql_query("SELECT content FROM feedback", cnx)
 
    comment_words = ''
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
        
        comment_words += " ".join(tokens)+" "
    
    wordcloud = WordCloud(width = 800, height = 800,
                    background_color ='white',
                    stopwords = stopwords,
                    min_font_size = 10).generate(comment_words)
    
    wordcloud.to_file('images/test.jpg')


@app.route("/")
def index():
    initiatives = Initiative.query.all()
    return render_template("index.html", initiatives=initiatives)


@app.route("/add_initiative", methods=["GET", "POST"])
def add_initiative():
    if request.method == "POST":
        name = request.form.get("name")
        new_initiative = Initiative(name=name)
        db.session.add(new_initiative)
        db.session.commit()
        return redirect(url_for("index"))
    return render_template("add_initiative.html")


@app.route("/submit_feedback/<int:initiative_id>", methods=["POST"])
def submit_feedback(initiative_id):
    content = request.form.get("content")

    # Analyze the sentiment using TextBlob
    analysis = TextBlob(content)
    if analysis.sentiment.polarity > 0:
        sentiment = "positive"
    elif analysis.sentiment.polarity == 0:
        sentiment = "neutral"
    else:
        sentiment = "negative"

    new_feedback = Feedback(content=content, department='0', sentiment=sentiment)
    db.session.add(new_feedback)
    db.session.commit()

    wordcloud()
    flash("Feedback submitted successfully!", "success")
    return redirect(url_for("feedback_page", initiative_id=initiative_id))


@app.route("/initiative/<int:initiative_id>")
def feedback_page(initiative_id):
    initiative = Initiative.query.get_or_404(initiative_id)
    feedbacks = Feedback.query.filter_by(initiative_id=initiative.id).all()
    return render_template(
        "feedback_page.html", feedbacks=feedbacks, initiative=initiative
    )


if __name__ == "__main__":
    with app.app_context():
        db.drop_all()
        db.create_all()
    app.run(debug=True)
