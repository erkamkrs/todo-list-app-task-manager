from flask_login import UserMixin, LoginManager, login_user
from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from sqlalchemy.orm import relationship
import os
import shortuuid
import datetime
from forms import CreateListForm, RegisterForm, LoginForm
from werkzeug.security import generate_password_hash, check_password_hash

# Setup Flask App
SECRET_KEY = os.urandom(32)
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
Bootstrap(app)
app.app_context().push()


# Setup SQL
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///todo.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# create the extension
db = SQLAlchemy(app)
# initialize the app with the extension
db.init_app(app)

class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    due_date = db.Column(db.String(250), nullable=True)
    done = db.Column(db.Boolean, default=False)
    starred_task = db.Column(db.Boolean)
    parent_list = relationship("List", back_populates="tasks")
    list_id = db.Column(db.Integer, db.ForeignKey("lists.id"))

class List(db.Model):
    __tablename__ = "lists"
    id = db.Column(db.Integer, primary_key=True)
    url_key = db.Column(db.String(250), nullable=False, unique=True)
    name = db.Column(db.String(250), nullable=False)
    tasks = relationship("Task", back_populates="parent_list")
    user = relationship("User", back_populates="listss")
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), nullable=False, unique=True)
    password = db.Column(db.String(250), nullable=False)
    listss = relationship("List", back_populates="user")

    __hash__ = object.__hash__

    # db.create_all()

#  Makes the "current_year" variable available in every template#
@app.context_processor
def inject_now():
    return {'current_year': datetime.date.today().strftime("%Y"),
            'current_date': datetime.date.today().strftime("%Y-%m-%d")}

# Login Manager Setup

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)



@app.route("/", methods=["GET", "POST"])
def create_list():
    form = CreateListForm()
    url = shortuuid.ShortUUID().random(length=10)
    if form.validate_on_submit():
        new_list = List(
            name=form.name.data,
            url_key=url)
        db.session.add(new_list)
        db.session.commit()
        return redirect(url_for("home", url_key=url))
    return redirect(url_for("home", url_key=url))


# Shows a new list on the home page
@app.route("/<url_key>", methods=["GET", "POST"])
def home(url_key):
    list = List.query.filter_by(url_key=url_key).first()
    return render_template("index.html", list=list, url_key=url_key)


# takes the new list name and adds it to the database. returns home page with new name
@app.route("/name/<url_key>", methods=["POST"])
def new_name(url_key):
    list = List.query.filter_by(url_key=url_key).first()
    lname = request.form['lname']
    list.name = lname
    db.session.commit()
    return redirect(url_for("home", url_key=list.url_key))


# takes new  task created by the user and adds it to the list
@app.route("/task/<url_key>", methods=["POST"])
def new_task(url_key):
    print(request.form)
    name = request.form['task']
    list = List.query.filter_by(url_key=url_key).first()
    new_task = Task(
        name=name,
        list_id=list.id
    )
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for("home", url_key=list.url_key))

@app.route("/date/<url_key>/<id>", methods=["POST"])
def new_date(id, url_key):
    print(request.form)
    if request.form['due_date']:
        due_date = request.form['due_date']
    elif request.form['due_date_mobile']:
        due_date = request.form['due_date_mobile']
    else:
        due_date = request.form['due_date_tablet']
    task = Task.query.get(id)
    task.due_date = due_date
    db.session.commit()
    return redirect(url_for("home", url_key=url_key))


@app.route("/done/<url_key>/<id>", methods=["GET", "POST"])
def done_task(url_key, id):
   task = Task.query.get(id)
   if task.done:
       task.done = False
   else:
       task.done = True
   db.session.commit()
   return redirect(url_for("home", url_key=url_key))


@app.route("/starred/<url_key>/<id>", methods=["GET", "POST"])
def starred(url_key, id):
   task = Task.query.get(id)
   if task.starred_task:
        task.starred_task = False
   else:
       task.starred_task = True
   db.session.commit()
   return redirect(url_for("home", url_key=url_key))

@app.route("/delete_task/<url_key>/<id>")
def delete_task(url_key, id):
    task_to_delete = Task.query.get(id)
    db.session.delete(task_to_delete)
    db.session.commit()
    return redirect(url_for("home", url_key=url_key))

@app.route('/login', methods=["GET", "POST"])
def login(url_key):
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = User.query.filter_by(email=email).first()

        if user:
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for("home", url_key=url_key))
            else:
                flash("Password is incorrect. Check your password again.")
                return render_template("login.html", form=form, url_key=url_key)
        else:
            flash("This email is not registered.")
            return redirect(url_for("login", form=form, url_key=url_key))

    return render_template("login.html", form=form, url_key=url_key)


@app.route('/register', methods=["GET", "POST"])
def register(url_key):
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash("This email address is already signed up, login instead!")
            return render_template("register.html", form=form, url_key=url_key)
        hash_and_salted_password = generate_password_hash(
        form.password.data,
        method='pbkdf2:sha256',
        salt_length=8
        )
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("home", url_key=url_key))
    return render_template("register.html", form=form, url_key=url_key)


@app.route('/logout', methods=["GET", "POST"])
def logout():
    login_user()
    return redirect(url_for("create_list"))

@app.route("/user", methods=["GET", "POST"])
def user_page():
    return render_template("user.html")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)