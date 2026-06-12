from storages.backends.s3 import S3Storage


class CertificateStorage(S3Storage):
    location = "certificates"

class MembershipStorage(S3Storage):
    location = "memberships"
