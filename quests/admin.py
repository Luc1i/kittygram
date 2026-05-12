from django.contrib import admin

from .models import QuestParticipation, QuestStep, QuestStepProgress, QuestWeek


class QuestStepInline(admin.TabularInline):
    model = QuestStep
    extra = 0


@admin.register(QuestWeek)
class QuestWeekAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'slug',
        'week_start',
        'week_end',
        'is_published',
        'max_participants',
        'created_at',
    )
    list_filter = ('is_published',)
    search_fields = ('title', 'slug', 'description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [QuestStepInline]


@admin.register(QuestStep)
class QuestStepAdmin(admin.ModelAdmin):
    list_display = ('quest_week', 'order', 'title', 'points', 'related_cat')
    list_filter = ('quest_week',)
    ordering = ('quest_week', 'order')


@admin.register(QuestParticipation)
class QuestParticipationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'quest_week', 'status', 'joined_at')
    list_filter = ('status', 'quest_week')
    search_fields = ('user__username',)


@admin.register(QuestStepProgress)
class QuestStepProgressAdmin(admin.ModelAdmin):
    list_display = ('id', 'participation', 'step', 'is_completed', 'completed_at')
    list_filter = ('is_completed',)
