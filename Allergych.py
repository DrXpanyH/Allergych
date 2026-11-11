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
import os

login_redir = RedirectResponse('/login', status_code=303)

def before(req, session):
   auth = req.scope['auth'] = session.get('auth', None)
   if not auth: return login_redir
  
bware = Beforeware(before, skip=[r'/favicon\.ico', r'/static/.*', r'.*\.css', '/login', '/register', '/plslogin', '/send_magic_link', r'/verify_magic_link/.*'])

app, rt = fast_app(live=True, debug=True, before=bware)

# Register and Login Table
db = database('data/allergych.db')
db.execute("PRAGMA foreign_keys = ON;")
SQL_CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password TEXT 
);
"""
db.execute(SQL_CREATE_USERS)
rl_users = db.t.users
User = rl_users.dataclass()

# Magic Link Table
SQL_CREATE_MAGIC_LINK = """
CREATE TABLE IF NOT EXISTS magic_links (
   user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
   magic_link_token TEXT,
   magic_link_expiry TIMESTAMP,
   is_active BOOLEAN DEFAULT FALSE
);
"""
db.execute(SQL_CREATE_MAGIC_LINK)   
magic_links = db.t.magic_links
MagicLink = magic_links.dataclass()

# Diary Table
SQL_CREATE_DIARY = """
CREATE TABLE IF NOT EXISTS diary (
    entry_id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    entry_date TIMESTAMP NOT NULL,
    sneezing INTEGER NOT NULL,
    runny_nose INTEGER NOT NULL,
    nasal_congestion INTEGER NOT NULL,
    nasal_itching INTEGER NOT NULL,
    drug INTEGER NOT NULL,
    total_score INTEGER NOT NULL,
    UNIQUE(user_id, entry_date)
);
"""
db.execute(SQL_CREATE_DIARY)
diary = db.t.diary
Diary = diary.dataclass()

def MyForm(btn_text, target): # Universal form for both login and register pages
    return Form(
        Input(id="email", type="email", placeholder="Email", required=True),
        Input(id="password", type="password", placeholder="Password", required=True),
        Button(btn_text, type="submit"),
        Span(id="error", style="color:red"),
        hx_post=target,
        hx_target="#error",
    )

def MagicLinkForm(btn_text: str, target: str):
    return Form(
        Div(
            Div(
                Input(id='email', type='email', placeholder='Email', required=True) 
            )
        ),
       Button(btn_text, type="submit", id="submit-btn"),
       P(id="error"),
       hx_post=target,
       hx_target="#error",
       hx_disabled_elt="#submit-btn"
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
                    P("Уже есть аккаунт? ", A("Войти", href="/login")),
                    P("Или войти без пароля? ", A("Войти без пароля", href="/plslogin"))
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
                    P("Создать аккаунт? ", A("Регистрация", href="/register")),
                    P("Или войти без пароля? ", A("Войти без пароля", href="/plslogin"))
                  )

# Password verification
def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password: # If the hashed password is None or empty, return False
        return False
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

@rt('/plslogin')
def get():   
    return Titled('Войти без пароля',
            P("Введите ваш email, и мы отправим вам ссылку для входа в систему."),
            MagicLinkForm("Отправить ссылку", "/send_magic_link")
        )
    

def send_magic_link_email(email: str, magic_link: str):
    smtp_server = "smtp.gmail.com"
    smtp_port = 465  # Port for SSL
    
    sender_email = os.getenv("SENDER_SERVER")  
    sender_password = os.getenv("SENDER_PASSWORD")
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Ссылка для входа в приложение"
    msg["From"] = f"Мой Проект <{sender_email}>"
    msg["To"] = email

    message = Titled('Вход в приложение',
        Body(            
        Header(
            H1("Привет"),
            P(f"Нажмите на эту ссылку, чтобы войти в приложение: {magic_link}"),
            P("Если вы не запрашивали вход в приложение, просто проигнорируйте это письмо."),
            P("С уважением, Илья")            
        )))
    message = to_xml(message)
    msg.attach(MIMEText(message, "html"))
    
    try:
        # Connect to the SMTP server and send the email
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, msg.as_string())
        print(f"[Success] The letter has been sent to {email}")
        return True
    except Exception as e:
        print(f"[SMTP Error] Failed to send email: {e}")
        return False

@rt('/send_magic_link')
def post(email: str):
    if not email:
        return "Email is required"
    try:
        user = rl_users.selectone(email=email)
    except NotFoundError:
        user = rl_users.insert(User(email=email, password=None))

  
    magic_link_token = secrets.token_urlsafe(32)
    magic_link_expiry = datetime.now() + timedelta(minutes=15)
  
    # .upsert() automatically inserts or updates based on the primary key (user_id)
    magic_links.upsert({
        'user_id': user.user_id,
        'magic_link_token': magic_link_token,
        'magic_link_expiry': magic_link_expiry,
        'is_active': False,
    })  
    magic_link = f"http://0.0.0.0:5001/verify_magic_link/{magic_link_token}"
  
    send_magic_link_email(email, magic_link)
  
    return (P("Ссылка для входа была отправлена на ваш email. Пожалуйста, проверьте вашу почту. Ссылка действительна в течение 15 минут.", 
            id="success"), 
            HttpHeader('HX-Reswap', 'outerHTML'), 
            Button("Magic link sent", type="submit", id="submit-btn", disabled=True, hx_swap_oob="true"))

@rt('/verify_magic_link/{token}')
def get(session, token: str):
    now = datetime.now().isoformat()
    try:
        user_mag = magic_links(
            where="magic_link_token = ? AND magic_link_expiry > ?", 
            where_args=[token, now]
        )[0]
        email=rl_users.selectone(user_id=user_mag.user_id).email
        session['auth'] = email
        magic_links.update({
            'user_id': user_mag.user_id,
            'magic_link_token': None,
            'magic_link_expiry': None,
            'is_active': True
        })
        return RedirectResponse('/main')
    except IndexError:
        return "Invalid or expired magic link"


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