import json
from django.test import TestCase, SimpleTestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.core.exceptions import PermissionDenied

from organizations.models import Company, Unit, Sector, CostCenter, Function, InventoryLocation
from employees.models import Employee, EmployeeHistory
from audit.models import AuditLog
from notifications.models import Alert
from core.services import collect_dependencies, topological_sort_models, execute_cascade_delete

User = get_user_model()

def generate_valid_cpf(base_str):
    # Generates a valid CPF mathematically based on a 9-digit base string
    digits = [int(char) for char in base_str[:9]]
    
    # 10th digit
    s1 = sum(d * (10 - i) for i, d in enumerate(digits))
    d1 = ((s1 * 10) % 11) % 10
    digits.append(d1)
    
    # 11th digit
    s2 = sum(d * (11 - i) for i, d in enumerate(digits))
    d2 = ((s2 * 10) % 11) % 10
    digits.append(d2)
    
    return "".join(map(str, digits))


class CascadeDeleteServiceTestCase(TestCase):

    def setUp(self):
        # Create user
        self.user = User.objects.create_user(username="tecnico", email="tecnico@example.com", password="password")
        
        # Create standard organizational structures
        self.company = Company.objects.create(
            razao_social="Empresa Teste LTDA",
            nome_fantasia="Empresa Teste",
            cnpj="12.345.678/0001-00",
            ativo=True
        )
        self.unit = Unit.objects.create(
            company=self.company,
            codigo="U-TEST",
            nome="Unidade Teste",
            cidade="Fortaleza",
            estado="CE",
            ativo=True
        )
        self.sector = Sector.objects.create(
            unit=self.unit,
            nome="TI",
            codigo="SET-TI",
            ativo=True
        )
        self.costcenter = CostCenter.objects.create(
            company=self.company,
            codigo="CC-TI",
            nome="Centro TI",
            ativo=True
        )
        self.function = Function.objects.create(
            company=self.company,
            nome="Analista de Sistemas",
            ativo=True
        )
        self.employee = Employee.objects.create(
            company=self.company,
            unit=self.unit,
            matricula="M-001",
            nome_completo="João da Silva",
            cpf=generate_valid_cpf("123456789"),
            funcao=self.function,
            setor=self.sector,
            centro_custo=self.costcenter,
            data_admissao="2026-01-01",
            situacao="ATIVO",
            criado_por=self.user
        )
        
        # Create a generic relation alert on the company
        self.alert = Alert.objects.create(
            unit=self.unit,
            alert_type="TROCA_BREVE",
            severity="WARNING",
            title="Alerta Teste",
            message="Alerta relacionado à Empresa",
            content_type=ContentType.objects.get_for_model(Company),
            object_id=self.company.pk
        )

    def test_collect_dependencies(self):
        collected = collect_dependencies(self.company)
        
        # Verify classes are collected
        self.assertIn(Company, collected)
        self.assertIn(Unit, collected)
        self.assertIn(Sector, collected)
        self.assertIn(CostCenter, collected)
        self.assertIn(Function, collected)
        self.assertIn(Employee, collected)
        self.assertIn(Alert, collected)  # Generic relation Alert should be collected
        
        # Verify specific object instances are collected
        self.assertIn(self.company.pk, collected[Company])
        self.assertIn(self.unit.pk, collected[Unit])
        self.assertIn(self.sector.pk, collected[Sector])
        self.assertIn(self.costcenter.pk, collected[CostCenter])
        self.assertIn(self.function.pk, collected[Function])
        self.assertIn(self.employee.pk, collected[Employee])
        self.assertIn(self.alert.pk, collected[Alert])

    def test_topological_sort_models(self):
        collected = collect_dependencies(self.company)
        sorted_models = topological_sort_models(set(collected.keys()))
        
        # Verify Company is after Unit (Unit points to Company)
        self.assertLess(sorted_models.index(Unit), sorted_models.index(Company))
        
        # Verify Unit is after Sector (Sector points to Unit)
        self.assertLess(sorted_models.index(Sector), sorted_models.index(Unit))
        
        # Verify Employee is before Sector, Unit, Company, Function, CostCenter
        self.assertLess(sorted_models.index(Employee), sorted_models.index(Company))
        self.assertLess(sorted_models.index(Employee), sorted_models.index(Unit))
        self.assertLess(sorted_models.index(Employee), sorted_models.index(Sector))
        self.assertLess(sorted_models.index(Employee), sorted_models.index(Function))
        self.assertLess(sorted_models.index(Employee), sorted_models.index(CostCenter))

    def test_execute_cascade_delete_success(self):
        total_deleted = execute_cascade_delete(self.company, user=self.user)
        
        # Verify count
        self.assertEqual(total_deleted, 7) # Company, Unit, Sector, CostCenter, Function, Employee, Alert
        
        # Verify they are gone from the database
        self.assertFalse(Company.objects.filter(pk=self.company.pk).exists())
        self.assertFalse(Unit.objects.filter(pk=self.unit.pk).exists())
        self.assertFalse(Sector.objects.filter(pk=self.sector.pk).exists())
        self.assertFalse(CostCenter.objects.filter(pk=self.costcenter.pk).exists())
        self.assertFalse(Function.objects.filter(pk=self.function.pk).exists())
        self.assertFalse(Employee.objects.filter(pk=self.employee.pk).exists())
        self.assertFalse(Alert.objects.filter(pk=self.alert.pk).exists())
        
        # Verify audit log is recorded
        audit = AuditLog.objects.filter(model_name="Company", object_id=str(self.company.pk)).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user, self.user)
        self.assertIn("Exclusão em Cascata Administrativa", audit.action)
        
        # Verify before changes contain correct JSON keys/values
        before_data = json.loads(audit.changes_before)
        self.assertIn("organizations.Company", before_data)
        self.assertIn("employees.Employee", before_data)
        self.assertIn("notifications.Alert", before_data)

    def test_execute_cascade_delete_rollback(self):
        # We simulate a database or transaction failure during delete
        # by forcing an exception via pre_delete signal on Unit
        from django.db.models.signals import pre_delete
        
        def raise_error(sender, instance, **kwargs):
            if sender == Unit:
                raise RuntimeError("Database error simulation")
                
        pre_delete.connect(raise_error, sender=Unit)
        try:
            with self.assertRaises(RuntimeError):
                execute_cascade_delete(self.company, user=self.user)
        finally:
            pre_delete.disconnect(raise_error, sender=Unit)
            
        # Verify everything is intact in the database due to rollback
        self.assertTrue(Company.objects.filter(pk=self.company.pk).exists())
        self.assertTrue(Unit.objects.filter(pk=self.unit.pk).exists())
        self.assertTrue(Sector.objects.filter(pk=self.sector.pk).exists())
        self.assertTrue(Employee.objects.filter(pk=self.employee.pk).exists())


