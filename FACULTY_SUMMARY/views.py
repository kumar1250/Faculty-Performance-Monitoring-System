from django.db.models import Sum
from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from accounts.models import User
from accounts.models import Profile
from accounts.serializers import UserSerializer
from accounts.token_jwt import decode_token, get_token_from_request
from accounts.permissions import IsAuthenticated, IsHOD, IsPrincipal, IsDean
import boto3
from django.conf import settings

# ── per-app model + serializer imports ───────────────────────────────────────
from BOOK_PUBLICATIONS.models import BookPublication
from BOOK_PUBLICATIONS.serializers import BookPublicationSerializer

from CERTIFICATE_COURSES_DONE.models import Course
from CERTIFICATE_COURSES_DONE.serializers import CourseSerializer

from CONFERENCE_PUBLICATIONS.models import Publication
from CONFERENCE_PUBLICATIONS.serializers import PublicationSerializer

from CONSULTANCY.models import Consultancy
from CONSULTANCY.serializers import ConsultancySerializer

from FDPs_SUCH_AS_WORKSHOPS_CONFERENCES_SEMINARS_etc_ATTENDED.models import FDPs_Attended
from FDPs_SUCH_AS_WORKSHOPS_CONFERENCES_SEMINARS_etc_ATTENDED.serializers import FDPsAttendedSerializer

from FDPs_SUCH_AS_WORKSHOPS_CONFERENCES_SEMINARS_etc_ORGANIZED.models import FDPs_Organized
from FDPs_SUCH_AS_WORKSHOPS_CONFERENCES_SEMINARS_etc_ORGANIZED.serializers import FDPsOrganizedSerializer

from FUNDED_PROJECTS.models import FundedProject
from FUNDED_PROJECTS.serializers import FundedProjectSerializer

from JOURNAL_PUBLICATIONS.models import JournalPublication
from JOURNAL_PUBLICATIONS.serializers import JournalPublicationSerializer

from LEARNING_MATERIAL.models import SubjectContribution
from LEARNING_MATERIAL.serializers import SubjectContributionSerializer

from MEMBERSHIPS_WITH_PROFESSIONAL_BODIES.models import ProfessionalMembership
from MEMBERSHIPS_WITH_PROFESSIONAL_BODIES.serializers import ProfessionalMembershipSerializer

from PATENTS.models import Patent
from PATENTS.serializers import PatentSerializer

from RESEARCH_GUIDANCE.models import ResearchGuidance
from RESEARCH_GUIDANCE.serializers import ResearchGuidanceSerializer

from SESSIONS_AND_DELIVERING_TALKS_LECTURES.models import ChairingSession
from SESSIONS_AND_DELIVERING_TALKS_LECTURES.serializers import ChairingSessionSerializer

from STUDENT_COUNSELLING_MENTORING.models import StudentCounselling
from STUDENT_COUNSELLING_MENTORING.serializers import StudentCounsellingSerializer

from STUDENT_PROJECT_WORKS_UNDERTAKEN.models import StudentProjectWork
from STUDENT_PROJECT_WORKS_UNDERTAKEN.serializers import StudentProjectWorkSerializer

from THEORY_COURSES_HANDLED.models import StudentFeedbackPerformance
from THEORY_COURSES_HANDLED.serializers import StudentFeedbackPerformanceSerializer


PRIVILEGED_ROLES = ('hod', 'principal', 'dean', 'committee_coordinator', 'department_incharge')


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_authenticated_user(request):
    """Return the decoded JWT payload or None."""
    token = get_token_from_request(request)
    if not token:
        return None
    return decode_token(token)


def _approved_points_sum(queryset):
    result = queryset.filter(approval_status='approved').aggregate(total=Sum('points'))
    return float(result['total'] or 0)


def _module_summary_no_approval(label, queryset):
    """For models without an approval_status field — count all records and sum points."""
    pts = queryset.aggregate(total=Sum('points'))['total'] or 0
    return {
        'module':   label,
        'total':    queryset.count(),
        'approved': queryset.count(),
        'pending':  0,
        'rejected': 0,
        # Different apps store `points` as FloatField vs DecimalField, so Sum()
        # can return either a float or a Decimal depending on the model.
        # Normalize to float here so later sum()/sort() calls never mix types.
        'points':   float(pts),
    }


