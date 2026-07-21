from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from organizations.models import Company, Unit
from notifications.models import Alert

User = get_user_model()

class AlertFilterTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_superuser(username="admin_notif", email="admin_notif@example.com", password="password123")
        self.company = Company.objects.create(razao_social="Empresa Notif LTDA", cnpj="12345678000177")
        self.unit = Unit.objects.create(company=self.company, codigo="U-NOTIF", nome="Unidade Notif")
        self.user.units.add(self.unit)

        self.alert1 = Alert.objects.create(unit=self.unit, severity="CRITICAL", title="Alerta Crítico EPI", message="Troca urgente", status="NOVO")
        self.alert2 = Alert.objects.create(unit=self.unit, severity="INFO", title="Aviso Informativo", message="Treinamento agendado", status="NOVO")

    def test_alert_list_filter(self):
        self.client.force_login(self.user)
        url = reverse('alert_list')
        
        # Test filter by text 'Crítico'
        response = self.client.get(url, {'q': 'Crítico'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['alerts']), 1)
        self.assertEqual(response.context['alerts'][0].id, self.alert1.id)
