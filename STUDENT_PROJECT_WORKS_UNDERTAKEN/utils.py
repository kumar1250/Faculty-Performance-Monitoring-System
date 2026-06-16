import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings


def send_project_status_email(
    email,
    username,
    project_title,
    project_type,
    publication_status,
    status,
    points=0,
    message=None,
):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = settings.BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    status_text = status.capitalize()

    html_content = f"""
    <html>
        <body>
            <p>Hello {username},</p>

            <p>Your student project submission has been
            <strong>{status_text}</strong>.</p>

            <table style="border-collapse: collapse;">
                <tr>
                    <td><strong>Project Title:</strong></td>
                    <td>{project_title}</td>
                </tr>
                <tr>
                    <td><strong>Project Type:</strong></td>
                    <td>{project_type}</td>
                </tr>
                <tr>
                    <td><strong>Publication Status:</strong></td>
                    <td>{publication_status}</td>
                </tr>
                <tr>
                    <td><strong>Status:</strong></td>
                    <td>{status_text}</td>
                </tr>
    """

    if status == "approved":
        html_content += f"""
                <tr>
                    <td><strong>Points Awarded:</strong></td>
                    <td>{points}</td>
                </tr>
        """

    if message:
        html_content += f"""
                <tr>
                    <td><strong>Remarks:</strong></td>
                    <td>{message}</td>
                </tr>
        """

    html_content += """
            </table>

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
        subject=f"Student Project {status_text}",
        html_content=html_content,
    )

    try:
        api_instance.send_transac_email(email_data)

    except ApiException as e:
        raise Exception(f"Brevo API error: {e}")