def _module_summary(label, queryset):
    """Return a dict with count/approved/pending/rejected/points for one module."""
    approved_qs = queryset.filter(approval_status='approved')
    pending_qs  = queryset.filter(approval_status='pending')
    rejected_qs = queryset.filter(approval_status='rejected')

    pts = approved_qs.aggregate(total=Sum('points'))['total'] or 0

    return {
        'module':   label,
        'total':    queryset.count(),
        'approved': approved_qs.count(),
        'pending':  pending_qs.count(),
        'rejected': rejected_qs.count(),
        # Normalize to float — same reasoning as above.
        'points':   float(pts),
    }


# Config used by both the lightweight summary and the full-detail builders.
# (label, queryset_fn(user_obj), serializer_class, has_approval_status)
def _module_config(user_obj):
    return [
        ("Book Publications",
         BookPublication.objects.filter(user=user_obj), BookPublicationSerializer, True),

        ("Certificate Courses Done",
         Course.objects.filter(user=user_obj), CourseSerializer, False),

        ("Conference Publications",
         Publication.objects.filter(user=user_obj), PublicationSerializer, True),

        ("Consultancy",
         Consultancy.objects.filter(user=user_obj), ConsultancySerializer, True),

        ("FDPs Attended",
         FDPs_Attended.objects.filter(user=user_obj), FDPsAttendedSerializer, True),

        ("FDPs Organized",
         FDPs_Organized.objects.filter(user=user_obj), FDPsOrganizedSerializer, True),

        ("Funded Projects",
         FundedProject.objects.filter(user=user_obj), FundedProjectSerializer, True),

        ("Journal Publications",
         JournalPublication.objects.filter(user=user_obj), JournalPublicationSerializer, True),

        ("Learning Material",
         SubjectContribution.objects.filter(user=user_obj), SubjectContributionSerializer, False),

        ("Memberships with Professional Bodies",
         ProfessionalMembership.objects.filter(user=user_obj), ProfessionalMembershipSerializer, False),

        ("Patents",
         Patent.objects.filter(user=user_obj), PatentSerializer, True),

        ("Research Guidance",
         ResearchGuidance.objects.filter(user=user_obj), ResearchGuidanceSerializer, True),

        ("Sessions & Delivering Talks/Lectures",
         ChairingSession.objects.filter(user=user_obj), ChairingSessionSerializer, True),

        # StudentCounselling uses 'faculty' FK instead of 'user'
        ("Student Counselling / Mentoring",
         StudentCounselling.objects.filter(faculty=user_obj), StudentCounsellingSerializer, False),

        ("Student Project Works",
         StudentProjectWork.objects.filter(user=user_obj), StudentProjectWorkSerializer, True),

        ("Theory Courses Handled",
         StudentFeedbackPerformance.objects.filter(user=user_obj), StudentFeedbackPerformanceSerializer, False),
    ]


def _build_faculty_detail(user_obj):
    """Lightweight version — counts + points only (used by existing endpoints)."""
    modules = []
    for label, qs, _serializer_cls, has_approval in _module_config(user_obj):
        if has_approval:
            modules.append(_module_summary(label, qs))
        else:
            modules.append(_module_summary_no_approval(label, qs))

    # total_points = sum(m['points'] for m in modules)
    module_points = sum(m['points'] for m in modules)
    total_points  = module_points + float(user_obj.points or 0)

    return {
        'user_id':      user_obj.id,
        'register_no':  user_obj.register_no,
        'username':     user_obj.username,
        'email':        user_obj.email,
        'role':         user_obj.role,
        'modules':      modules,
        'total_points': total_points,
    }


