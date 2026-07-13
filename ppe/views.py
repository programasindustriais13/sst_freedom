from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView
from django.views import View
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import transaction, models
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from django.contrib import messages
from django.utils import timezone
from organizations.models import Unit, InventoryLocation, Function
from inventory.models import Lot, StockMovement
from inventory.services import get_stock_balance
from employees.models import Employee
from .models import Product, ProductVariant, CertificadoAprovacao, PPEMatrix, PPEDelivery, ExtraordinaryPPE
from .services import deliver_ppe, confirm_delivery_signature, return_ppe, write_off_ppe
from .forms import ProductForm, PPEMatrixForm, PPEMatrixBulkForm

class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "ppe/product_list.html"
    context_object_name = "products"


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "ppe/product_form.html"
    success_url = "/ppe/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Novo Produto / EPI"
        return context


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "ppe/product_form.html"
    success_url = "/ppe/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Editar Produto: {self.object.nome}"
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
        
        # Grava auditoria
        from audit.models import log_audit
        log_audit(
            request=self.request,
            action=f"Cadastro manual de C.A.: {self.object.numero_exibicao} (Fabricante: {self.object.fabricante})",
            model_name="CertificadoAprovacao",
            object_id=self.object.id,
            before=None,
            after={'numero_exibicao': self.object.numero_exibicao, 'justificativa': self.object.justificativa_manual}
        )
        
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
                
                # Grava auditoria
                from audit.models import log_audit
                log_audit(
                    request=request,
                    action=f"Entrega individual de EPI: {product_variant.product.nome} para {employee.nome_completo}",
                    model_name="PPEDelivery",
                    object_id=delivery.id,
                    before=None,
                    after={'colaborador': employee.nome_completo, 'matricula': employee.matricula, 'quantidade': quantidade, 'status_assinatura': 'PENDENTE'}
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
            
            # Grava auditoria
            from audit.models import log_audit
            log_audit(
                request=request,
                action=f"Confirmação de Ciência de Entrega: Colaborador {delivery.employee.nome_completo} assinou recibo",
                model_name="PPEDelivery",
                object_id=delivery.id,
                before={'status_assinatura': 'PENDENTE'},
                after={'status_assinatura': 'ASSINADO', 'confirmado_por': nome_confirmacao, 'hash': delivery.recibo_hash}
            )
            
            messages.success(request, "Ciência do trabalhador registrada e recibo assinado eletronicamente!")
            return redirect('employee_detail', pk=delivery.employee.id)
        except Exception as e:
            messages.error(request, f"Erro ao assinar: {str(e)}")
            
    return render(request, "ppe/delivery_sign.html", {'delivery': delivery})


@require_http_methods(["GET"])
def product_search_ajax(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'items': []})
    
    # Busca por nome (insensitivo) ou CA
    products = Product.objects.filter(ativo=True)
    products = products.filter(
        models.Q(nome__icontains=q) | 
        models.Q(ca_numero__icontains=q)
    )
    
    items = []
    for p in products[:10]:
        items.append({
            'id': p.id,
            'nome': p.nome,
            'tipo_produto': p.tipo_produto,
            'ca_numero': p.ca_numero or '',
            'unidade_medida': p.unidade_medida,
        })
    return JsonResponse({'items': items})


