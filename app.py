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
    feedbacks = Feedback.query.all()
    return render_template("index.html", feedbacks=feedbacks)


@app.route("/submit", methods=["POST"])
def submit_feedback():
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
    return redirect(url_for("index"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
