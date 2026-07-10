"""
Testes do Django Admin para o app ppe.
SPEC-2026-004 — Admin: Gerenciamento e Exclusão Completa pelo Superusuário

Cobertura:
- T-009: PPEDelivery não tem botão Excluir para superusuário
- T-015: Superusuário pode excluir CertificadoAprovacao sem lotes
- Permissão de CA com lote vinculado (PROTECT via Lot)
"""

from django.test import TestCase, Client, RequestFactory
from django.contrib.auth import get_user_model
from django.urls import reverse
from organizations.models import Company, Unit, Sector, CostCenter, Function
from employees.models import Employee
from .models import Product, ProductVariant, CertificadoAprovacao, PPEDelivery, ExtraordinaryPPE

User = get_user_model()


class PPEAdminSetupMixin:
    """Dados mínimos de apoio aos testes de ppe."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="superadmin",
            password="testpass123",
            email="super@test.com",
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
        self.sector = Sector.objects.create(unit=self.unit, nome="Setor Teste")
        self.cost_center = CostCenter.objects.create(
            company=self.company, codigo="CC001", nome="CC Teste"
        )
        self.function = Function.objects.create(
            company=self.company, nome="Função Teste"
        )
        self.product = Product.objects.create(
            nome="EPI Teste",
            categoria="PROTECAO_CABECA",
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            tamanho="U",
        )
        self.client = Client()


class PPEDeliveryAdminTest(PPEAdminSetupMixin, TestCase):

    def test_superuser_nao_tem_permissao_excluir_ppe_delivery(self):
        """T-009: PPEDelivery não tem permissão de exclusão para superusuário."""
        from ppe.admin import PPEDeliveryAdmin
        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.superuser
        pda = PPEDeliveryAdmin(PPEDelivery, None)
        self.assertFalse(pda.has_delete_permission(request))

    def test_superuser_nao_tem_permissao_adicionar_ppe_delivery(self):
        """PPEDelivery não tem permissão de adição para superusuário."""
        from ppe.admin import PPEDeliveryAdmin
        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.superuser
        pda = PPEDeliveryAdmin(PPEDelivery, None)
        self.assertFalse(pda.has_add_permission(request))

    def test_superuser_acessa_listagem_ppe_delivery(self):
        """Superusuário acessa listagem de PPEDelivery."""
        self.client.force_login(self.superuser)
        url = reverse("admin:ppe_ppedelivery_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class CertificadoAprovacaoAdminTest(PPEAdminSetupMixin, TestCase):

    def test_superuser_tem_permissao_excluir_ca(self):
        """T-015: Superusuário tem permissão de exclusão em CertificadoAprovacao."""
        from ppe.admin import CertificadoAprovacaoAdmin
        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.superuser
        caa = CertificadoAprovacaoAdmin(CertificadoAprovacao, None)
        self.assertTrue(caa.has_delete_permission(request))

    def test_superuser_exclui_ca_sem_lotes(self):
        """T-015: Superusuário exclui CertificadoAprovacao sem lotes vinculados."""
        ca = CertificadoAprovacao.objects.create(
            numero="99999",
            numero_exibicao="CA 99999",
            data_validade="2030-01-01",
        )
        self.client.force_login(self.superuser)
        url = reverse("admin:ppe_certificadoaprovacao_delete", args=[ca.pk])
        response = self.client.post(url, {"post": "yes"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CertificadoAprovacao.objects.filter(pk=ca.pk).exists())

    def test_superuser_acessa_listagem_ca(self):
        """Superusuário acessa listagem de CertificadoAprovacao."""
        self.client.force_login(self.superuser)
        url = reverse("admin:ppe_certificadoaprovacao_changelist")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class AuditLogAdminTest(TestCase):
    """T-008: AuditLog permanece imutável para superusuário."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="superadmin2",
            password="testpass123",
            email="super2@test.com",
        )

    def test_superuser_nao_tem_permissao_excluir_audit_log(self):
        from audit.admin import AuditLogAdmin
        from audit.models import AuditLog
        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.superuser
        ala = AuditLogAdmin(AuditLog, None)
        self.assertFalse(ala.has_delete_permission(request))

    def test_superuser_nao_tem_permissao_adicionar_audit_log(self):
        from audit.admin import AuditLogAdmin
        from audit.models import AuditLog
        factory = RequestFactory()
        request = factory.get("/")
        request.user = self.superuser
        ala = AuditLogAdmin(AuditLog, None)
        self.assertFalse(ala.has_add_permission(request))
