from django.core.mail import send_mail
from django.conf import settings


def send_otp_email(email, otp, username):
    subject = "Password Reset OTP - Faculty Performance System"
    message = f"""
Hello {username},

Your OTP for password reset is: {otp}

This OTP is valid for 10 minutes only.
Do not share this OTP with anyone.

If you did not request this, please ignore this email.

Regards,
Faculty Performance Monitoring System
    """
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )