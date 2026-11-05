from fasthtml.common import *
from fastlite import database, NotFoundError
import secrets
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app, rt = fast_app(live=True, debug=True)

@rt('/')
def get():
    return Titled('Добро пожаловать в Allergych')

serve()