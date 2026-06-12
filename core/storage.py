from storages.backends.s3 import S3Storage


class CertificateStorage(S3Storage):
    location = "certificates"

<<<<<<< HEAD
class MembershipStorage(S3Storage):
    location = "memberships"
=======
class Sessioncertificate(S3Storage):
    location = "session_certificates"
>>>>>>> origin/main
