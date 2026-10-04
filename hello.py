import os
import json
import requests
from dotenv import load_dotenv
from flask import Flask, render_template, session, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'hard to guess string')
app.config['SQLALCHEMY_DATABASE_URI'] =\
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SENDGRID_API_KEY'] = os.getenv('SENDGRID_API_KEY')
SENDGRID_SENDER_EMAIL = os.getenv('SENDGRID_SENDER_EMAIL', 'caiovieiraalmeida07@gmail.com')

STUDENT_NAME = "Caio Vieira"
STUDENT_PRONT = "PT3035824"

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


# Tabela para persistir o histórico de e-mails enviados
class EmailLog(db.Model):
    __tablename__ = 'email_logs'
    id = db.Column(db.Integer, primary_key=True)
    de = db.Column(db.String(64))
    para = db.Column(db.Text)
    assunto = db.Column(db.String(128))
    texto = db.Column(db.String(256))
    timestamp = db.Column(db.DateTime, default=datetime.now)

    @property
    def para_lista(self):
        try:
            return json.loads(self.para)
        except Exception:
            return [self.para]


# Formulário da página inicial (Index)
class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    role = SelectField('Role?:', choices=[
        ('Admin', 'Admin'),
        ('Moderator', 'Moderator'),
        ('User', 'User')
    ], validators=[DataRequired()])
    submit = SubmitField('Submit')


# Formulário da página /email (Aula 070)
class EmailPageForm(FlaskForm):
    name = StringField('Qual é o seu nome?', validators=[DataRequired()])
    send_zoho = BooleanField('Deseja enviar e-mail para flaskaulasweb@zohomail.com?')
    submit = SubmitField('Submit')


def send_notification_email(new_username, send_to_zoho=False):
    recipients = ['caio.vieira1@aluno.ifsp.edu.br']

    if send_to_zoho:
        recipients.append('flaskaulasweb@zohomail.com')

    print(f"--> [DISPARO SENDGRID] Destinatários: {recipients} | Novo utilizador: {new_username}")

    subject = "[Flasky] Novo usuário"
    text_content = f"Novo usuário cadastrado: {new_username}"

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
        "subject": subject,
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
        if response.status_code == 202:
            log = EmailLog(
                de=new_username,
                para=json.dumps(recipients),
                assunto=subject,
                texto=text_content,
                timestamp=datetime.now()
            )
            db.session.add(log)
            db.session.commit()
        else:
            print(f"--> [RESPOSTA SENDGRID] Erro: {response.text}")
    except Exception as e:
        print(f"--> [ERRO SENDGRID]: {e}")


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role, EmailLog=EmailLog)


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

    return render_template(
        'index.html',
        form=form,
        name=session.get('name'),
        known=session.get('known', False),
        users=users,
        roles=roles,
        num_users=len(users),
        num_roles=len(roles)
    )


@app.route('/email', methods=['GET', 'POST'])
def email_route():
    default_role = Role.query.filter_by(name='User').first()
    if not default_role:
        default_role = Role(name='User')
        db.session.add(default_role)
        db.session.commit()

    form = EmailPageForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            user = User(username=form.name.data, role=default_role)
            db.session.add(user)
            db.session.commit()
            session['known'] = False

            send_notification_email(user.username, send_to_zoho=form.send_zoho.data)
        else:
            session['known'] = True

        session['name'] = form.name.data
        return redirect(url_for('email_route'))

    users = User.query.all()

    return render_template(
        'email.html',
        form=form,
        name=session.get('name'),
        known=session.get('known', False),
        users=users
    )

@app.route('/emails_enviados')
def emails_enviados():
    emails = EmailLog.query.order_by(EmailLog.timestamp.desc()).all()
    return render_template('emails_enviados.html', emails=emails)


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