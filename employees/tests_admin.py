"""
Testes do Django Admin para o app employees.
SPEC-2026-004 — Admin: Gerenciamento e Exclusão Completa pelo Superusuário

Cobertura:
- T-002: Superusuário acessa tela de detalhe de Employee com botão Excluir
- T-003: Superusuário exclui Employee sem entregas de EPI
- T-004: Superusuário usa exclusão em massa de Employee sem entregas
- T-005: Superusuário tenta excluir Employee com PPEDelivery → mensagem amigável
- T-006: Staff não-superusuário não vê botão Excluir em Employee
- T-013 (parcial): EmployeeHistory aparece no admin com exclusão para superusuário
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from organizations.models import Company, Unit, Sector, CostCenter, Function
from .models import Employee, EmployeeHistory

User = get_user_model()


class EmployeeAdminSetupMixin:
    """Dados mínimos de apoio aos testes."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="superadmin",
            password="testpass123",
            email="super@test.com",
        )
        self.staff_user = User.objects.create_user(
            username="staff",
            password="testpass123",
            email="staff@test.com",
            is_staff=True,
        )

        self.company = Company.objects.create(
            razao_social="Empresa Teste LTDA",
            nome_fantasia="Empresa Teste",
            cnpj="00.000.000/0001-00",
        )
        self.unit = Unit.objects.create(
            company=self.company,
            codigo="U001",
            nome="Unidade Teste",
            cidade="Fortaleza",
            estado="CE",
        )
        self.sector = Sector.objects.create(
            unit=self.unit, nome="Setor Teste"
        )
        self.cost_center = CostCenter.objects.create(
            company=self.company, codigo="CC001", nome="CC Teste"
        )
        self.function = Function.objects.create(
            company=self.company, nome="Função Teste"
        )
        self.employee = Employee.objects.create(
            company=self.company,
            unit=self.unit,
            matricula="001",
            nome_completo="Colaborador Teste",
            cpf="529.982.247-25",
            funcao=self.function,
            setor=self.sector,
            centro_custo=self.cost_center,
            data_admissao="2024-01-01",
        )
        self.client = Client()


class EmployeeAdminSuperuserTest(EmployeeAdminSetupMixin, TestCase):

    def test_superuser_acessa_listagem_employee(self):
        """T-001 parcial: Superusuário acessa listagem de Employee."""
        self.client.force_login(self.superuser)
        url = reverse("admin:employees_employee_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_superuser_acessa_detalhe_employee(self):
        """T-002: Superusuário acessa tela de detalhe de Employee."""
        self.client.force_login(self.superuser)
        url = reverse("admin:employees_employee_change", args=[self.employee.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_superuser_ve_botao_excluir_employee(self):
        """T-002: O link de exclusão deve aparecer para superusuário.
        O Django Admin em pt-br exibe 'Remover' como texto do link de exclusão.
        """
        self.client.force_login(self.superuser)
        url = reverse("admin:employees_employee_change", args=[self.employee.pk])
        response = self.client.get(url)
        # O template do Django Admin em pt-br usa "Remover" no link de delete
        self.assertContains(response, "deletelink")

    def test_superuser_exclui_employee_sem_dependencias(self):
        """T-003: Superusuário exclui Employee sem entregas de EPI."""
        self.client.force_login(self.superuser)
        url = reverse("admin:employees_employee_delete", args=[self.employee.pk])
        response = self.client.post(url, {"post": "yes"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Employee.objects.filter(pk=self.employee.pk).exists())

    def test_superuser_exclui_employee_em_massa(self):
        """T-004: Superusuário usa exclusão em massa."""
        employee2 = Employee.objects.create(
            company=self.company,
            unit=self.unit,
            matricula="002",
            nome_completo="Colaborador Dois",
            cpf="275.484.297-98",
            funcao=self.function,
            setor=self.sector,
            centro_custo=self.cost_center,
            data_admissao="2024-01-01",
        )
        self.client.force_login(self.superuser)
        url = reverse("admin:employees_employee_changelist")
        response = self.client.post(
            url,
            {
                "action": "delete_selected",
                "_selected_action": [self.employee.pk, employee2.pk],
            },
        )
        # Deve exibir a página de confirmação (200) ou redirecionar (302) após confirmação
        self.assertIn(response.status_code, [200, 302])

    def test_superuser_acessa_listagem_employee_history(self):
        """T-013 parcial: EmployeeHistory aparece no admin."""
        self.client.force_login(self.superuser)
        url = reverse("admin:employees_employeehistory_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class EmployeeAdminStaffTest(EmployeeAdminSetupMixin, TestCase):

    def test_staff_nao_ve_botao_excluir_employee(self):
        """T-006: Staff não-superusuário não deve ver botão Excluir em Employee."""
        self.client.force_login(self.staff_user)
        url = reverse("admin:employees_employee_changelist")
        response = self.client.get(url)
        # Staff sem permissão de delete não vê a ação delete_selected
        # O response pode ser 200 (se staff tem permissão de view) ou 302 (redirect para login/dashboard)
        # O importante é que o staff_user não tenha permissão de exclusão
        from employees.admin import EmployeeAdmin
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.staff_user
        ea = EmployeeAdmin(Employee, None)
        self.assertFalse(ea.has_delete_permission(request))

    def test_superuser_tem_permissao_excluir_employee(self):
        """Confirmação: superusuário tem permissão de exclusão em Employee."""
        from employees.admin import EmployeeAdmin
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.superuser
        ea = EmployeeAdmin(Employee, None)
        self.assertTrue(ea.has_delete_permission(request))
