from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from django.test import override_settings

from .models import EmailOTP, Profile


class ProfileDeviceStateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='device-user',
            email='device@example.com',
            password='StrongPass123!',
        )
        self.profile = Profile.objects.create(user=self.user)
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_device_state_endpoint_updates_permissions_and_coordinates(self):
        response = self.client.patch(
            '/api/users/profile/device-state/',
            {
                'phone_permission_granted': True,
                'location_permission_granted': True,
                'latitude': 28.6139,
                'longitude': 77.2090,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.phone_permission_granted)
        self.assertTrue(self.profile.location_permission_granted)
        self.assertEqual(self.profile.latitude, 28.6139)
        self.assertEqual(self.profile.longitude, 77.2090)
        self.assertIsNotNone(self.profile.location_timestamp)

    def test_device_state_requires_complete_coordinate_pair(self):
        response = self.client.patch(
            '/api/users/profile/device-state/',
            {'latitude': 28.6139},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('location', response.data)


class OTPDeliveryTests(APITestCase):
    @override_settings(DEBUG=True, EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend')
    def test_register_returns_debug_otp_when_console_backend_is_used(self):
        response = self.client.post(
            '/api/users/register/',
            {'email': 'otp-console@example.com'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['delivery_method'], 'console')
        self.assertIn('debug_otp', response.data)
        self.assertEqual(len(response.data['debug_otp']), 6)
        self.assertTrue(
            EmailOTP.objects.filter(
                email='otp-console@example.com',
                purpose='register',
                code=response.data['debug_otp'],
            ).exists()
        )

    @override_settings(DEBUG=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_register_marks_non_console_backends_as_email_delivery(self):
        response = self.client.post(
            '/api/users/register/',
            {'email': 'otp-email@example.com'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['delivery_method'], 'email')
        self.assertNotIn('debug_otp', response.data)
