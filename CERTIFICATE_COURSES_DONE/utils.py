import logging
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from django.conf import settings

logger = logging.getLogger(__name__)


def send_course_status_email(email, username, course_name, status, message=None):
    try:
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = settings.BREVO_API_KEY

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        email_data = sib_api_v3_sdk.SendSmtpEmail(
            sender={
                "name": "Faculty Performance Monitoring System",
                "email": settings.DEFAULT_FROM_EMAIL,
            },
            to=[{"email": email}],
            subject=f"Course Request {status.title()}",
            html_content=f"""
            <p>Hello {username},</p>

            <p>Your course request <strong>{course_name}</strong>
            has been <strong>{status.upper()}</strong>.</p>

            <p>{message or ""}</p>
            """
        )

        response = api_instance.send_transac_email(email_data)

        logger.info(f"Brevo email sent successfully: {response}")

    except ApiException as e:
        logger.error(f"Brevo API error: {e}")
        raise

    except Exception as e:
        logger.error(f"Unexpected email error: {e}")
        raise