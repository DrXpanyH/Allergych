from fasthtml.common import *
from fastlite import database, NotFoundError
import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app, rt = fast_app(live=True, debug=True)

def MyForm(btn_text, target): # Universal form for both login and register pages
    return Form(
        Input(id="email", type="email", placeholder="Email", required=True),
        Input(id="password", type="password", placeholder="Password", required=True),
        Button(btn_text, type="submit"),
        Span(id="error", style="color:red"),
        hx_post=target,
        hx_target="#error",
    )

@rt('/')
def get():
    return Titled('Добро пожаловать в Allergych',
                  Div(Img(src='images/30168.jpg', style="width: 50%; height: 50%;"), ),
                  Form(
                      P("Для продолжения войдите в систему: "),
                      Button('Войти ', href='/login'),
                      P('Или зарегистрируйтесь'),
                      Button('Регистрация ', href='/register')
                  ),
                  style="text-align:center;")

serve()