from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.utils import timezone
from organizations.models import Unit, InventoryLocation
from inventory.models import Lot, StockMovement
from inventory.services import get_stock_balance
from .models import Product, ProductVariant, CertificadoAprovacao, PPEMatrix, PPEDelivery, ExtraordinaryPPE
from .services import deliver_ppe, confirm_delivery_signature, return_ppe, write_off_ppe

class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "ppe/product_list.html"
    context_object_name = "products"


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    fields = ['nome', 'categoria', 'descricao', 'unidade_medida', 'fabricante', 'exige_ca', 'controlado_individualmente', 'ativo']
    template_name = "organizations/form.html"
    success_url = "/ppe/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Novo Produto / EPI"
        return context


class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = "ppe/product_detail.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['variants'] = self.object.variants.all()
        
        # Calcula saldos por local para cada variante
        user_units = self.request.user.units.all()
        if self.request.user.is_superuser and not user_units.exists():
            user_units = Unit.objects.all()
            
        locations = InventoryLocation.objects.filter(unit__in=user_units, ativo=True)
        
        variant_balances = []
        for variant in context['variants']:
            loc_bals = []
            for loc in locations:
                bal = get_stock_balance(loc, variant)
                if bal > 0:
                    loc_bals.append({
                        'location': loc.nome,
                        'unit': loc.unit.codigo,
                        'balance': bal
                    })
            variant_balances.append({
                'variant': variant,
                'balances': loc_bals
            })
            
        context['variant_balances'] = variant_balances
        return context


class ProductVariantCreateView(LoginRequiredMixin, CreateView):
    model = ProductVariant
    fields = ['tamanho', 'sku', 'codigo_barras', 'estoque_minimo', 'estoque_maximo', 'ativo']

    def post(self, request, *args, **kwargs):
        product_id = self.kwargs.get('product_pk')
        product = get_object_or_404(Product, pk=product_id)
        form = self.get_form()
        if form.is_valid():
            variant = form.save(commit=False)
            variant.product = product
            variant.save()
            messages.success(request, f"Tamanho {variant.tamanho} adicionado com sucesso.")
        else:
            messages.error(request, f"Erro ao adicionar variante: {form.errors.as_text()}")
        return redirect('product_detail', pk=product_id)


class CertificadoAprovacaoListView(LoginRequiredMixin, ListView):
    model = CertificadoAprovacao
    template_name = "ppe/ca_list.html"
    context_object_name = "cas"


class CertificadoAprovacaoCreateView(LoginRequiredMixin, CreateView):
    model = CertificadoAprovacao
    fields = ['numero_exibicao', 'fabricante', 'natureza_protecao', 'data_validade', 'justificativa_manual']
    template_name = "organizations/form.html"
    success_url = "/ppe/ca/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Novo C.A. Manual"
        return context

    def form_valid(self, form):
        # normaliza o número do C.A. (apenas dígitos)
        num_exib = form.cleaned_data.get('numero_exibicao', '')
        num_norm = "".join([c for c in num_exib if c.isdigit()])
        
        if not num_norm:
            form.add_error('numero_exibicao', "Número do C.A. deve conter dígitos numéricos.")
            return self.form_invalid(form)

        form.instance.numero = num_norm
        form.instance.status_verificacao = 'INFORMADO_MANUALMENTE'
        form.instance.situacao = 'VÁLIDO' if form.cleaned_data.get('data_validade') >= timezone.now().date() else 'VENCIDO'
        
        response = super().form_valid(form)
        messages.success(self.request, f"Certificado {num_exib} cadastrado manualmente.")
        return response


class PPEDeliveryListView(LoginRequiredMixin, ListView):
    model = PPEDelivery
    template_name = "ppe/delivery_list.html"
    context_object_name = "deliveries"

    def get_queryset(self):
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            user_units = Unit.objects.all()
        return PPEDelivery.objects.filter(unit__in=user_units).select_related('employee', 'product_variant__product', 'ca_entregue', 'lot')


class PPEDeliveryCreateView(LoginRequiredMixin, CreateView):
    model = PPEDelivery
    fields = ['employee', 'product_variant', 'lot', 'quantidade', 'data_entrega', 'natureza_entrega', 'motivo_substituicao']
    template_name = "ppe/delivery_form.html"

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            user_units = Unit.objects.all()
            
        # Filtra colaboradores da unidade permitida
        form.fields['employee'].queryset = Employee.objects.filter(unit__in=user_units, situacao='ATIVO')
        # Filtra variantes de EPI ativas
        form.fields['product_variant'].queryset = ProductVariant.objects.filter(ativo=True).select_related('product')
        
        # Filtra lotes disponíveis no estoque SST das unidades permitidas
        sst_locations = InventoryLocation.objects.filter(unit__in=user_units, tipo='SST', ativo=True)
        available_lots = []
        lots = Lot.objects.all().select_related('product_variant__product')
        for lot in lots:
            # Check balance in any SST location
            for loc in sst_locations:
                bal = get_stock_balance(loc, lot.product_variant, lot)
                if bal > 0:
                    available_lots.append(lot.id)
                    break
        form.fields['lot'].queryset = Lot.objects.filter(id__in=available_lots).select_related('product_variant__product')
        return form

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            employee = form.cleaned_data['employee']
            product_variant = form.cleaned_data['product_variant']
            lot = form.cleaned_data['lot']
            quantidade = form.cleaned_data['quantidade']
            data_entrega = form.cleaned_data['data_entrega']
            natureza_entrega = form.cleaned_data['natureza_entrega']
            motivo_substituicao = form.cleaned_data['motivo_substituicao']

            try:
                delivery = deliver_ppe(
                    employee=employee,
                    product_variant=product_variant,
                    lot=lot,
                    quantity=quantidade,
                    user=request.user,
                    data_entrega=data_entrega,
                    natureza_entrega=natureza_entrega,
                    motivo_substituicao=motivo_substituicao
                )
                messages.success(request, f"EPI {product_variant.product.nome} entregue com sucesso! Coleta de ciência pendente.")
                return redirect('delivery_sign', pk=delivery.id)
            except Exception as e:
                messages.error(request, f"Erro ao realizar entrega: {str(e)}")
        else:
            messages.error(request, f"Erro no formulário: {form.errors.as_text()}")
        return render(request, self.template_name, {'form': form})


def delivery_sign_view(request, pk):
    delivery = get_object_or_404(PPEDelivery, pk=pk)
    if request.method == 'POST':
        nome_confirmacao = request.POST.get('nome_confirmacao')
        if not nome_confirmacao:
            messages.error(request, "O nome do trabalhador é obrigatório para confirmar a assinatura.")
            return render(request, "ppe/delivery_sign.html", {'delivery': delivery})
            
        try:
            confirm_delivery_signature(delivery, nome_confirmacao)
            messages.success(request, "Ciência do trabalhador registrada e recibo assinado eletronicamente!")
            return redirect('employee_detail', pk=delivery.employee.id)
        except Exception as e:
            messages.error(request, f"Erro ao assinar: {str(e)}")
            
    return render(request, "ppe/delivery_sign.html", {'delivery': delivery})
