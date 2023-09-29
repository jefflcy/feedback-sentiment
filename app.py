from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from textblob import TextBlob

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///feedbacks.db"
app.config["SECRET_KEY"] = "some_secret_key"
db = SQLAlchemy(app)


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    sentiment = db.Column(db.String(50), nullable=True)


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

    new_feedback = Feedback(content=content, sentiment=sentiment)
    db.session.add(new_feedback)
    db.session.commit()

    flash("Feedback submitted successfully!", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
