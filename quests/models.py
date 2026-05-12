from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class QuestWeek(models.Model):
    title = models.CharField('название', max_length=200)
    slug = models.SlugField('slug', max_length=200, unique=True)
    description = models.TextField('описание', blank=True)
    week_start = models.DateField('начало недели')
    week_end = models.DateField('конец недели')
    is_published = models.BooleanField('опубликован', default=False)
    max_participants = models.PositiveIntegerField(
        'макс. участников',
        null=True,
        blank=True,
        help_text='если пусто — без лимита',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='создал',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quest_weeks_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'неделя квестов'
        verbose_name_plural = 'недели квестов'
        ordering = ['-week_start', '-id']
        constraints = [
            models.CheckConstraint(
                check=Q(week_end__gte=models.F('week_start')),
                name='questweek_week_end_gte_week_start',
            ),
            models.CheckConstraint(
                check=Q(max_participants__isnull=True) | Q(max_participants__gte=1),
                name='questweek_max_participants_null_or_positive',
            ),
        ]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.week_end < self.week_start:
            raise ValidationError({'week_end': 'конец раньше начала'})
        if self.max_participants is not None and self.max_participants < 1:
            raise ValidationError({'max_participants': 'лимит 1 и больше, или пусто'})


class QuestStep(models.Model):
    quest_week = models.ForeignKey(
        QuestWeek,
        verbose_name='неделя',
        on_delete=models.CASCADE,
        related_name='steps',
    )
    order = models.PositiveSmallIntegerField('порядок', db_index=True)
    title = models.CharField('заголовок', max_length=200)
    description = models.TextField('текст задания', blank=True)
    points = models.PositiveSmallIntegerField('очки', default=1)
    related_cat = models.ForeignKey(
        'cats.Cat',
        verbose_name='кот из каталога',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quest_steps',
    )

    class Meta:
        verbose_name = 'шаг квеста'
        verbose_name_plural = 'шаги квестов'
        ordering = ['quest_week_id', 'order']
        constraints = [
            models.UniqueConstraint(
                fields=['quest_week', 'order'],
                name='queststep_unique_order_per_week',
            ),
            models.CheckConstraint(
                check=Q(points__gte=1),
                name='queststep_points_gte_1',
            ),
        ]

    def __str__(self):
        return f'{self.quest_week.slug}#{self.order} {self.title}'


class QuestParticipation(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Активен'
        COMPLETED = 'completed', 'Завершён'
        DROPPED = 'dropped', 'Брошен'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='пользователь',
        on_delete=models.CASCADE,
        related_name='quest_participations',
    )
    quest_week = models.ForeignKey(
        QuestWeek,
        verbose_name='неделя',
        on_delete=models.CASCADE,
        related_name='participations',
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        'статус',
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    class Meta:
        verbose_name = 'участие'
        verbose_name_plural = 'участия'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'quest_week'],
                name='questparticipation_unique_user_week',
            ),
        ]

    def __str__(self):
        return f'{self.user_id} → {self.quest_week.slug}'


class QuestStepProgress(models.Model):
    participation = models.ForeignKey(
        QuestParticipation,
        verbose_name='участие',
        on_delete=models.CASCADE,
        related_name='progresses',
    )
    step = models.ForeignKey(
        QuestStep,
        verbose_name='шаг',
        on_delete=models.PROTECT,
        related_name='progress_rows',
    )
    is_completed = models.BooleanField('выполнен', default=False)
    completed_at = models.DateTimeField('когда выполнили', null=True, blank=True)

    class Meta:
        verbose_name = 'прогресс шага'
        verbose_name_plural = 'прогресс шагов'
        constraints = [
            models.UniqueConstraint(
                fields=['participation', 'step'],
                name='queststepprogress_unique_participation_step',
            ),
        ]

    def __str__(self):
        return f'{self.participation_id} step {self.step_id}'
