from storages.backends.s3 import S3Storage


class CertificateStorage(S3Storage):
    location = "certificates"
    
class MembershipStorage(S3Storage):
    location = "memberships"

class Sessioncertificate(S3Storage):
    location = "session_certificates"

    
class ConferenceCertificate(S3Storage):
    location = "conference_certificates"

class Patent_certificate(S3Storage):
    location = "patent_certificate"

class FDPs_Attended_Storage(S3Storage):
    location = "FDPS_certificate"
    




class Student_project_Storage(S3Storage):
    location = "student_project_certificate"
    
class FDPs_Organized_Storage(S3Storage):
    location = "FDPs_Organized_Storage"