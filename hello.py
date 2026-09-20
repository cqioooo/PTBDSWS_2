import os
import requests
from flask import Flask, render_template, session, redirect, url_for, request
from dotenv import load_dotenv
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'
app.config['SQLALCHEMY_DATABASE_URI'] =\
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SENDGRID_API_KEY'] = os.getenv('SENDGRID_API_KEY')
SENDGRID_SENDER_EMAIL = os.getenv('SENDGRID_SENDER_EMAIL', 'caiovieiraalmeida07@gmail.com')

STUDENT_NAME = "Caio Vieira"
STUDENT_PRONT = "PT3035824"

def send_notification_email(new_username):
    print(f"--> [DISPARO SENDGRID] A enviar e-mail para: {new_username}")
    recipients = ['flaskaulasweb@zohomail.com', 'caio.vieira1@aluno.ifsp.edu.br']

    html_content = render_template(
        'email_body.html',
        student_name=STUDENT_NAME,
        student_pront=STUDENT_PRONT,
        new_username=new_username
    )

    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {app.config['SENDGRID_API_KEY']}",
        "Content-Type": "application/json"
    }

    payload = {
        "personalizations": [
            {
                "to": [{"email": r} for r in recipients]
            }
        ],
        "from": {
            "email": SENDGRID_SENDER_EMAIL,
            "name": STUDENT_NAME
        },
        "subject": "Novo Usuário Cadastrado",
        "content": [
            {
                "type": "text/html",
                "value": html_content
            }
        ]
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"--> [RESPOSTA SENDGRID] Status: {response.status_code}")
        print(f"--> [RESPOSTA SENDGRID] Resposta: {response.text}")
    except Exception as e:
        print(f"--> [ERRO SENDGRID]: {e}")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"--> [RESPOSTA SENDGRID] Código HTTP: {response.status_code}")
        print(f"--> [RESPOSTA SENDGRID] Corpo: {response.text}")
    except Exception as e:
        print(f"--> [ERRO DE CONEXÃO SENDGRID]: {e}")

bootstrap = Bootstrap(app)
moment = Moment(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role %r>' % self.name


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __repr__(self):
        return '<User %r>' % self.username


# Formulário com o campo de seleção Role?:
class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    role = SelectField('Role?:', choices=[
        ('Admin', 'Admin'),
        ('Moderator', 'Moderator'),
        ('User', 'User')
    ], validators=[DataRequired()])
    submit = SubmitField('Submit')

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@app.route('/', methods=['GET', 'POST'])
def index():
    roles_names = ['Admin', 'Moderator', 'User']
    for r_name in roles_names:
        if not Role.query.filter_by(name=r_name).first():
            db.session.add(Role(name=r_name))
    db.session.commit()

    form = NameForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        selected_role = Role.query.filter_by(name=form.role.data).first()

        if user is None:
            user = User(username=form.name.data, role=selected_role)
            db.session.add(user)
            db.session.commit()
            session['known'] = False
        else:
            user.role = selected_role
            db.session.commit()
            session['known'] = True

        session['name'] = form.name.data
        return redirect(url_for('index'))

    users = User.query.all()
    roles = Role.query.all()
    num_users = len(users)
    num_roles = len(roles)

    return render_template(
        'index.html',
        form=form,
        name=session.get('name'),
        known=session.get('known', False),
        users=users,
        roles=roles,
        num_users=num_users,
        num_roles=num_roles
    )


@app.route('/email', methods=['GET', 'POST'])
def email_route():
    form = NameForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            user = User(username=form.name.data)
            db.session.add(user)
            db.session.commit()
            session['known'] = False

            send_notification_email(user.username)
        else:
            session['known'] = True

        session['name'] = form.name.data
        return redirect(url_for('email_route'))

    return render_template(
        'email.html',
        form=form,
        name=session.get('name'),
        known=session.get('known', False)
    )


@app.route('/user/<name>/<pront>/<inst>')
def user(name, pront, inst):
    return render_template('user.html', name=name, pront=pront, inst=inst)


@app.route('/contextorequisicao/<name>')
def contexto(name):
    return render_template(
        'contexto.html',
        name=name,
        user_agent=request.headers.get('User-Agent'),
        ip=request.remote_addr,
        host=request.host
    )