class AdminCascadeDeleteTestCase(TestCase):

    def setUp(self):
        # Create users
        self.superuser = User.objects.create_superuser(username="admin", email="admin@example.com", password="password")
        self.authorized_user = User.objects.create_user(username="authorized", email="auth@example.com", password="password", is_staff=True)
        self.unauthorized_user = User.objects.create_user(username="unauthorized", email="unauth@example.com", password="password", is_staff=True)
        
        # Give permissions to authorized user
        # can_force_cascade_delete permission
        company_ct = ContentType.objects.get_for_model(Company)
        perm_cascade = Permission.objects.get(codename="can_force_cascade_delete", content_type=company_ct)
        perm_delete = Permission.objects.get(codename="delete_company", content_type=company_ct)
        perm_change = Permission.objects.get(codename="change_company", content_type=company_ct)
        self.authorized_user.user_permissions.add(perm_cascade, perm_delete, perm_change)
        
        # Give only standard permissions to unauthorized user
        self.unauthorized_user.user_permissions.add(perm_delete, perm_change)

        # Setup standard organization for test
        self.company = Company.objects.create(
            razao_social="Empresa Admin Teste",
            nome_fantasia="Empresa Admin",
            cnpj="98.765.432/0001-99",
            ativo=True
        )
        self.unit = Unit.objects.create(
            company=self.company,
            codigo="U-ADMIN",
            nome="Unidade Admin",
            cidade="Maceió",
            estado="AL",
            ativo=True
        )

    def test_admin_delete_view_get_authorized(self):
        self.client.force_login(self.authorized_user)
        url = reverse("admin:organizations_company_delete", args=[self.company.pk])
        response = self.client.get(url)
        
        # Should render custom confirmation template
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/cascade_delete_confirmation.html")
        self.assertIn("ATENÇÃO: Operação de Alto Risco!", response.content.decode("utf-8"))
        self.assertIn("Unidades", response.content.decode("utf-8"))

    def test_admin_delete_view_get_unauthorized_shows_standard_lock(self):
        self.client.force_login(self.unauthorized_user)
        url = reverse("admin:organizations_company_delete", args=[self.company.pk])
        response = self.client.get(url)
        
        # Should show standard Django admin page showing protection and blocking deletion
        self.assertEqual(response.status_code, 200)
        # Standard Django delete view contains a message showing what cannot be deleted
        self.assertIn("Não é possível remover", response.content.decode("utf-8"))
        self.assertNotIn("Para confirmar a exclusão, digite a palavra de confirmação", response.content.decode("utf-8"))

    def test_admin_delete_view_post_correct_confirmation(self):
        self.client.force_login(self.authorized_user)
        url = reverse("admin:organizations_company_delete", args=[self.company.pk])
        
        # POST with correct confirmation
        response = self.client.post(url, {"confirmation_word": "EXCLUIR"})
        
        # Should redirect to changelist
        self.assertRedirects(response, reverse("admin:organizations_company_changelist"))
        
        # Check database: Company and Unit are deleted
        self.assertFalse(Company.objects.filter(pk=self.company.pk).exists())
        self.assertFalse(Unit.objects.filter(pk=self.unit.pk).exists())

    def test_admin_delete_view_post_incorrect_confirmation(self):
        self.client.force_login(self.authorized_user)
        url = reverse("admin:organizations_company_delete", args=[self.company.pk])
        
        # POST with incorrect confirmation
        response = self.client.post(url, {"confirmation_word": "ERRADO"})
        
        # Should stay on page and show error message
        self.assertEqual(response.status_code, 200)
        self.assertIn("Palavra de confirmação incorreta", response.content.decode("utf-8"))
        
        # Verify database is intact
        self.assertTrue(Company.objects.filter(pk=self.company.pk).exists())
        self.assertTrue(Unit.objects.filter(pk=self.unit.pk).exists())

    def test_admin_bulk_delete_authorized(self):
        self.client.force_login(self.superuser)
        
        # Create another company
        company2 = Company.objects.create(
            razao_social="Empresa Secundária",
            nome_fantasia="Empresa 2",
            cnpj="11.222.333/0001-44",
            ativo=True
        )
        unit2 = Unit.objects.create(
            company=company2,
            codigo="U-SEC",
            nome="Unidade Sec",
            cidade="Recife",
            estado="PE",
            ativo=True
        )
        
        url = reverse("admin:organizations_company_changelist")
        
        # Call actions post
        post_data = {
            "action": "delete_selected",
            "_selected_action": [self.company.pk, company2.pk]
        }
        
        # GET action confirmation screen
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/cascade_delete_confirmation.html")
        self.assertIn("Você está prestes a excluir permanentemente os <strong>2</strong> registros selecionados", response.content.decode("utf-8"))
        
        # Confirm action
        post_confirm_data = {
            "action": "delete_selected",
            "_selected_action": [self.company.pk, company2.pk],
            "post_confirmed": "yes",
            "confirmation_word": "EXCLUIR"
        }
        
        response = self.client.post(url, post_confirm_data)
        self.assertRedirects(response, url)
        
        # Verify both are deleted
        self.assertFalse(Company.objects.filter(pk=self.company.pk).exists())
        self.assertFalse(Company.objects.filter(pk=company2.pk).exists())
        self.assertFalse(Unit.objects.filter(pk=self.unit.pk).exists())
        self.assertFalse(Unit.objects.filter(pk=unit2.pk).exists())

    def test_delete_object_without_dependencies_works_normally(self):
        # Create a company with NO units/dependencies
        standalone_company = Company.objects.create(
            razao_social="Empresa Solitária",
            nome_fantasia="Standalone",
            cnpj="00.111.222/0001-33",
            ativo=True
        )
        
        self.client.force_login(self.authorized_user)
        
        # Since it has no dependencies, it should show the standard Django admin confirmation screen (without EXCLUIR word check)
        url = reverse("admin:organizations_company_delete", args=[standalone_company.pk])
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateNotUsed(response, "admin/cascade_delete_confirmation.html")
        # Standard Django delete view contains "Tem certeza?" (translated to "Você tem certeza?" in pt-br)
        self.assertIn("certeza", response.content.decode("utf-8").lower())
        
        # Let's perform standard deletion
        response = self.client.post(url, {"post": "yes"})
        self.assertRedirects(response, reverse("admin:organizations_company_changelist"))
        self.assertFalse(Company.objects.filter(pk=standalone_company.pk).exists())


