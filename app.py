from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from flask_mail import Mail
import json
import time
import datetime
import math
import os

with open('config.json', 'r') as c:
    params = json.load(c)["params"]

local_server = True
app = Flask(__name__)
app.secret_key = 'rakesh'
app.config['UPLOAD_FOLDER'] = params['upload_location']
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail-user'],
    MAIL_PASSWORD=params['gmail-password']
)
mail = Mail(app)
if(local_server):
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']

db = SQLAlchemy(app)


class Contacts(db.Model):
    srno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone_no = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    email = db.Column(db.String(20), nullable=False)


class Posts(db.Model):
    srno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    tagline = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(21), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(12), nullable=True)
    comments = db.relationship('Comments', backref='title', lazy='dynamic')

    def get_comments(self):
        return Comment.query.filter_by(post_srno=post.srno)

    def __repr__(self):
        return '<Posts %r>' % (self.content)


class Comments(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    content = db.Column(db.String(120), nullable=False)
    post_srno = db.Column(db.Integer, db.ForeignKey('posts.srno'))

    def __repr__(self):
        return '<Posts %r>' % (self.body)

    # pagination logic
    # first
    # previous = #
    # next= page+1
    # middele
    # previous = page-1
    # next = page + 1
    # last
    # previous = page-1
    # next = #


@app.route("/")
def home():
    posts = Posts.query.filter_by().all()
    posts.reverse()
    last = math.ceil(len(posts)/int(params['no_of_post']))
    page = request.args.get('page')
    if (not str(page).isnumeric()):
        page = 1
    page = int(page)
    posts = posts[(page-1)*int(params['no_of_post']):(page-1) *
                  int(params['no_of_post'])+int(params['no_of_post'])]
    if (page == 1):
        prev = "#"
        next = "/?page=" + str(page + 1)
    elif (page == last):
        prev = "/?page=" + str(page - 1)
        next = "#"
    else:
        prev = "/?page=" + str(page - 1)
        next = "/?page=" + str(page + 1)

    return render_template('index.html', params=params, posts=posts, prev=prev, next=next)


@app.route("/post/<int:post_srno>/<string:post_slug>", methods=['GET', 'POST'])
def post_route(post_slug, post_srno):
    post = Posts.query.filter_by(slug=post_slug).first()
    comments = Comments.query.filter_by(post_srno=post.srno).all()
    no_of_comments = len(comments)

    if(request.method == 'POST'):
        username = request.form.get('username')
        content = request.form.get('content')
        no_of_comments = no_of_comments
        date = datetime.datetime.now()
        post_srno = Posts.srno
        comment = Comments(username=username, content=content,
                           date=date, post_srno=post.srno)
        if (username == content or username == '' or content == ''):
            return render_template('post.html', params=params, comments=comments, post=post)
        else:
            db.session.add(comment)
            db.session.commit()
    return render_template('post.html', params=params, comments=comments, post=post)


@app.route("/about")
def about():
    return render_template('about.html', params=params)


@app.route("/comments", methods=['GET', 'POST'])
def comment_control():
    posts = Posts.query.filter_by().all()
    if 'user' in session and session['user'] == params['admin_username']:
        comments = Comments.query.filter_by().all()
        return render_template('comment-control.html', params=params, posts=posts, comments=comments)

    if request.method == 'POST':
        username = request.form.get('uname')
        password = request.form.get('pass')
        comments = Comments.query.filter_by().all()
        if (username == params['admin_username'] and password == params['admin_password']):
            session['user'] = username
        return render_template('comment-control.html', params=params, comments=comments, posts=posts)

    return render_template('login.html', params=params)


@app.route("/dashboard", methods=['GET', 'POST'])
def login():
    if 'user' in session and session['user'] == params['admin_username']:
        posts = Posts.query.filter_by().all()
        return render_template('dashboard.html', params=params, posts=posts)

    if request.method == 'POST':
        username = request.form.get('uname')
        password = request.form.get('pass')
        posts = Posts.query.filter_by().all()
        if (username == params['admin_username'] and password == params['admin_password']):
            session['user'] = username
            return render_template('dashboard.html', params=params, posts=posts)

    return render_template('login.html', params=params)


@app.route("/edit/<string:srno>", methods=['GET', 'POST'])
def edit(srno):
    if 'user' in session and session['user'] == params['admin_username']:
        if request.method == 'POST':
            box_title = request.form.get('title')
            tagline = request.form.get('tagline')
            slug = request.form.get('slug')
            img_file = request.form.get('img_file')
            content = request.form.get('content')
            date = datetime.datetime.now()

            if (srno == '0'):
                post = Posts(title=box_title, tagline=tagline, slug=slug,
                             img_file=img_file, content=content, date=date)
                db.session.add(post)
                db.session.commit()
                return redirect('/post/'+slug)
            else:
                post = Posts.query.filter_by(srno=srno).first()
                post.title = box_title
                post.tagline = tagline
                post.slug = slug
                post.img_file = img_file
                post.content = content
                post.date = date
                db.session.commit()
                return redirect('/post/'+slug)
        post = Posts.query.filter_by(srno=srno).first()
        return render_template('edit.html', params=params, srno=srno, post=post)


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if(request.method == 'POST'):
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        entry = Contacts(name=name, phone_no=phone,
                         msg=message, date=time.asctime(time.localtime(time.time())), email=email)
        date = time.asctime(time.localtime(time.time()))
        db.session.add(entry)
        db.session.commit()
        mail.send_message('New message from ' + name,
                          sender=email,
                          recipients=[params['gmail-user']],
                          body=message + "\n" + phone+"\n"+date
                          )
    return render_template('contact.html', params=params)


@app.route("/delete/<string:srno>", methods=['GET', 'POST'])
def delete(srno):
    if 'user' in session and session['user'] == params['admin_username']:
        post = Posts.query.filter_by(srno=srno).first()
        db.session.delete(post)
        db.session.commit()
    return redirect('/dashboard')


@app.route("/comment/<string:sno>", methods=['GET', 'POST'])
def delete_comment(sno):
    if 'user' in session and session['user'] == params['admin_username']:
        comment = Comments.query.filter_by(sno=sno).first()
        db.session.delete(comment)
        db.session.commit()
    return redirect('/comments')


@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/dashboard')


@app.route('/uploader', methods=('GET', 'POST'))
def uploadimg():
    if 'user' in session and session['user'] == params['admin_username']:
        if (request.method == 'POST'):
            f = request.files['img_file']
            f.save(os.path.join(
                app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            return "Uploaded Successfully"


app.run(debug=True)
