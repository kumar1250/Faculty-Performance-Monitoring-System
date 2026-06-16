from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from accounts.models import User
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD, IsPrincipal, IsDean

# ── per-app model imports ──────────────────────────────────────────────────────
from BOOK_PUBLICATIONS.models import BookPublication
from CERTIFICATE_COURSES_DONE.models import Course
from CONFERENCE_PUBLICATIONS.models import Publication
from CONSULTANCY.models import Consultancy
from FDPs_SUCH_AS_WORKSHOPS_CONFERENCES_SEMINARS_etc_ATTENDED.models import FDPs_Attended
from FDPs_SUCH_AS_WORKSHOPS_CONFERENCES_SEMINARS_etc_ORGANIZED.models import FDPs_Organized
from FUNDED_PROJECTS.models import FundedProject
from JOURNAL_PUBLICATIONS.models import JournalPublication
from LEARNING_MATERIAL.models import SubjectContribution
from MEMBERSHIPS_WITH_PROFESSIONAL_BODIES.models import ProfessionalMembership
from PATENTS.models import Patent
from RESEARCH_GUIDANCE.models import ResearchGuidance
from SESSIONS_AND_DELIVERING_TALKS_LECTURES.models import ChairingSession
from STUDENT_COUNSELLING_MENTORING.models import StudentCounselling
from STUDENT_PROJECT_WORKS_UNDERTAKEN.models import StudentProjectWork
from THEORY_COURSES_HANDLED.models import StudentFeedbackPerformance


# ── helpers ────────────────────────────────────────────────────────────────────

def _get_authenticated_user(request):
    """Return the decoded JWT payload or None."""
    token = get_token_from_request(request)
    if not token:
        return None
    return decode_token(token)


def _approved_points_sum(queryset):
    """Sum the `points` field of approved records only."""
    from django.db.models import Sum
    result = queryset.filter(approval_status='approved').aggregate(total=Sum('points'))
    return result['total'] or 0.0


def _module_summary(label, queryset):
    """Return a dict with count/approved/pending/rejected/points for one module."""
    approved_qs = queryset.filter(approval_status='approved')
    pending_qs  = queryset.filter(approval_status='pending')
    rejected_qs = queryset.filter(approval_status='rejected')

    from django.db.models import Sum
    pts = approved_qs.aggregate(total=Sum('points'))['total'] or 0.0

    return {
        'module':   label,
        'total':    queryset.count(),
        'approved': approved_qs.count(),
        'pending':  pending_qs.count(),
        'rejected': rejected_qs.count(),
        'points':   pts,
    }


def _build_faculty_detail(user_obj):
    """
    Build the full module breakdown + total_points for a single User instance.
    Uses related_name / reverse FK queries for every app.
    """
    uid = user_obj.id

    modules = [
        _module_summary("Book Publications",
                        BookPublication.objects.filter(user=user_obj)),

        _module_summary("Certificate Courses Done",
                        Course.objects.filter(user=user_obj)),

        _module_summary("Conference Publications",
                        Publication.objects.filter(user=user_obj)),

        _module_summary("Consultancy",
                        Consultancy.objects.filter(user=user_obj)),

        _module_summary("FDPs Attended",
                        FDPs_Attended.objects.filter(user=user_obj)),

        _module_summary("FDPs Organized",
                        FDPs_Organized.objects.filter(user=user_obj)),

        _module_summary("Funded Projects",
                        FundedProject.objects.filter(user=user_obj)),

        _module_summary("Journal Publications",
                        JournalPublication.objects.filter(user=user_obj)),

        _module_summary("Learning Material",
                        SubjectContribution.objects.filter(user=user_obj)),

        _module_summary("Memberships with Professional Bodies",
                        ProfessionalMembership.objects.filter(user=user_obj)),

        _module_summary("Patents",
                        Patent.objects.filter(user=user_obj)),

        _module_summary("Research Guidance",
                        ResearchGuidance.objects.filter(user=user_obj)),

        _module_summary("Sessions & Delivering Talks/Lectures",
                        ChairingSession.objects.filter(user=user_obj)),

        # StudentCounselling uses 'faculty' FK instead of 'user'
        _module_summary("Student Counselling / Mentoring",
                        StudentCounselling.objects.filter(faculty=user_obj)),

        _module_summary("Student Project Works",
                        StudentProjectWork.objects.filter(user=user_obj)),

        _module_summary("Theory Courses Handled",
                        StudentFeedbackPerformance.objects.filter(user=user_obj)),
    ]

    total_points = sum(m['points'] for m in modules)

    return {
        'user_id':     user_obj.id,
        'register_no': user_obj.register_no,
        'username':    user_obj.username,
        'email':       user_obj.email,
        'role':        user_obj.role,
        'modules':     modules,
        'total_points': total_points,
    }


# ── ViewSet ────────────────────────────────────────────────────────────────────