def _build_faculty_full_detail(user_obj, request):
    """
    Full version — every record's complete field data for every module,
    plus the same counts/points summary, plus total points.
    """
    modules = []
    for label, qs, serializer_cls, has_approval in _module_config(user_obj):
        records = serializer_cls(qs, many=True, context={'request': request}).data

        if has_approval:
            summary = _module_summary(label, qs)
        else:
            summary = _module_summary_no_approval(label, qs)

        modules.append({
            'module':   label,
            'total':    summary['total'],
            'approved': summary['approved'],
            'pending':  summary['pending'],
            'rejected': summary['rejected'],
            'points':   summary['points'],
            'records':  records,   # <-- every field of every record in this module
        })

    total_points = sum(m['points'] for m in modules)

    return {
        'user_id':      user_obj.id,
        'register_no':  user_obj.register_no,
        'username':     user_obj.username,
        'email':        user_obj.email,
        'role':         user_obj.role,
        'modules':      modules,
        'total_points': total_points,
    }


def _assign_ranks(rows):
    """
    Dense ranking: equal points share the same rank, and the next distinct
    score simply continues at (previous_rank + 1) — no gaps.
    e.g. points [90, 80, 80, 70] -> ranks [1, 2, 2, 3]
    """
    ranked = []
    previous_points = None
    current_rank = 0
    for row in rows:
        if row['total_points'] != previous_points:
            current_rank += 1
            previous_points = row['total_points']
        row_with_rank = {'rank': current_rank, **row}
        ranked.append(row_with_rank)
    return ranked


def _rank_of_user(ranked_rows, user_id):
    """Find a specific user's rank/row inside an already-ranked leaderboard list."""
    for row in ranked_rows:
        if row['user_id'] == user_id:
            return row
    return None


def _get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )


def _profile_image_urls_for_users(users):
    """
    Bulk-build {user_id: presigned_profile_image_url} for a list/queryset of
    User objects in ONE query instead of one Profile lookup per row — search
    results can return up to 25 rows and the leaderboard/all-faculty list can
    return every faculty member, so this avoids an N+1 query (and N S3 calls
    only happen for users who actually have a photo uploaded).
    Mirrors the key format used in accounts/views.py ProfileViewSet so the
    presigned URL always points at the same S3 prefix the file was uploaded to.
    """
    user_ids = [u.id for u in users]
    profiles = Profile.objects.filter(user_id__in=user_ids).exclude(profile_image='')
    if not profiles:
        return {}

    s3 = _get_s3_client()
    urls = {}
    for profile in profiles:
        if not profile.profile_image:
            continue
        key = f"profile_image/{profile.profile_image.name}"
        urls[profile.user_id] = s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key,
            },
            ExpiresIn=3600,
        )
    return urls


def _serialize_basic_user(u, image_url=None):
    return {
        'user_id':           u.id,
        'register_no':       u.register_no,
        'username':          u.username,
        'email':             u.email,
        'role':              u.role,
        'profile_image_url': image_url,
    }


# ── ViewSet ───────────────────────────────────────────────────────────────────

