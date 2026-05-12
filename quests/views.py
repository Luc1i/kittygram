from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.deletion import ProtectedError
from django.db.models.functions import Coalesce
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import mixins, permissions, serializers, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .filters import QuestStepFilter, QuestWeekFilter
from .models import QuestParticipation, QuestStep, QuestStepProgress, QuestWeek
from .permissions import IsOwnerOrStaff, IsStaff
from .serializers import (
    QuestParticipationSerializer,
    QuestStepProgressSerializer,
    QuestStepSerializer,
    QuestWeekSerializer,
    StaffKeySerializer,
    StepCompleteSerializer,
    UserRegisterSerializer,
)

User = get_user_model()


class QuestWeekViewSet(viewsets.ModelViewSet):
    queryset = QuestWeek.objects.all().prefetch_related('steps')
    serializer_class = QuestWeekSerializer
    filterset_class = QuestWeekFilter
    search_fields = ('title', 'slug', 'description')
    ordering_fields = ('week_start', 'week_end', 'created_at', 'title', 'id')
    ordering = ('-week_start', '-id')
    lookup_field = 'pk'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return qs
        return qs.filter(is_published=True)

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsStaff()]
        if self.action == 'enroll':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.participations.filter(status=QuestParticipation.Status.ACTIVE).exists():
            return Response(
                {
                    'code': 'active_participants',
                    'detail': 'есть активные участники, удалять нельзя',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='enroll')
    def enroll(self, request, pk=None):
        week = self.get_object()
        user = request.user
        today = timezone.now().date()

        if not week.is_published:
            return Response(
                {'code': 'not_published', 'detail': 'неделя не опубликована'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not (week.week_start <= today <= week.week_end):
            return Response(
                {'code': 'enrollment_closed', 'detail': 'запись не в датах недели'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if week.max_participants is not None:
            occupied = QuestParticipation.objects.filter(
                quest_week=week,
                status__in=(
                    QuestParticipation.Status.ACTIVE,
                    QuestParticipation.Status.COMPLETED,
                ),
            ).count()
            if occupied >= week.max_participants:
                return Response(
                    {'code': 'quest_full', 'detail': 'мест нет'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        existing = QuestParticipation.objects.filter(user=user, quest_week=week).first()
        if existing:
            if existing.status == QuestParticipation.Status.ACTIVE:
                return Response(
                    {'code': 'already_enrolled', 'detail': 'уже записаны'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if existing.status == QuestParticipation.Status.COMPLETED:
                return Response(
                    {'code': 'already_completed', 'detail': 'квест этой недели уже пройден'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if existing.status == QuestParticipation.Status.DROPPED:
                with transaction.atomic():
                    existing.status = QuestParticipation.Status.ACTIVE
                    existing.save(update_fields=['status'])
                    existing.progresses.all().update(is_completed=False, completed_at=None)
                ser = QuestParticipationSerializer(existing, context={'request': request})
                return Response(ser.data, status=status.HTTP_200_OK)

        with transaction.atomic():
            participation = QuestParticipation.objects.create(
                user=user,
                quest_week=week,
                status=QuestParticipation.Status.ACTIVE,
            )
            steps = list(QuestStep.objects.filter(quest_week=week).order_by('order'))
            QuestStepProgress.objects.bulk_create(
                [
                    QuestStepProgress(
                        participation=participation,
                        step=s,
                        is_completed=False,
                    )
                    for s in steps
                ]
            )
        ser = QuestParticipationSerializer(participation, context={'request': request})
        return Response(ser.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='leaderboard')
    def leaderboard(self, request, pk=None):
        week = self.get_object()
        limit = min(int(request.query_params.get('limit', 10)), 50)
        rows = (
            QuestParticipation.objects.filter(
                quest_week=week,
                status__in=(
                    QuestParticipation.Status.ACTIVE,
                    QuestParticipation.Status.COMPLETED,
                ),
            )
            .select_related('user')
            .annotate(
                total_points=Coalesce(
                    Sum('progresses__step__points', filter=Q(progresses__is_completed=True)),
                    0,
                )
            )
            .order_by('-total_points', 'joined_at')[:limit]
        )
        data = [
            {
                'user_id': r.user_id,
                'username': r.user.username,
                'total_points': int(r.total_points or 0),
                'status': r.status,
            }
            for r in rows
        ]
        return Response({'quest_week': week.id, 'results': data})

    @action(detail=False, methods=['get'], url_path='current')
    def current(self, request):
        today = timezone.now().date()
        qs = self.filter_queryset(self.get_queryset())
        week = (
            qs.filter(week_start__lte=today, week_end__gte=today)
            .order_by('-week_start')
            .first()
        )
        if not week:
            return Response({'detail': 'нет подходящей недели на сегодня'}, status=404)
        ser = self.get_serializer(week)
        return Response(ser.data)


class QuestStepViewSet(viewsets.ModelViewSet):
    queryset = QuestStep.objects.select_related('quest_week', 'related_cat').all()
    serializer_class = QuestStepSerializer
    filterset_class = QuestStepFilter
    ordering_fields = ('order', 'id', 'points')
    ordering = ('quest_week', 'order')

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.is_staff:
            return qs
        return qs.filter(quest_week__is_published=True)

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsStaff()]
        return [permissions.AllowAny()]

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    'detail': 'шаг нельзя удалить, есть прогресс',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class QuestParticipationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = QuestParticipation.objects.select_related('quest_week', 'user').prefetch_related(
        'progresses__step',
    )
    serializer_class = QuestParticipationSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrStaff]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return qs
        return qs.filter(user=user)

    def partial_update(self, request, *args, **kwargs):
        if set(request.data.keys()) - {'status'}:
            return Response(
                {'detail': 'только status = dropped'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().partial_update(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='complete_step')
    def complete_step(self, request, pk=None):
        participation = self.get_object()
        if participation.user_id != request.user.id:
            return Response(
                {'detail': 'чужое участие'},
                status=status.HTTP_403_FORBIDDEN,
            )
        ser = StepCompleteSerializer(
            data=request.data,
            context={'participation': participation, 'request': request},
        )
        ser.is_valid(raise_exception=True)
        progress: QuestStepProgress = ser.validated_data['progress']
        now = timezone.now()
        with transaction.atomic():
            progress.is_completed = True
            progress.completed_at = now
            progress.save(update_fields=['is_completed', 'completed_at'])
            total_steps = QuestStep.objects.filter(quest_week_id=participation.quest_week_id).count()
            done = participation.progresses.filter(is_completed=True).count()
            if total_steps and done >= total_steps:
                participation.status = QuestParticipation.Status.COMPLETED
                participation.save(update_fields=['status'])
        participation.refresh_from_db()
        out = QuestParticipationSerializer(participation, context={'request': request})
        return Response(out.data, status=status.HTTP_200_OK)


class QuestStepProgressViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = QuestStepProgress.objects.select_related('participation', 'step').all()
    serializer_class = QuestStepProgressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrStaff]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return qs
        return qs.filter(participation__user=user)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary='Регистрация',
        description='Логин, пароль, опционально staff_key если совпадает с .env',
        request=UserRegisterSerializer,
        responses={
            201: inline_serializer(
                name='RegisterResponse',
                fields={
                    'token': serializers.CharField(),
                    'user_id': serializers.IntegerField(),
                    'username': serializers.CharField(),
                    'is_staff': serializers.BooleanField(),
                },
            ),
        },
        auth=[],
    )
    def post(self, request):
        ser = UserRegisterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        incoming_key = (request.data.get('staff_key') or '').strip()
        with transaction.atomic():
            user = ser.save()
            if (
                settings.REGISTER_STAFF_KEY
                and incoming_key == settings.REGISTER_STAFF_KEY
            ):
                user.is_staff = True
                user.save(update_fields=['is_staff'])
            token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                'token': token.key,
                'user_id': user.pk,
                'username': user.username,
                'is_staff': user.is_staff,
            },
            status=status.HTTP_201_CREATED,
        )


class PromoteSelfStaffView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary='Сделать себя staff по ключу',
        description='Тело: staff_key как в REGISTER_STAFF_KEY. Нужен токен.',
        request=StaffKeySerializer,
        responses={
            200: inline_serializer(
                name='PromoteSelfResponse',
                fields={
                    'is_staff': serializers.BooleanField(),
                    'username': serializers.CharField(),
                },
            ),
        },
    )
    def post(self, request):
        if not settings.REGISTER_STAFF_KEY:
            return Response(
                {
                    'detail': 'в .env нет REGISTER_STAFF_KEY',
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        ser = StaffKeySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if ser.validated_data['staff_key'] != settings.REGISTER_STAFF_KEY:
            return Response(
                {'detail': 'ключ не тот'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = request.user
        user.is_staff = True
        user.save(update_fields=['is_staff'])
        return Response({'is_staff': True, 'username': user.username})


class LoginTokenView(ObtainAuthToken):

    @extend_schema(
        summary='Токен по логину/паролю',
        request=AuthTokenSerializer,
        responses={
            200: inline_serializer(
                name='TokenResponse',
                fields={'token': serializers.CharField()},
            ),
        },
        auth=[],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