@require_http_methods(["POST"])
def product_add_ajax(request):
    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({'success': False, 'error': 'JSON inválido.'}, status=400)
    
    nome = data.get('nome', '').strip()
    tipo_produto = data.get('tipo_produto', 'EPI').strip()
    categoria = data.get('categoria', 'OUTRO').strip()
    ca_numero = data.get('ca_numero', '').strip()
    unidade_medida = data.get('unidade_medida', 'UND').strip()
    fabricante = data.get('fabricante', '').strip()
    tamanho_inicial = data.get('tamanho_inicial', 'U').strip()
    
    if not nome:
        return JsonResponse({'success': False, 'error': 'Nome do produto é obrigatório.'}, status=400)
    
    # Prevenção de duplicados exatos
    if Product.objects.filter(nome__iexact=nome).exists():
        return JsonResponse({'success': False, 'error': 'Já existe um produto com este nome.'}, status=400)
    
    try:
        with transaction.atomic():
            product = Product.objects.create(
                nome=nome,
                tipo_produto=tipo_produto,
                categoria=categoria if tipo_produto == 'EPI' else 'OUTRO',
                ca_numero=ca_numero if tipo_produto == 'EPI' else '',
                unidade_medida=unidade_medida,
                fabricante=fabricante,
                exige_ca=(tipo_produto == 'EPI' and bool(ca_numero)),
                controlado_individualmente=True,
                ativo=True
            )
            
            # Se tiver C.A. e for EPI, verifica/cria a entrada no CertificadoAprovacao
            ca_obj = None
            if tipo_produto == 'EPI' and ca_numero:
                num_norm = "".join([c for c in ca_numero if c.isdigit()])
                if num_norm:
                    ca_obj, created = CertificadoAprovacao.objects.get_or_create(
                        numero=num_norm,
                        defaults={
                            'numero_exibicao': ca_numero,
                            'fabricante': fabricante or 'Informado via NF',
                            'data_validade': timezone.now().date() + timezone.timedelta(days=365*2), # 2 anos padrão
                            'status_verificacao': 'INFORMADO_MANUALMENTE',
                            'justificativa_manual': 'Cadastrado automaticamente via recebimento de Nota Fiscal.'
                        }
                    )
            
            # Cria variante padrão
            variant = ProductVariant.objects.create(
                product=product,
                tamanho=tamanho_inicial or 'U',
                estoque_minimo=0,
                ativo=True
            )
            
            # Grava auditoria
            from audit.models import log_audit
            log_audit(
                request=request,
                action=f"Cadastro rápido de Produto: {product.nome} (Tipo: {product.tipo_produto}) via AJAX",
                model_name="Product",
                object_id=product.id,
                before=None,
                after={'nome': product.nome, 'tipo_produto': product.tipo_produto, 'ca_numero': product.ca_numero}
            )
            
            return JsonResponse({
                'success': True,
                'product': {
                    'id': product.id,
                    'nome': product.nome,
                    'tipo_produto': product.tipo_produto,
                    'ca_numero': product.ca_numero or '',
                    'unidade_medida': product.unidade_medida,
                    'variant_id': variant.id,
                    'tamanho': variant.tamanho,
                    'ca_id': ca_obj.id if ca_obj else None
                }
            })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


class PPEMatrixCreateView(LoginRequiredMixin, CreateView):
    model = PPEMatrix
    form_class = PPEMatrixForm
    template_name = "organizations/form.html"

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_tecnico() or request.user.is_admin()):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Apenas Técnicos SST ou Administradores podem gerenciar a matriz de EPI por função.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        function_pk = self.kwargs.get('function_pk')
        self.funcao = get_object_or_404(Function, pk=function_pk)
        kwargs['funcao'] = self.funcao
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Adicionar EPI à Matriz de {self.funcao.nome}"
        return context

    def form_valid(self, form):
        form.instance.funcao = self.funcao
        form.instance.criado_por = self.request.user
        response = super().form_valid(form)
        
        # Auditoria
        from audit.models import log_audit
        log_audit(
            request=self.request,
            action=f"Adicionado EPI {self.object.product.nome} à matriz da função {self.funcao.nome}",
            model_name="PPEMatrix",
            object_id=self.object.id,
            before=None,
            after={
                'funcao': self.funcao.nome,
                'produto': self.object.product.nome,
                'quantidade_padrao': self.object.quantidade_padrao,
                'vida_util_dias': self.object.vida_util_dias,
                'obrigatorio': self.object.obrigatorio,
                'principal': self.object.principal
            }
        )
        
        messages.success(self.request, f"EPI {self.object.product.nome} adicionado com sucesso à matriz.")
        return response

    def get_success_url(self):
        return reverse('function_detail', kwargs={'pk': self.funcao.id})


