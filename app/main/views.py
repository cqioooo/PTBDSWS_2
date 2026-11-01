from flask import render_template, session, redirect, url_for, current_app, request, flash
from .. import db
from ..models import User, Role
from ..email import send_simple_message
from . import main
from .forms import NameForm

@main.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()

    # 1. Trata a atualização inline do nome
    if request.method == 'POST' and 'update_user_id' in request.form:
        user_id = request.form.get('update_user_id')
        novo_nome = request.form.get('new_username')
        user = User.query.get(user_id)
        if user and novo_nome and novo_nome.strip():
            user.username = novo_nome.strip()
            db.session.commit()
            flash('Nome do usuário atualizado com sucesso.')
        return redirect(url_for('.index'))

    # 2. Trata a exclusão do usuário
    if request.method == 'POST' and 'delete_user_id' in request.form:
        user_id = request.form.get('delete_user_id')
        user = User.query.get(user_id)
        if user:
            db.session.delete(user)
            db.session.commit()
        return redirect(url_for('.index'))

    # 3. Trata o formulário de novo cadastro
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

            send_simple_message(destinatarios, 'Novo usuário', form.name.data)
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