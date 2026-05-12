from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import QuestParticipation, QuestStep, QuestStepProgress, QuestWeek

User = get_user_model()


class QuestWeekSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestWeek
        fields = (
            'id',
            'title',
            'slug',
            'description',
            'week_start',
            'week_end',
            'is_published',
            'max_participants',
            'created_by',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')

    def validate(self, attrs):
        week_start = attrs.get('week_start', getattr(self.instance, 'week_start', None))
        week_end = attrs.get('week_end', getattr(self.instance, 'week_end', None))
        if week_start and week_end and week_end < week_start:
            raise serializers.ValidationError(
                {'week_end': 'конец раньше начала'}
            )
        instance = self.instance
        request = self.context.get('request')
        if instance and request and request.user.is_staff:
            critical = {'week_start', 'week_end', 'slug'} & set(attrs.keys())
            if critical and instance.participations.filter(
                status=QuestParticipation.Status.ACTIVE
            ).exists():
                raise serializers.ValidationError(
                    {
                        'code': 'active_participants',
                        'detail': 'нельзя менять slug/даты пока кто-то в active',
                    }
                )
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            validated_data['created_by'] = user
        return super().create(validated_data)


class QuestStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestStep
        fields = (
            'id',
            'quest_week',
            'order',
            'title',
            'description',
            'points',
            'related_cat',
        )
        read_only_fields = ('id',)


class QuestStepProgressSerializer(serializers.ModelSerializer):
    step_detail = QuestStepSerializer(source='step', read_only=True)

    class Meta:
        model = QuestStepProgress
        fields = (
            'id',
            'participation',
            'step',
            'step_detail',
            'is_completed',
            'completed_at',
        )
        read_only_fields = (
            'id',
            'participation',
            'step',
            'step_detail',
            'is_completed',
            'completed_at',
        )


class QuestParticipationSerializer(serializers.ModelSerializer):
    progresses = QuestStepProgressSerializer(many=True, read_only=True)
    quest_week_detail = QuestWeekSerializer(source='quest_week', read_only=True)

    class Meta:
        model = QuestParticipation
        fields = (
            'id',
            'user',
            'quest_week',
            'quest_week_detail',
            'joined_at',
            'status',
            'progresses',
        )
        read_only_fields = ('id', 'user', 'quest_week', 'joined_at', 'progresses', 'quest_week_detail')

    def validate_status(self, value):
        if value not in (QuestParticipation.Status.DROPPED,):
            raise serializers.ValidationError('только dropped')
        return value


class StepCompleteSerializer(serializers.Serializer):
    step_id = serializers.IntegerField()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        participation: QuestParticipation = self.context['participation']
        try:
            step = QuestStep.objects.get(
                pk=attrs['step_id'],
                quest_week_id=participation.quest_week_id,
            )
        except QuestStep.DoesNotExist:
            raise serializers.ValidationError(
                {'step_id': 'шаг не из этой недели'}
            )
        if participation.status != QuestParticipation.Status.ACTIVE:
            raise serializers.ValidationError(
                {'code': 'participation_inactive', 'detail': 'участие не active'}
            )
        try:
            progress = QuestStepProgress.objects.get(
                participation=participation,
                step=step,
            )
        except QuestStepProgress.DoesNotExist:
            raise serializers.ValidationError({'step_id': 'нет прогресса'})

        if progress.is_completed:
            raise serializers.ValidationError({'code': 'step_already_done', 'detail': 'уже сделано'})

        prior_steps = QuestStep.objects.filter(
            quest_week_id=participation.quest_week_id,
            order__lt=step.order,
        ).order_by('order')
        for prior in prior_steps:
            prior_progress = QuestStepProgress.objects.filter(
                participation=participation,
                step=prior,
            ).first()
            if not prior_progress or not prior_progress.is_completed:
                raise serializers.ValidationError(
                    {
                        'code': 'previous_steps_incomplete',
                        'detail': 'сначала предыдущие по order',
                    }
                )
        attrs['step'] = step
        attrs['progress'] = progress
        return attrs


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    staff_key = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text='если как в REGISTER_STAFF_KEY в .env — сразу staff',
    )

    class Meta:
        model = User
        fields = ('username', 'password', 'staff_key')

    def create(self, validated_data):
        validated_data.pop('staff_key', None)
        return User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
        )


class StaffKeySerializer(serializers.Serializer):
    staff_key = serializers.CharField()
