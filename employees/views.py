from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib import messages
from django.db.models import Q
from organizations.models import Unit, Sector, CostCenter, Function
from .models import Employee, EmployeeHistory

class EmployeeListView(LoginRequiredMixin, ListView):
    model = Employee
    template_name = "employees/list.html"
    context_object_name = "employees"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            user_units = Unit.objects.all()

        queryset = Employee.objects.filter(unit__in=user_units)
        
        # Filtros de busca
        q_search = self.request.GET.get('search')
        if q_search:
            # Remove pontos/traço do CPF se digitados na busca para facilitar a comparação normalizada
            search_clean = q_search.replace('.', '').replace('-', '')
            queryset = queryset.filter(
                Q(nome_completo__icontains=q_search) |
                Q(matricula__icontains=q_search) |
                Q(cpf__icontains=search_clean) |
                Q(telefone__icontains=q_search)
            )

        # Filtro por unidade
        q_unit = self.request.GET.get('unit')
        if q_unit:
            queryset = queryset.filter(unit_id=q_unit)

        # Filtro por situação
        q_situacao = self.request.GET.get('situacao')
        if q_situacao:
            queryset = queryset.filter(situacao=q_situacao)

        return queryset.select_related('unit', 'funcao', 'setor').order_name() if hasattr(queryset, 'order_name') else queryset.select_related('unit', 'funcao', 'setor').order_by('nome_completo')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            user_units = Unit.objects.all()
            
        context['units'] = user_units
        context['search_val'] = self.request.GET.get('search', '')
        context['unit_val'] = self.request.GET.get('unit', '')
        context['situacao_val'] = self.request.GET.get('situacao', '')
        return context


class EmployeeCreateView(LoginRequiredMixin, CreateView):
    model = Employee
    fields = [
        'company', 'unit', 'matricula', 'nome_completo', 'cpf',
        'funcao', 'setor', 'centro_custo', 'turno', 'data_admissao',
        'situacao', 'telefone', 'email', 'tamanho_camisa', 'tamanho_calca',
        'num_calcado', 'tamanho_luva', 'modelo_farda', 'observacoes'
    ]
    template_name = "employees/form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        if not user.is_superuser or user.units.exists():
            form.fields['unit'].queryset = user.units.all()
        return form

    def form_valid(self, form):
        form.instance.criado_por = self.request.user
        response = super().form_valid(form)
        
        # Cria histórico inicial
        EmployeeHistory.objects.create(
            employee=self.object,
            funcao=self.object.funcao,
            setor=self.object.setor,
            unit=self.object.unit,
            centro_custo=self.object.centro_custo,
            alterado_por=self.request.user,
            observacao="Histórico funcional inicial criado no cadastro do colaborador."
        )
        
        # Grava auditoria
        from audit.models import log_audit
        log_audit(
            request=self.request,
            action=f"Criação de colaborador: {self.object.nome_completo} (Matrícula: {self.object.matricula})",
            model_name="Employee",
            object_id=self.object.id,
            before=None,
            after={'nome': self.object.nome_completo, 'matricula': self.object.matricula, 'cpf': self.object.cpf}
        )
        
        messages.success(self.request, "Colaborador cadastrado com sucesso!")
        return response

    def get_success_url(self):
        return reverse_lazy('employee_detail', kwargs={'pk': self.object.pk})


class EmployeeUpdateView(LoginRequiredMixin, UpdateView):
    model = Employee
    fields = [
        'company', 'unit', 'matricula', 'nome_completo', 'cpf',
        'funcao', 'setor', 'centro_custo', 'turno', 'data_admissao',
        'situacao', 'data_desligamento', 'telefone', 'email', 'tamanho_camisa',
        'tamanho_calca', 'num_calcado', 'tamanho_luva', 'modelo_farda', 'observacoes'
    ]
    template_name = "employees/form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        if not user.is_superuser or user.units.exists():
            form.fields['unit'].queryset = user.units.all()
        return form

    def form_valid(self, form):
        # Captura valores originais antes de salvar
        old_instance = Employee.objects.get(pk=self.object.pk)
        response = super().form_valid(form)
        
        # Verifica se houve alteração de campos críticos funcionais
        has_changed = (
            old_instance.funcao != self.object.funcao or
            old_instance.setor != self.object.setor or
            old_instance.unit != self.object.unit or
            old_instance.centro_custo != self.object.centro_custo
        )

        if has_changed:
            # Encerra o histórico ativo
            active_hist = EmployeeHistory.objects.filter(employee=self.object, data_fim__isnull=True).first()
            if active_hist:
                active_hist.data_fim = timezone.now()
                active_hist.save()

            # Cria novo histórico
            EmployeeHistory.objects.create(
                employee=self.object,
                funcao=self.object.funcao,
                setor=self.object.setor,
                unit=self.object.unit,
                centro_custo=self.object.centro_custo,
                alterado_por=self.request.user,
                observacao=f"Mudança de cargo/setor. Anterior: {old_instance.funcao.nome} ({old_instance.setor.nome}). Novo: {self.object.funcao.nome} ({self.object.setor.nome})."
            )
            messages.info(self.request, "Cadastro e histórico funcional do colaborador atualizados.")
        else:
            messages.success(self.request, "Cadastro do colaborador atualizado com sucesso.")
            
        # Grava auditoria
        from audit.models import log_audit
        log_audit(
            request=self.request,
            action=f"Alteração de colaborador: {self.object.nome_completo} (Matrícula: {self.object.matricula})",
            model_name="Employee",
            object_id=self.object.id,
            before={'funcao': old_instance.funcao.nome, 'setor': old_instance.setor.nome, 'unit': old_instance.unit.codigo, 'centro_custo': old_instance.centro_custo.codigo, 'situacao': old_instance.situacao},
            after={'funcao': self.object.funcao.nome, 'setor': self.object.setor.nome, 'unit': self.object.unit.codigo, 'centro_custo': self.object.centro_custo.codigo, 'situacao': self.object.situacao}
        )

        return response

    def get_success_url(self):
        return reverse_lazy('employee_detail', kwargs={'pk': self.object.pk})


class EmployeeDetailView(LoginRequiredMixin, DetailView):
    model = Employee
    template_name = "employees/detail.html"
    context_object_name = "employee"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee = self.object
        
        # Carrega ficha de EPI (entregas)
        deliveries = employee.ppe_deliveries.all().select_related('product_variant__product', 'ca_entregue', 'lot')
        
        # Carrega histórico funcional
        history = employee.history.all().select_related('funcao', 'setor', 'unit', 'centro_custo')

        # Busca matriz de EPI recomendada para a função do colaborador
        from ppe.models import PPEMatrix, ExtraordinaryPPE
        matrix = PPEMatrix.objects.filter(funcao=employee.funcao, ativo=True).select_related('product')
        
        # Busca EPIs extraordinários ativos
        extraordinary = ExtraordinaryPPE.objects.filter(employee=employee, ativo=True).select_related('product')

        context.update({
            'deliveries': deliveries,
            'history': history,
            'matrix': matrix,
            'extraordinary': extraordinary,
        })
        return context
