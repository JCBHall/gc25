import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config import settings
from utils.email_templates import DOC_HTML_TEMPLATE

def sendMail(to_email: str, subject: str, empName: str, link: str = "#"):
    """
    Send an email with the given parameters.
    """
    msg = MIMEMultipart()
    msg["From"] = settings.SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    
    message = DOC_HTML_TEMPLATE.replace("{{username}}", empName).replace("{{link}}", link)
    msg.attach(MIMEText(message, "html"))

    try:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, int(settings.SMTP_PORT)) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, to_email, msg.as_string())

        print(f"Email sent to {to_email} successfully!")
        return f"Email sent to {to_email}"
    except Exception as e:
        print(f"Error sending email: {e}")
        return f"Failed: {e}"