class PPEMatrixUpdateView(LoginRequiredMixin, UpdateView):
    model = PPEMatrix
    form_class = PPEMatrixForm
    template_name = "organizations/form.html"

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_tecnico() or request.user.is_admin()):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Apenas Técnicos SST ou Administradores podem gerenciar a matriz de EPI por função.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['funcao'] = self.get_object().funcao
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Editar Configuração na Matriz: {self.object.product.nome} para {self.object.funcao.nome}"
        return context

    def form_valid(self, form):
        old_obj = PPEMatrix.objects.get(pk=self.object.pk)
        before_state = {
            'quantidade_padrao': old_obj.quantidade_padrao,
            'vida_util_dias': old_obj.vida_util_dias,
            'obrigatorio': old_obj.obrigatorio,
            'principal': old_obj.principal,
            'ativo': old_obj.ativo
        }
        
        response = super().form_valid(form)
        
        # Auditoria
        from audit.models import log_audit
        log_audit(
            request=self.request,
            action=f"Atualizada configuração do EPI {self.object.product.nome} na matriz da função {self.object.funcao.nome}",
            model_name="PPEMatrix",
            object_id=self.object.id,
            before=before_state,
            after={
                'quantidade_padrao': self.object.quantidade_padrao,
                'vida_util_dias': self.object.vida_util_dias,
                'obrigatorio': self.object.obrigatorio,
                'principal': self.object.principal,
                'ativo': self.object.ativo
            }
        )
        
        messages.success(self.request, f"Configuração do EPI {self.object.product.nome} na matriz atualizada.")
        return response

    def get_success_url(self):
        return reverse('function_detail', kwargs={'pk': self.object.funcao.id})


@require_http_methods(["POST"])
def ppe_matrix_toggle_active(request, pk):
    if not (request.user.is_tecnico() or request.user.is_admin()):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Apenas Técnicos SST ou Administradores podem gerenciar a matriz de EPI por função.")
        
    entry = get_object_or_404(PPEMatrix, pk=pk)
    old_status = entry.ativo
    entry.ativo = not entry.ativo
    entry.save()
    
    # Auditoria
    from audit.models import log_audit
    log_audit(
        request=request,
        action=f"{'Ativada' if entry.ativo else 'Desativada'} entrada na matriz de EPI: {entry.product.nome} para {entry.funcao.nome}",
        model_name="PPEMatrix",
        object_id=entry.id,
        before={'ativo': old_status},
        after={'ativo': entry.ativo}
    )
    
    status_str = "ativado" if entry.ativo else "desativado"
    messages.success(request, f"EPI {entry.product.nome} foi {status_str} com sucesso na matriz de {entry.funcao.nome}.")
    return redirect('function_detail', pk=entry.funcao.id)


class PPEMatrixListView(LoginRequiredMixin, ListView):
    model = Function
    template_name = "ppe/matrix_list.html"
    context_object_name = "functions"
    paginate_by = 10

    def get_queryset(self):
        queryset = Function.objects.filter(ppe_matrix_entries__isnull=False).distinct()
        
        # Filtro de busca por nome da função
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(nome__icontains=q)
            
        # Filtro por empresa
        company_id = self.request.GET.get('company', '').strip()
        if company_id:
            queryset = queryset.filter(company_id=company_id)
            
        # Ordenação e prefetch de EPIs ativos e inativos para listagem
        queryset = queryset.select_related('company').prefetch_related(
            models.Prefetch('ppe_matrix_entries', queryset=PPEMatrix.objects.all().select_related('product', 'variant'))
        ).order_by('nome')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from organizations.models import Company
        context['companies'] = Company.objects.filter(ativo=True).order_by('razao_social')
        context['q'] = self.request.GET.get('q', '').strip()
        context['selected_company'] = self.request.GET.get('company', '').strip()
        return context