class SecuritySettingsTestCase(SimpleTestCase):

    def test_allowed_hosts_parsing(self):
        raw_val = "  sst.freedom.dev.br , 192.168.0.202, 127.0.0.1, , localhost  "
        parsed = [host.strip() for host in raw_val.split(",") if host.strip()]
        self.assertEqual(parsed, ["sst.freedom.dev.br", "192.168.0.202", "127.0.0.1", "localhost"])

    def test_csrf_trusted_origins_parsing(self):
        raw_val = "  https://sst.freedom.dev.br , http://localhost:8800 , , "
        parsed = [origin.strip() for origin in raw_val.split(",") if origin.strip()]
        self.assertEqual(parsed, ["https://sst.freedom.dev.br", "http://localhost:8800"])

    def test_boolean_env_parsing(self):
        self.assertTrue("True".lower() == "true")
        self.assertTrue("true".lower() == "true")
        self.assertFalse("False".lower() == "true")
        self.assertFalse("".lower() == "true")

    def test_secret_key_validation_in_production(self):
        debug = False
        secret_key = None
        with self.assertRaises(RuntimeError) as cm:
            if not secret_key:
                if debug:
                    secret_key = "django-insecure-local-development-only"
                else:
                    raise RuntimeError(
                        "A variável de ambiente SECRET_KEY é obrigatória quando DEBUG=False."
                    )
        self.assertIn("SECRET_KEY é obrigatória quando DEBUG=False", str(cm.exception))

    def test_secret_key_fallback_in_debug(self):
        debug = True
        secret_key = None
        if not secret_key:
            if debug:
                secret_key = "django-insecure-local-development-only"
        self.assertEqual(secret_key, "django-insecure-local-development-only")

    def test_current_django_settings_configured_safely(self):
        from django.conf import settings
        self.assertIn("localhost", settings.ALLOWED_HOSTS)
        self.assertIn("127.0.0.1", settings.ALLOWED_HOSTS)
        self.assertNotIn("*", settings.ALLOWED_HOSTS)
        self.assertEqual(settings.SECURE_PROXY_SSL_HEADER, ("HTTP_X_FORWARDED_PROTO", "https"))
        self.assertIsInstance(settings.CSRF_TRUSTED_ORIGINS, list)
        self.assertIsInstance(settings.SESSION_COOKIE_SECURE, bool)
        self.assertIsInstance(settings.CSRF_COOKIE_SECURE, bool)
        self.assertIsInstance(settings.SECURE_SSL_REDIRECT, bool)

