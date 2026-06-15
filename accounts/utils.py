import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings


def send_otp_email(email, otp, username):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = settings.BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    html_content = f"""
    <html>
        <body>
            <p>Hello {username},</p>

            <p>Your OTP for password reset is:</p>

            <h2>{otp}</h2>

            <p>This OTP is valid for <strong>10 minutes</strong> only.</p>

            <p>Do not share this OTP with anyone.</p>

            <p>If you did not request this, please ignore this email.</p>

            <br>

            <p>Regards,</p>
            <p><strong>Faculty Performance Monitoring System</strong></p>
        </body>
    </html>
    """

    email_data = sib_api_v3_sdk.SendSmtpEmail(
        sender={
            "name": "Faculty Performance Monitoring System",
            "email": settings.DEFAULT_FROM_EMAIL,
        },
        to=[{"email": email}],
        subject="Password Reset OTP - Faculty Performance System",
        html_content=html_content,
    )

    try:
        api_instance.send_transac_email(email_data)

    except ApiException as e:
        raise Exception(f"Brevo API error: {e}")