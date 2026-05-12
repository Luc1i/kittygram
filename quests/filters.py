import django_filters

from .models import QuestStep, QuestWeek


class QuestWeekFilter(django_filters.FilterSet):
    week_start_after = django_filters.DateFilter(field_name='week_start', lookup_expr='gte')
    week_start_before = django_filters.DateFilter(field_name='week_start', lookup_expr='lte')
    week_end_after = django_filters.DateFilter(field_name='week_end', lookup_expr='gte')
    week_end_before = django_filters.DateFilter(field_name='week_end', lookup_expr='lte')

    class Meta:
        model = QuestWeek
        fields = ['is_published']


class QuestStepFilter(django_filters.FilterSet):
    class Meta:
        model = QuestStep
        fields = ['quest_week']
