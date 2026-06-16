import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings


def send_counselling_status_email(
    email,
    username,
    total_students,
    status,
    points=0,
    message=None
):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = settings.BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    html_content = f"""
    <html>
        <body>
            <p>Hello {username},</p>

            <p>Your student counselling submission has been
            <strong>{status}</strong>.</p>

            <table style="border-collapse: collapse;">
                <tr>
                    <td><strong>Total Students:</strong></td>
                    <td>{total_students}</td>
                </tr>

                <tr>
                    <td><strong>Points Awarded:</strong></td>
                    <td>{points}</td>
                </tr>
            </table>
    """

    if message:
        html_content += f"""
            <p><strong>Remarks:</strong> {message}</p>
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
        subject=f"Student Counselling Request {status}",
        html_content=html_content,
    )

    try:
        return api_instance.send_transac_email(email_data)

    except ApiException as e:
        raise Exception(f"Brevo API error: {e}")