class PPEMatrixBulkCreateView(LoginRequiredMixin, FormView):
    form_class = PPEMatrixBulkForm
    template_name = "ppe/matrix_bulk_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_tecnico() or request.user.is_admin()):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Apenas Técnicos SST ou Administradores podem gerenciar a matriz de EPI.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Nova Matriz de EPI por Função"
        context['is_create'] = True
        return context

    def form_valid(self, form):
        funcao = form.cleaned_data['funcao']
        products = form.cleaned_data['products']
        quantidade_padrao = form.cleaned_data['quantidade_padrao']
        vida_util_dias = form.cleaned_data['vida_util_dias']
        obrigatorio = form.cleaned_data['obrigatorio']
        principal = form.cleaned_data['principal']
        orientacoes = form.cleaned_data['orientacoes']

        created_count = 0
        updated_count = 0
        
        with transaction.atomic():
            for product in products:
                # Procura ou cria a associação
                entry, created = PPEMatrix.objects.get_or_create(
                    funcao=funcao,
                    product=product,
                    defaults={
                        'quantidade_padrao': quantidade_padrao,
                        'vida_util_dias': vida_util_dias,
                        'obrigatorio': obrigatorio,
                        'principal': principal,
                        'orientacoes': orientacoes,
                        'ativo': True,
                        'criado_por': self.request.user
                    }
                )
                if created:
                    created_count += 1
                else:
                    entry.ativo = True
                    entry.quantidade_padrao = quantidade_padrao
                    entry.vida_util_dias = vida_util_dias
                    entry.obrigatorio = obrigatorio
                    entry.principal = principal
                    entry.orientacoes = orientacoes
                    entry.save()
                    updated_count += 1

            # Gravar log de auditoria
            from audit.models import log_audit
            log_audit(
                request=self.request,
                action=f"Criação/Atualização em lote da matriz de EPI para a função: {funcao.nome}",
                model_name="PPEMatrix",
                object_id=funcao.id,
                before=None,
                after={
                    'funcao': funcao.nome,
                    'produtos_associados': [p.nome for p in products],
                    'criados': created_count,
                    'atualizados': updated_count
                }
            )

        messages.success(self.request, f"Matriz da função {funcao.nome} salva com sucesso! ({created_count} novos associados, {updated_count} atualizados)")
        return redirect('function_detail', pk=funcao.id)


