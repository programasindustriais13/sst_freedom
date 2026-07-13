from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, TemplateView, DetailView
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied
from .models import Company, Unit, Sector, CostCenter, Function, InventoryLocation

class OrganizationDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "organizations/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            user_units = Unit.objects.all()

        context.update({
            'companies': Company.objects.all(),
            'units': Unit.objects.filter(id__in=user_units),
            'sectors': Sector.objects.filter(unit__in=user_units),
            'cost_centers': CostCenter.objects.all(),
            'functions': Function.objects.all(),
            'locations': InventoryLocation.objects.filter(unit__in=user_units),
        })
        return context


class CompanyCreateView(LoginRequiredMixin, CreateView):
    model = Company
    fields = ['razao_social', 'nome_fantasia', 'cnpj', 'ativo']
    template_name = "organizations/form.html"
    success_url = reverse_lazy('organization_dashboard')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied("Apenas administradores podem cadastrar empresas.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Nova Empresa"
        return context


class UnitCreateView(LoginRequiredMixin, CreateView):
    model = Unit
    fields = ['company', 'codigo', 'nome', 'cidade', 'estado', 'ativo']
    template_name = "organizations/form.html"
    success_url = reverse_lazy('organization_dashboard')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied("Apenas administradores podem cadastrar unidades.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Nova Unidade"
        return context


class SectorCreateView(LoginRequiredMixin, CreateView):
    model = Sector
    fields = ['unit', 'nome', 'codigo', 'ativo']
    template_name = "organizations/form.html"
    success_url = reverse_lazy('organization_dashboard')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filtra unidades permitidas
        user = self.request.user
        if not user.is_superuser or user.units.exists():
            form.fields['unit'].queryset = user.units.all()
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Novo Setor"
        return context


class CostCenterCreateView(LoginRequiredMixin, CreateView):
    model = CostCenter
    fields = ['company', 'codigo', 'nome', 'ativo']
    template_name = "organizations/form.html"
    success_url = reverse_lazy('organization_dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Novo Centro de Custo"
        return context


class FunctionCreateView(LoginRequiredMixin, CreateView):
    model = Function
    fields = ['company', 'nome', 'descricao', 'ativo']
    template_name = "organizations/form.html"
    success_url = reverse_lazy('organization_dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Nova Função/Cargo"
        return context


class InventoryLocationCreateView(LoginRequiredMixin, CreateView):
    model = InventoryLocation
    fields = ['unit', 'codigo', 'nome', 'tipo', 'ativo']
    template_name = "organizations/form.html"
    success_url = reverse_lazy('organization_dashboard')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        if not user.is_superuser or user.units.exists():
            form.fields['unit'].queryset = user.units.all()
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Novo Local de Estoque"
        return context


class FunctionDetailView(LoginRequiredMixin, DetailView):
    model = Function
    template_name = "organizations/function_detail.html"
    context_object_name = "function"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from ppe.models import PPEMatrix
        context['matrix_entries'] = PPEMatrix.objects.filter(funcao=self.object).select_related('product', 'variant').order_by('product__nome')
        return context

