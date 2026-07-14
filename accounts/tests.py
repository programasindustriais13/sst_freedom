from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class SafeLogoutViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.username = "testuser"
        self.password = "testpass123"
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password
        )

    def test_logout_post(self):
        """Test logging out using a POST request."""
        # Log the user in first
        self.assertTrue(self.client.login(username=self.username, password=self.password))
        
        # Perform POST request to logout
        response = self.client.post(reverse('logout'))
        
        # Check that we got redirected to login
        self.assertRedirects(response, reverse('login'))
        
        # Check that the user is no longer authenticated
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_get(self):
        """Test logging out using a GET request (supported by SafeLogoutView)."""
        # Log the user in first
        self.assertTrue(self.client.login(username=self.username, password=self.password))
        
        # Perform GET request to logout
        response = self.client.get(reverse('logout'))
        
        # Check that we got redirected to login
        self.assertRedirects(response, reverse('login'))
        
        # Check that the user is no longer authenticated
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_service_worker_status_ok(self):
        """Test that /service-worker.js returns status 200 and javascript content type."""
        response = self.client.get('/service-worker.js')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get('Content-Type'), 'application/javascript')

