import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings


def send_session_status_email(
    email,
    username,
    event_name,
    event_type,
    event_level,
    status,
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

            <p>Your session activity request has been
            <strong>{status}</strong>.</p>

            <table style="border-collapse: collapse;">
                <tr>
                    <td><strong>Event Name:</strong></td>
                    <td>{event_name}</td>
                </tr>

                <tr>
                    <td><strong>Event Type:</strong></td>
                    <td>{event_type}</td>
                </tr>

                <tr>
                    <td><strong>Event Level:</strong></td>
                    <td>{event_level}</td>
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
        subject=f"Session Request {status}",
        html_content=html_content,
    )

    try:
        return api_instance.send_transac_email(email_data)

    except ApiException as e:
        raise Exception(f"Brevo API error: {e}")