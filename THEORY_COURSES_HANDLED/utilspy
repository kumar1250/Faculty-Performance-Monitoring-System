import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings


def send_student_feedback_email(
    email,
    username,
    subject_name,
    academic_year,
    cycle_1_feedback,
    cycle_2_feedback,
    exam_result,
    points=0,
    message=None,
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

            <p>Your student feedback performance record has been submitted successfully.</p>

            <table style="border-collapse: collapse;">
                <tr>
                    <td><strong>Academic Year:</strong></td>
                    <td>{academic_year}</td>
                </tr>

                <tr>
                    <td><strong>Subject:</strong></td>
                    <td>{subject_name}</td>
                </tr>

                <tr>
                    <td><strong>Cycle 1 Feedback:</strong></td>
                    <td>{cycle_1_feedback}</td>
                </tr>

                <tr>
                    <td><strong>Cycle 2 Feedback:</strong></td>
                    <td>{cycle_2_feedback}</td>
                </tr>

                <tr>
                    <td><strong>Exam Result:</strong></td>
                    <td>{exam_result}</td>
                </tr>

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
        subject="Student Feedback Performance Submitted",
        html_content=html_content,
    )

    try:
        api_instance.send_transac_email(email_data)

    except ApiException as e:
        raise Exception(f"Brevo API error: {e}")