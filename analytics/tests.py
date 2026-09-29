from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class AdminAnalyticsDashboardTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='password123',
            is_staff=True,
            is_superuser=True
        )
        self.regular_user = User.objects.create_user(
            username='regular_test',
            password='password123',
            is_staff=False
        )

    def test_unauthorized_user_cannot_access_dashboard(self):
        """
        Regular non-staff users cannot access the business intelligence dashboard.
        """
        self.client.login(username='regular_test', password='password123')
        response = self.client.get(reverse('analytics:dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)

    def test_admin_can_access_dashboard(self):
        """
        Staff administrators can access the dashboard.
        """
        self.client.login(username='admin_test', password='password123')
        response = self.client.get(reverse('analytics:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cinema Operations Dashboard")
        self.assertContains(response, "Real-Time Business Intelligence")

    def test_csv_exports(self):
        """
        Verify CSV report export endpoints return valid CSV files.
        """
        self.client.login(username='admin_test', password='password123')

        for export_url in [
            reverse('analytics:export_revenue'),
            reverse('analytics:export_occupancy'),
            reverse('analytics:export_bookings')
        ]:
            response = self.client.get(export_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'text/csv')
            self.assertIn('attachment;', response['Content-Disposition'])
