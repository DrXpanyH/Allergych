from fasthtml.common import *
from fastlite import database, NotFoundError
import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from functools import wraps

app, rt = fast_app(live=True, debug=True)

# Register and Login Database
rldb = database('data/users.db')
SQL_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);
"""
rldb.execute(SQL_CREATE_USERS)
rl_users = rldb.t.users
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
                  Div(Img(src='images/30168.jpg', style="width: 50%; height: 50%;")),
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

# Password hashing
ph = PasswordHasher()
def get_password_hash(password: str) -> str:
    return ph.hash(password)

@rt('/register') # Handling the registration
def post(email:str, password:str):
    try:
        user = rl_users.selectone(email=email)
        if user:
            return "Данный email уже зарегистрирован"
    except NotFoundError:
        new_user = User(email=email, password=get_password_hash(password))
        rl_users.insert(new_user)
        return HttpHeader('HX-Redirect', '/login')

@rt('/login')
def get():
    return Titled('Вход в систему', 
                    MyForm('Войти', '/login'),
                    Hr(),
                    P("Создать аккаунт? ", A("Регистрация", href="/register"))
                  )

# Password verification
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # Library will return True if the password matches
        return ph.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        # Library will raise an exception if the password does not match
        return False

@rt('/login') # Handling the login
def post(session, email:str, password:str):
    # The session is a simple key/value storage mechanism 
    # that persists between requests. 
    # It's unique to every user. 
    try:
        user = rl_users.selectone(email=email)
    except NotFoundError:
        return "Email или пароль введены неверно"
    if not verify_password(password, user.password):
        return "Email или пароль введены неверно"
    session['auth'] = user.email
    return HttpHeader('HX-Redirect', '/main')

def basic_auth(f):
    @wraps(f)
    def wrapper(session, *args, **kwargs):
        if "auth" not in session:
            return Response('Not Authorized', status_code=401)
        return f(session, *args, **kwargs)
    return wrapper

@rt('/main')
@basic_auth
def get(session):    
    return Titled('Меню',
                    Button("Выйти", hx_post="/logout", 
                        style="position: fixed; top: 16px; right: 16px; ")
                    )
                
@rt('/logout')
def post(session):
    del session['auth']
    return HttpHeader('HX-Redirect', '/login')

serve()