class PPEMatrixBulkUpdateView(LoginRequiredMixin, FormView):
    form_class = PPEMatrixBulkForm
    template_name = "ppe/matrix_bulk_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_tecnico() or request.user.is_admin()):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Apenas Técnicos SST ou Administradores podem gerenciar a matriz de EPI.")
        self.funcao = get_object_or_404(Function, pk=self.kwargs.get('function_pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['is_update'] = True
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial['funcao'] = self.funcao
        active_entries = PPEMatrix.objects.filter(funcao=self.funcao, ativo=True)
        initial['products'] = [entry.product.id for entry in active_entries]
        
        first_entry = active_entries.first()
        if first_entry:
            initial['quantidade_padrao'] = first_entry.quantidade_padrao
            initial['vida_util_dias'] = first_entry.vida_util_dias
            initial['obrigatorio'] = first_entry.obrigatorio
            initial['principal'] = first_entry.principal
            initial['orientacoes'] = first_entry.orientacoes
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Editar Matriz de EPI por Função: {self.funcao.nome}"
        context['funcao'] = self.funcao
        context['is_create'] = False
        return context

    def form_valid(self, form):
        products = form.cleaned_data['products']
        quantidade_padrao = form.cleaned_data['quantidade_padrao']
        vida_util_dias = form.cleaned_data['vida_util_dias']
        obrigatorio = form.cleaned_data['obrigatorio']
        principal = form.cleaned_data['principal']
        orientacoes = form.cleaned_data['orientacoes']

        from audit.models import log_audit
        old_active_products = list(PPEMatrix.objects.filter(funcao=self.funcao, ativo=True).values_list('product__nome', flat=True))

        with transaction.atomic():
            # 1. Inativa os EPIs que foram desmarcados
            current_active = PPEMatrix.objects.filter(funcao=self.funcao, ativo=True)
            deactivated_count = 0
            for entry in current_active:
                if entry.product not in products:
                    entry.ativo = False
                    entry.save()
                    deactivated_count += 1

            # 2. Cria ou Reativa os marcados
            created_count = 0
            reactivated_count = 0
            for product in products:
                entry, created = PPEMatrix.objects.get_or_create(
                    funcao=self.funcao,
                    product=product,
                    defaults={
                        'quantidade_padrao': quantidade_padrao,
                        'vida_util_dias': vida_util_dias,
                        'obrigatorio': obrigatorio,
                        'principal': principal,
                        'orientacoes': orientacoes,
                        'ativo': True,
                        'criado_por': self.request.user
                    }
                )
                if created:
                    created_count += 1
                else:
                    if not entry.ativo:
                        entry.ativo = True
                        entry.quantidade_padrao = quantidade_padrao
                        entry.vida_util_dias = vida_util_dias
                        entry.obrigatorio = obrigatorio
                        entry.principal = principal
                        entry.orientacoes = orientacoes
                        entry.save()
                        reactivated_count += 1

            # Grava auditoria
            log_audit(
                request=self.request,
                action=f"Atualização em lote da matriz de EPI para a função: {self.funcao.nome}",
                model_name="PPEMatrix",
                object_id=self.funcao.id,
                before={'produtos_ativos_anterior': old_active_products},
                after={
                    'produtos_ativos_novo': [p.nome for p in products],
                    'desativados': deactivated_count,
                    'criados': created_count,
                    'reativados': reactivated_count
                }
            )

        messages.success(self.request, f"Matriz da função {self.funcao.nome} atualizada com sucesso! (Desativados: {deactivated_count}, Novos: {created_count}, Reativados: {reactivated_count})")
        return redirect('function_detail', pk=self.funcao.id)


class PPEMatrixBulkDeleteView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_tecnico() or request.user.is_admin()):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Apenas Técnicos SST ou Administradores podem excluir a matriz de EPI.")
        self.funcao = get_object_or_404(Function, pk=self.kwargs.get('function_pk'))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        entries = PPEMatrix.objects.filter(funcao=self.funcao)
        return render(request, "ppe/matrix_confirm_delete.html", {
            'funcao': self.funcao,
            'entries': entries
        })

    def post(self, request, *args, **kwargs):
        entries = PPEMatrix.objects.filter(funcao=self.funcao)
        entries_info = [f"{e.product.nome} (Ativo: {e.ativo})" for e in entries]
        
        from django.db.models import ProtectedError
        try:
            with transaction.atomic():
                count = entries.count()
                entries.delete()
                
                # Grava auditoria
                from audit.models import log_audit
                log_audit(
                    request=self.request,
                    action=f"Exclusão física da matriz de EPI da função: {self.funcao.nome}",
                    model_name="PPEMatrix",
                    object_id=self.funcao.id,
                    before={'itens_excluidos': entries_info},
                    after=None
                )
                
            messages.success(request, f"Matriz de EPIs da função {self.funcao.nome} excluída com sucesso! ({count} registros removidos)")
            return redirect('matrix_list')
        except ProtectedError:
            messages.error(request, "Não foi possível excluir a matriz porque alguns itens estão vinculados a outros registros protegidos no sistema.")
            return redirect('function_detail', pk=self.funcao.id)


@require_http_methods(["GET"])
def ca_consultar_ajax(request):
    """
    Consulta rápida de um Certificado de Aprovação (CA) pelo número no ConsultaCA com cache.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Autenticação necessária.'}, status=401)

    q = request.GET.get('q', '').strip()
    
    # Remove "CA" prefix or dashes
    q_clean = q.upper().replace('CA', '').replace('-', '').strip()
    
    # Ensure parameter has only digits and is within limits (max 20 chars)
    if not q_clean.isdigit() or len(q_clean) > 20:
        return JsonResponse({'success': False, 'error': 'Número de CA inválido (deve conter apenas dígitos, máximo 20 caracteres).'}, status=400)
        
    from .ca_services import ConsultaCAService
    
    try:
        result = ConsultaCAService.get_or_query(q_clean)
    except Exception as e:
        import logging
        logger = logging.getLogger('ppe.views')
        logger.error(f"Erro ao consultar CA {q_clean}: {str(e)}")
        return JsonResponse({
            'success': False,
            'indisponivel': True,
            'error': 'Não foi possível consultar o CA neste momento. Você pode tentar novamente ou continuar o cadastro informando os dados manualmente.'
        })
    
    # Check if the query returned a non-success response due to external service unavailability
    if not result.get('success', False):
        if result.get('indisponivel', False):
            return JsonResponse({
                'success': False,
                'indisponivel': True,
                'error': result.get('error', 'Não foi possível consultar o CA neste momento. Você pode tentar novamente ou continuar o cadastro informando os dados manualmente.')
            })
        return JsonResponse({'success': False, 'error': result.get('error', 'Erro desconhecido.')}, status=400)
        
    return JsonResponse(result)



