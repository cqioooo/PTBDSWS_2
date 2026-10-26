from flask import render_template, session, redirect, url_for, current_app
from .. import db
from ..models import User, Role
from ..email import send_simple_message
from . import main
from .forms import NameForm


@main.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            user_role = Role.query.filter_by(name='User').first()
            user = User(username=form.name.data, role=user_role)
            db.session.add(user)
            db.session.commit()
            session['known'] = False

            destinatarios = [form.email.data]

            admin_email = current_app.config.get('FLASKY_ADMIN')
            if admin_email and admin_email not in destinatarios:
                destinatarios.append(admin_email)

            zohu_email = "flaskaulasweb@zohomail.com"
            if zohu_email not in destinatarios:
                destinatarios.append(zohu_email)

            print('Enviando mensagem para:', destinatarios, flush=True)
            send_simple_message(destinatarios, 'Novo usuário', form.name.data)
            print('Mensagem enviada...', flush=True)
        else:
            session['known'] = True

        session['name'] = form.name.data
        return redirect(url_for('.index'))

    users = User.query.all()
    return render_template(
        'index.html',
        form=form,
        name=session.get('name'),
        known=session.get('known', False),
        users=users
    )