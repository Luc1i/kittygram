from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    QuestParticipationViewSet,
    QuestStepProgressViewSet,
    QuestStepViewSet,
    QuestWeekViewSet,
)

router = DefaultRouter()
router.register(r'quest-weeks', QuestWeekViewSet, basename='quest-week')
router.register(r'quest-steps', QuestStepViewSet, basename='quest-step')
router.register(r'participations', QuestParticipationViewSet, basename='quest-participation')
router.register(r'step-progress', QuestStepProgressViewSet, basename='quest-step-progress')

urlpatterns = [
    path('', include(router.urls)),
]
