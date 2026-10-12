from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from . import mail

import requests
from datetime import datetime

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email(to, subject, template, **kwargs):
    app = current_app._get_current_object()
    msg = Message(app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['FLASKY_MAIL_SENDER'], recipients=[to])
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr

def send_simple_message(to, subject, newUser):
    app = current_app._get_current_object()
    full_subject = f"{app.config.get('FLASKY_MAIL_SUBJECT_PREFIX', '[Flasky]')} {subject}"
    body_text = f"Novo usuário cadastrado: {newUser}"

    print('Enviando mensagem (POST)...', flush=True)
    print('URL: ' + str(app.config.get('API_URL')), flush=True)
    print('api: ' + str(app.config.get('API_KEY')), flush=True)
    print('from: ' + str(app.config.get('API_FROM')), flush=True)
    print('to: ' + str(to), flush=True)
    print('subject: ' + full_subject, flush=True)
    print('text: ' + body_text, flush=True)

    # 1. Monta a lista de destinatários no padrão SendGrid
    if isinstance(to, str):
        to_list = [to]
    else:
        to_list = to

    recipients = [{"email": email} for email in to_list]

    # 2. Estrutura o payload JSON exigido pela v3 do SendGrid
    payload = {
        "personalizations": [
            {
                "to": recipients
            }
        ],
        "from": {
            "email": app.config['API_FROM']
        },
        "subject": full_subject,
        "content": [
            {
                "type": "text/plain",
                "value": body_text
            }
        ]
    }

    # 3. Headers com Bearer Token
    headers = {
        "Authorization": f"Bearer {app.config['API_KEY']}",
        "Content-Type": "application/json"
    }

    # 4. Envio com json=payload
    resposta = requests.post(
        app.config['API_URL'],
        headers=headers,
        json=payload
    )

    print(f'Enviando mensagem (Resposta)...{resposta} - {datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}', flush=True)
    if resposta.status_code != 202:
        print(f'Detalhes do erro SendGrid: {resposta.text}', flush=True)

    return resposta