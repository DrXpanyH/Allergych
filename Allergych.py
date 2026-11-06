from fasthtml.common import *
from fastlite import database, NotFoundError
import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app, rt = fast_app(live=True, debug=True)


# Register and Login Database
rldb = database('data/users.db')
SQL_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    PRIMARY KEY (user_id, email)
);
"""
rldb.execute(SQL_CREATE_USERS)
rl_users = rldb.t.rl_users
User = rl_users.dataclass()

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
                      A('Войти ', href='/login', role='button'),
                      P('Или зарегистрируйтесь'),
                      A('Регистрация ', href='/register', role='button')
                  ),
                  style="text-align:center;")

@rt('/register')
def get():
    return Titled('Регистрация', 
                    MyForm('Зарегистрироваться', '/register'),
                    Hr(),
                    P("Уже есть аккаунт? ", 
                    A("Войти", href="/login"))
                )
    
@rt('/login')
def get():
    return Titled('Вход в систему', 
                  MyForm('Войти', '/login'))

serve()