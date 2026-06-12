from storages.backends.s3 import S3Storage


class CertificateStorage(S3Storage):
    location = "certificates"

class Sessioncertificate(S3Storage):
    location = "session_certificates"
    
class ConferenceCertificate(S3Storage):
    location = "conference_certificates"

class Patent_certificate(S3Storage):
    location = "certificates"