class FacultySummaryViewSet(ViewSet):
    """
    Endpoints
    ---------
    GET  /summary/faculty-summary/my-summary/
        → Own module details + total points (any authenticated user).

    GET  /summary/faculty-summary/by-user/?user_id=<id>
        → Module details for a specific user_id  (HOD / Principal / Dean).

    GET  /summary/faculty-summary/by-register/?register_no=<register_no>
        → Module details looked up by register_no  (HOD / Principal / Dean).

    GET  /summary/faculty-summary/total-points/
        → Own total approved points only (any authenticated user).

    GET  /summary/faculty-summary/total-points-by-user/?user_id=<id>
        → Total approved points for a specific user_id  (HOD / Principal / Dean).

    GET  /summary/faculty-summary/all-faculty/
        → List of all faculty with their total points  (HOD / Principal / Dean).
    """

    def get_permissions(self):
        privileged_actions = (
            'by_user', 'by_register',
            'total_points_by_user', 'all_faculty',
        )
        if self.action in privileged_actions:
            # HOD, Principal, or Dean can view other faculty
            return [IsAuthenticated()]   # tighten to IsHOD | IsPrincipal if needed
        return [IsAuthenticated()]

    # ------------------------------------------------------------------ #
    # MY SUMMARY  –  own modules                                          #
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='my-summary', methods=['get'])
    def my_summary(self, request):
        """Return the calling faculty's full module breakdown."""
        jwt_payload = _get_authenticated_user(request)
        if not jwt_payload:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user_obj = User.objects.get(id=jwt_payload['user_id'])
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response(_build_faculty_detail(user_obj), status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # BY USER ID  –  privileged lookup                                    #
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='by-user', methods=['get'])
    def by_user(self, request):
        """Return module details for any user_id (HOD / Principal / Dean)."""
        jwt_payload = _get_authenticated_user(request)
        if not jwt_payload:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        # Only HOD, principal, or dean may query other users
        allowed_roles = ('hod', 'principal', 'dean', 'committee_coordinator', 'department_incharge')
        if jwt_payload.get('role') not in allowed_roles:
            return Response(
                {'error': 'You do not have permission to view other faculty details.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_obj = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(_build_faculty_detail(user_obj), status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # BY REGISTER NO  –  privileged lookup                                #
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='by-register', methods=['get'])
    def by_register(self, request):
        """Return module details for a faculty identified by register_no."""
        jwt_payload = _get_authenticated_user(request)
        if not jwt_payload:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        allowed_roles = ('hod', 'principal', 'dean', 'committee_coordinator', 'department_incharge')
        if jwt_payload.get('role') not in allowed_roles:
            return Response(
                {'error': 'You do not have permission to view other faculty details.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        register_no = request.query_params.get('register_no')
        if not register_no:
            return Response({'error': 'register_no query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_obj = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response({'error': 'User not found for the given register_no.'}, status=status.HTTP_404_NOT_FOUND)

        return Response(_build_faculty_detail(user_obj), status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # TOTAL POINTS  –  own                                                #
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='total-points', methods=['get'])
    def total_points(self, request):
        """Return the calling faculty's total approved points."""
        jwt_payload = _get_authenticated_user(request)
        if not jwt_payload:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user_obj = User.objects.get(id=jwt_payload['user_id'])
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        detail = _build_faculty_detail(user_obj)
        return Response(
            {
                'user_id':      user_obj.id,
                'register_no':  user_obj.register_no,
                'username':     user_obj.username,
                'total_points': detail['total_points'],
            },
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------ #
    # TOTAL POINTS BY USER ID  –  privileged                             #
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='total-points-by-user', methods=['get'])
    def total_points_by_user(self, request):
        """Return total approved points for a specific user_id."""
        jwt_payload = _get_authenticated_user(request)
        if not jwt_payload:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        allowed_roles = ('hod', 'principal', 'dean', 'committee_coordinator', 'department_incharge')
        if jwt_payload.get('role') not in allowed_roles:
            return Response(
                {'error': 'You do not have permission to view other faculty details.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response({'error': 'user_id query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_obj = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        detail = _build_faculty_detail(user_obj)
        return Response(
            {
                'user_id':      user_obj.id,
                'register_no':  user_obj.register_no,
                'username':     user_obj.username,
                'total_points': detail['total_points'],
            },
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------ #
    # ALL FACULTY  –  list with points                                    #
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='all-faculty', methods=['get'])
    def all_faculty(self, request):
        """
        Return a list of all faculty members with their total approved points.
        Optionally filter by ?role=faculty (or any role).
        """
        jwt_payload = _get_authenticated_user(request)
        if not jwt_payload:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        allowed_roles = ('hod', 'principal', 'dean', 'committee_coordinator', 'department_incharge')
        if jwt_payload.get('role') not in allowed_roles:
            return Response(
                {'error': 'You do not have permission to list all faculty.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        role_filter = request.query_params.get('role', 'faculty')
        users = User.objects.filter(role=role_filter).order_by('register_no')

        results = []
        for u in users:
            detail = _build_faculty_detail(u)
            results.append({
                'user_id':      u.id,
                'register_no':  u.register_no,
                'username':     u.username,
                'email':        u.email,
                'total_points': detail['total_points'],
            })

        return Response({'count': len(results), 'faculty': results}, status=status.HTTP_200_OK)