class FacultySummaryViewSet(ViewSet):
    """
    Endpoints
    ---------
    GET  /summary/faculty-summary/my-summary/
        -> Own module details (counts + points) for the logged-in user.

    GET  /summary/faculty-summary/by-user/?user_id=<id>
        -> Module details (counts + points) for a specific user_id.

    GET  /summary/faculty-summary/by-register/?register_no=<register_no>
        -> Module details (counts + points) looked up by register_no.

    GET  /summary/faculty-summary/by-register-full/?register_no=<register_no>
        -> EVERY full record (all fields) for every module, for one faculty,
           looked up by register_no. This is the "enter register number,
           get everything" endpoint. Works for ANY role, not just faculty.

    GET  /summary/faculty-summary/search/?q=<text>
        -> Search ALL users (any role — faculty, HOD, principal, dean, etc.)
           by partial register_no or username match. Returns a short list
           of {user_id, register_no, username, email, role} so the frontend
           can build a live search/autocomplete box without pulling the
           entire accounts list and filtering client-side.

    GET  /summary/faculty-summary/dashboard/?register_no=<register_no>&role=all
        -> The all-in-one view: same full module breakdown as by-register-full,
           PLUS that user's live rank among peers and points behind #1.
           Defaults to ranking against ALL users; pass ?role=faculty to
           narrow the peer group to one role.

    GET  /summary/faculty-summary/total-points/
        -> Own total approved points only.

    GET  /summary/faculty-summary/total-points-by-user/?user_id=<id>
        -> Total approved points for a specific user_id.

    GET  /summary/faculty-summary/all-faculty/?role=all
        -> List of all users with their total points (unranked, register_no
           order). Defaults to ALL roles now; pass ?role=faculty to narrow.

    GET  /summary/faculty-summary/leaderboard/?role=all
        -> All users ranked by total points, HIGHEST FIRST, with rank numbers.
           Dense ranking: ties share a rank, next score continues +1 with no
           gaps (e.g. points 90, 80, 80, 70 -> ranks 1, 2, 2, 3).
           Defaults to ALL roles; pass ?role=faculty (or hod/dean/etc.) to narrow.
    """

    def get_permissions(self):
        # Tighten these to IsHOD / IsPrincipal / IsDean if you want to lock
        # down who can see other people's data.
        return [IsAuthenticated()]

    # ------------------------------------------------------------------ #
    # MY SUMMARY
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='my-summary', methods=['get'])
    def my_summary(self, request):
        jwt_payload = _get_authenticated_user(request)
        if not jwt_payload:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            user_obj = User.objects.get(id=jwt_payload['user_id'])
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response(_build_faculty_detail(user_obj), status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # BY USER ID
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='by-user', methods=['get'])
    def by_user(self, request):
        jwt_payload = _get_authenticated_user(request)
        if not jwt_payload:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        if jwt_payload.get('role') not in PRIVILEGED_ROLES:
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
    # BY REGISTER NO (counts + points only)
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='by-register', methods=['get'])
    def by_register(self, request):
        jwt_payload = _get_authenticated_user(request)
        if not jwt_payload:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        if jwt_payload.get('role') not in PRIVILEGED_ROLES:
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
    # BY REGISTER NO — FULL DETAIL  (every module, every field)
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='by-register-full', methods=['get'])
    def by_register_full(self, request):
        """
        Enter a register_no, get back every module the faculty has any
        record in, with every field of every record, plus per-module and
        overall point totals.
        """
        jwt_payload = _get_authenticated_user(request)
        if not jwt_payload:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        if jwt_payload.get('role') not in PRIVILEGED_ROLES:
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

        return Response(_build_faculty_full_detail(user_obj, request), status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # SEARCH — across ALL users, any role
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='search', methods=['get'])
    def search_users(self, request):
        """
        Live search across every user, regardless of role.
        Matches partial register_no OR partial username (case-insensitive).

        GET /summary/faculty-summary/search/?q=21A1
        GET /summary/faculty-summary/search/?q=kumar
        GET /summary/faculty-summary/search/?q=21A1&role=hod   (optional role narrowing)
        """
        jwt_payload = _get_authenticated_user(request)
        if not jwt_payload:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({'error': 'q query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        from django.db.models import Q

        matches = User.objects.filter(
            Q(register_no__icontains=query) | Q(username__icontains=query)
        )

        role_filter = request.query_params.get('role')
        if role_filter:
            matches = matches.filter(role=role_filter)

        matches = matches.order_by('register_no')[:25]   # cap results for a search box
        matches = list(matches)

        image_urls = _profile_image_urls_for_users(matches)
        results = [_serialize_basic_user(u, image_urls.get(u.id)) for u in matches]
        return Response({'count': len(results), 'results': results}, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # TOTAL POINTS — own
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='total-points', methods=['get'])
    def total_points(self, request):
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
    # TOTAL POINTS BY USER ID
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='total-points-by-user', methods=['get'])
    def total_points_by_user(self, request):
        jwt_payload = _get_authenticated_user(request)
        if not jwt_payload:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        if jwt_payload.get('role') not in PRIVILEGED_ROLES:
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
    # DASHBOARD  – full module detail + live rank, in one call
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='dashboard', methods=['get'])
    def dashboard(self, request):
        """
        The all-in-one screen: enter a register_no and get back
          - every module, every record, every field (same as by-register-full)
          - that faculty's current rank among their peers (dense rank: 1,2,2,3)
          - how many points separate them from the #1 spot

        GET /summary/faculty-summary/dashboard/?register_no=21A1234&role=faculty
        """
        jwt_payload = _get_authenticated_user(request)
        if not jwt_payload:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        register_no = request.query_params.get('register_no')
        if not register_no:
            return Response({'error': 'register_no query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user_obj = User.objects.get(register_no=register_no)
        except User.DoesNotExist:
            return Response({'error': 'User not found for the given register_no.'}, status=status.HTTP_404_NOT_FOUND)

        # Full per-module breakdown for this one user.
        full_detail = _build_faculty_full_detail(user_obj, request)

        # Rank that user against their peer group. Defaults to ALL users now;
        # pass ?role=<role> to narrow the comparison to one role.
        role_filter = request.query_params.get('role', 'all')
        peers = User.objects.all() if role_filter == 'all' else User.objects.filter(role=role_filter)

        rows = []
        for u in peers:
            detail = _build_faculty_detail(u)
            rows.append({
                'user_id':      u.id,
                'register_no':  u.register_no,
                'username':     u.username,
                'total_points': detail['total_points'],
            })
        rows.sort(key=lambda r: (-r['total_points'], r['username'] or ''))
        ranked_rows = _assign_ranks(rows)

        my_rank_row = _rank_of_user(ranked_rows, user_obj.id)
        top_score = ranked_rows[0]['total_points'] if ranked_rows else 0
        points_behind_first = max(top_score - full_detail['total_points'], 0)

        full_detail['rank'] = my_rank_row['rank'] if my_rank_row else None
        full_detail['peer_group_size'] = len(ranked_rows)
        full_detail['points_behind_first'] = points_behind_first
        full_detail['profile_image_url'] = _profile_image_urls_for_users([user_obj]).get(user_obj.id)

        return Response(full_detail, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # ALL FACULTY  – list with points (unranked, register_no order)
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='all-faculty', methods=['get'])
    def all_faculty(self, request):
        jwt_payload = _get_authenticated_user(request)
        if not jwt_payload:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        if jwt_payload.get('role') not in PRIVILEGED_ROLES:
            return Response(
                {'error': 'You do not have permission to list all faculty.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Defaults to ALL roles now; pass ?role=faculty (or hod/dean/etc.) to narrow.
        role_filter = request.query_params.get('role', 'all')
        users = User.objects.all() if role_filter == 'all' else User.objects.filter(role=role_filter)
        users = list(users.order_by('register_no'))

        image_urls = _profile_image_urls_for_users(users)

        results = []
        for u in users:
            detail = _build_faculty_detail(u)
            results.append({
                'user_id':           u.id,
                'register_no':       u.register_no,
                'username':          u.username,
                'email':             u.email,
                'total_points':      detail['total_points'],
                'profile_image_url': image_urls.get(u.id),
            })

        return Response({'count': len(results), 'faculty': results}, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------ #
    # LEADERBOARD  – all faculty ranked by points, highest first
    # ------------------------------------------------------------------ #
    @action(detail=False, url_path='leaderboard', methods=['get'])
    def leaderboard(self, request):
        """
        Ranks every faculty member by total approved points, descending.
        ?role=faculty (default) — pass ?role=all to include every role.
        Dense ranking: ties share a rank, next distinct score continues at
        rank+1 with no gaps (e.g. points 90, 80, 80, 70 -> ranks 1, 2, 2, 3).
        """
        jwt_payload = _get_authenticated_user(request)
        if not jwt_payload:
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)

        role_filter = request.query_params.get('role', 'all')
        users = User.objects.all() if role_filter == 'all' else User.objects.filter(role=role_filter)
        users = list(users)

        image_urls = _profile_image_urls_for_users(users)

        rows = []
        for u in users:
            detail = _build_faculty_detail(u)
            rows.append({
                'user_id':           u.id,
                'register_no':       u.register_no,
                'username':          u.username,
                'email':             u.email,
                'role':              u.role,
                'total_points':      detail['total_points'],
                'profile_image_url': image_urls.get(u.id),
            })

        # Highest points first; stable secondary sort by username for a
        # deterministic order among exact ties.
        rows.sort(key=lambda r: (-r['total_points'], r['username'] or ''))

        ranked_rows = _assign_ranks(rows)

        return Response(
            {'count': len(ranked_rows), 'leaderboard': ranked_rows},
            status=status.HTTP_200_OK,
        )