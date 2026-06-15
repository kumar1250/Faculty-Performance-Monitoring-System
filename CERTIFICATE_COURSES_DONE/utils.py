import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings


def send_course_status_email(email, username, course_name, status, message=None):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = settings.BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    html_content = f"""
    <html>
        <body>
            <p>Hello {username},</p>

            <p>Your course request <strong>{course_name}</strong> has been
            <strong>{status.upper()}</strong>.</p>
    """

    if message:
        html_content += f"""
            <p><strong>Message:</strong> {message}</p>
        """

    html_content += """
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
        subject=f"Course Request {status.title()}",
        html_content=html_content,
    )

    try:
        api_instance.send_transac_email(email_data)
    except ApiException as e:
        print(f"Brevo email error: {e}")