"""Send the post-build notification via Gmail SMTP. Config comes from env vars (no secrets in git)."""
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

sender = os.environ['SMTP_USER']
password = os.environ['SMTP_PASS']
to = os.environ['MAIL_TO']
cc = os.environ.get('MAIL_CC', '')

msg = EmailMessage()
msg['From'] = sender
msg['To'] = to
if cc:
    msg['Cc'] = cc
msg['Subject'] = os.environ['MAIL_SUBJECT']
msg.set_content(Path(os.environ['MAIL_BODY_FILE']).read_text())

recipients = [a.strip() for a in [*to.split(','), *cc.split(',')] if a.strip()]
try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30) as s:
        s.login(sender, password)
        s.send_message(msg, to_addrs=recipients)
except Exception as err:  # fall back to STARTTLS on 587
    print(f'SSL/465 failed ({err}); retrying STARTTLS/587', file=sys.stderr)
    with smtplib.SMTP('smtp.gmail.com', 587, timeout=30) as s:
        s.starttls()
        s.login(sender, password)
        s.send_message(msg, to_addrs=recipients)
print(f'Email sent from {sender} to {recipients}')
