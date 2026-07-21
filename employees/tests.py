from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from organizations.models import Company, Unit, Sector, CostCenter, Function
from employees.models import Employee, validate_cpf
from employees.forms import EmployeeForm

User = get_user_model()

class CPFValidationTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(razao_social="Empresa Teste", cnpj="12345678000195")
        self.unit = Unit.objects.create(company=self.company, codigo="U1", nome="Unidade 1")
        self.sector = Sector.objects.create(unit=self.unit, nome="Manutenção")
        self.cost_center = CostCenter.objects.create(company=self.company, codigo="CC1", nome="Centro 1")
        self.function = Function.objects.create(company=self.company, nome="Eletricista")
        
        self.user = User.objects.create_superuser(username="admin", password="password123")
        self.user.units.add(self.unit)

    def test_validate_cpf_valid(self):
        # Valid test CPFs
        valid_cpfs = ["52998224725", "11144477735", "529.982.247-25"]
        for cpf in valid_cpfs:
            try:
                validate_cpf(cpf)
            except ValidationError:
                self.fail(f"validate_cpf falhou para o CPF válido {cpf}")

    def test_validate_cpf_invalid_repeated(self):
        invalid_cpfs = ["000.000.000-00", "111.111.111-11", "99999999999"]
        for cpf in invalid_cpfs:
            with self.assertRaises(ValidationError) as cm:
                validate_cpf(cpf)
            self.assertEqual(str(cm.exception.messages[0]), "CPF inválido. Sequência de dígitos repetidos não é permitida.")

    def test_validate_cpf_invalid_digits(self):
        # Invalid verifier digit (e.g. 123.123.123-55)
        with self.assertRaises(ValidationError) as cm:
            validate_cpf("12312312355")
        self.assertEqual(str(cm.exception.messages[0]), "CPF inválido. Os dígitos verificadores informados não conferem.")

    def test_validate_cpf_invalid_length(self):
        with self.assertRaises(ValidationError) as cm:
            validate_cpf("12345")
        self.assertEqual(str(cm.exception.messages[0]), "O CPF deve conter exatamente 11 dígitos.")

    def test_employee_form_valid_unformatted(self):
        form_data = {
            'company': self.company.id,
            'unit': self.unit.id,
            'matricula': 'MAT-001',
            'nome_completo': 'João da Silva',
            'cpf': '52998224725',
            'funcao': self.function.id,
            'setor': self.sector.id,
            'centro_custo': self.cost_center.id,
            'turno': 'ADM',
            'data_admissao': '2025-01-01',
            'situacao': 'ATIVO'
        }
        form = EmployeeForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['cpf'], '529.982.247-25')

    def test_employee_form_duplicate_prevented(self):
        Employee.objects.create(
            company=self.company,
            unit=self.unit,
            matricula='MAT-001',
            nome_completo='Existente',
            cpf='529.982.247-25',
            funcao=self.function,
            setor=self.sector,
            centro_custo=self.cost_center,
            data_admissao='2025-01-01'
        )

        # Try inserting unformatted version of the same CPF
        form_data = {
            'company': self.company.id,
            'unit': self.unit.id,
            'matricula': 'MAT-002',
            'nome_completo': 'Outro Silva',
            'cpf': '52998224725',
            'funcao': self.function.id,
            'setor': self.sector.id,
            'centro_custo': self.cost_center.id,
            'turno': 'ADM',
            'data_admissao': '2025-01-01',
            'situacao': 'ATIVO'
        }
        form = EmployeeForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('cpf', form.errors)
        self.assertEqual(form.errors['cpf'][0], 'Já existe um colaborador cadastrado com este CPF.')
