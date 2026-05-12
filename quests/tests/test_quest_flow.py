from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from cats.models import Cat
from quests.models import QuestParticipation, QuestStep, QuestWeek

User = get_user_model()


class QuestAPITests(APITestCase):
    def setUp(self):
        today = timezone.now().date()
        self.week = QuestWeek.objects.create(
            title='Тестовая неделя',
            slug='test-week',
            description='',
            week_start=today,
            week_end=today,
            is_published=True,
            max_participants=10,
        )
        self.cat = Cat.objects.create(name='Барсик', color='белый', birth_year=2019)
        self.step1 = QuestStep.objects.create(
            quest_week=self.week,
            order=1,
            title='Шаг 1',
            description='',
            points=3,
            related_cat=self.cat,
        )
        self.step2 = QuestStep.objects.create(
            quest_week=self.week,
            order=2,
            title='Шаг 2',
            description='',
            points=7,
            related_cat=None,
        )
        self.user = User.objects.create_user(username='player', password='secretpass123')
        self.token = Token.objects.create(user=self.user)
        self.other = User.objects.create_user(username='other', password='secretpass123')
        self.other_token = Token.objects.create(user=self.other)

    def test_enroll_and_complete_flow(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        url = f'/api/quest-weeks/{self.week.pk}/enroll/'
        r = self.client.post(url)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        pid = r.data['id']
        r2 = self.client.post(url)
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(r2.data.get('code'), 'already_enrolled')

        r3 = self.client.post(
            f'/api/participations/{pid}/complete_step/',
            {'step_id': self.step2.pk},
            format='json',
        )
        self.assertEqual(r3.status_code, status.HTTP_400_BAD_REQUEST)

        r4 = self.client.post(
            f'/api/participations/{pid}/complete_step/',
            {'step_id': self.step1.pk},
            format='json',
        )
        self.assertEqual(r4.status_code, status.HTTP_200_OK)
        r5 = self.client.post(
            f'/api/participations/{pid}/complete_step/',
            {'step_id': self.step2.pk},
            format='json',
        )
        self.assertEqual(r5.status_code, status.HTTP_200_OK)
        p = QuestParticipation.objects.get(pk=pid)
        self.assertEqual(p.status, QuestParticipation.Status.COMPLETED)

    def test_complete_step_forbidden_for_other_user(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        r = self.client.post(f'/api/quest-weeks/{self.week.pk}/enroll/')
        pid = r.data['id']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.other_token.key}')
        resp = self.client.post(
            f'/api/participations/{pid}/complete_step/',
            {'step_id': self.step1.pk},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_leaderboard(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.client.post(f'/api/quest-weeks/{self.week.pk}/enroll/')
        self.client.credentials()
        r = self.client.get(f'/api/quest-weeks/{self.week.pk}/leaderboard/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn('results', r.data)

    def test_cats_legacy_unchanged(self):
        r = self.client.get('/cats/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        r2 = self.client.post(
            '/cats/',
            {'name': 'Том', 'color': 'серый', 'birth_year': 2021},
            format='json',
        )
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.data['name'], 'Том')
