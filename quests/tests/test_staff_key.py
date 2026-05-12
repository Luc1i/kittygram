from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

User = get_user_model()


@override_settings(REGISTER_STAFF_KEY='test-secret-key')
class StaffKeyAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_with_staff_key_sets_is_staff(self):
        r = self.client.post(
            '/api/auth/register/',
            {
                'username': 'staffuser',
                'password': 'longpassword1',
                'staff_key': 'test-secret-key',
            },
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertTrue(r.data.get('is_staff'))
        u = User.objects.get(username='staffuser')
        self.assertTrue(u.is_staff)

    def test_register_wrong_staff_key_not_staff(self):
        r = self.client.post(
            '/api/auth/register/',
            {
                'username': 'plainuser',
                'password': 'longpassword1',
                'staff_key': 'wrong',
            },
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertFalse(r.data.get('is_staff'))

    def test_promote_self(self):
        u = User.objects.create_user(username='olduser', password='longpassword1')
        tok = Token.objects.create(user=u)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {tok.key}')
        r = self.client.post(
            '/api/auth/promote-self/',
            {'staff_key': 'test-secret-key'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertTrue(r.data.get('is_staff'))
        u.refresh_from_db()
        self.assertTrue(u.is_staff)


@override_settings(REGISTER_STAFF_KEY='')
class StaffKeyDisabledTests(TestCase):
    def test_promote_self_forbidden_when_key_empty(self):
        client = APIClient()
        u = User.objects.create_user(username='u1', password='longpassword1')
        tok = Token.objects.create(user=u)
        client.credentials(HTTP_AUTHORIZATION=f'Token {tok.key}')
        r = client.post('/api/auth/promote-self/', {'staff_key': 'x'}, format='json')
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
