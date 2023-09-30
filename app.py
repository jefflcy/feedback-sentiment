from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
)
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from textblob import TextBlob

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///feedbacks.db"
app.config["SECRET_KEY"] = "some_secret_key"
db = SQLAlchemy(app)


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    sentiment = db.Column(db.String(50), nullable=True)
    initiative_id = db.Column(db.Integer, db.ForeignKey("initiative.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    initiative = db.relationship("Initiative", back_populates="feedbacks")


class Initiative(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)

    feedbacks = db.relationship("Feedback", back_populates="initiative")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    feedbacks = db.relationship("Feedback", backref="user", lazy=True)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username, password=password).first()

        if user:  # if got user
            session["user_id"] = user.id
            session["role"] = user.role
            return redirect(url_for("index"))
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    initiatives = Initiative.query.all()
    return render_template("index.html", initiatives=initiatives)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


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

    new_feedback = Feedback(
        sentiment=sentiment, content=content, initiative_id=initiative_id
    )
    db.session.add(new_feedback)
    db.session.commit()
    flash("Feedback submitted successfully!", "success")
    return redirect(url_for("feedback_page", initiative_id=initiative_id))


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
