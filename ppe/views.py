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
from organizations.models import Unit, InventoryLocation, Function, Sector
from inventory.models import Lot, StockMovement
from inventory.services import get_stock_balance
from employees.models import Employee
from .models import Product, ProductVariant, CertificadoAprovacao, PPEMatrix, PPEDelivery, ExtraordinaryPPE, SectorPPEMatrix
from .services import deliver_ppe, confirm_delivery_signature, return_ppe, write_off_ppe, sync_product_variants
from .forms import ProductForm, PPEMatrixForm, PPEMatrixBulkForm, PPEMatrixFormSet, PPEMatrixFunctionForm, PPEDeliveryForm, PPEMatrixSectorFormSet, PPEMatrixSectorChoiceForm


class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "ppe/product_list.html"
    context_object_name = "products"
    paginate_by = 20

    def get_queryset(self):
        queryset = Product.objects.all().order_by('nome')
        
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(models.Q(nome__icontains=q) | models.Q(descricao__icontains=q))
            
        ca = self.request.GET.get('ca', '').strip()
        if ca:
            ca_clean = "".join([c for c in ca if c.isdigit()])
            queryset = queryset.filter(ca_numero__icontains=ca_clean or ca)
            
        tipo = self.request.GET.get('tipo', '').strip()
        if tipo:
            queryset = queryset.filter(tipo_produto=tipo)
            
        categoria = self.request.GET.get('categoria', '').strip()
        if categoria:
            queryset = queryset.filter(categoria=categoria)
            
        fabricante = self.request.GET.get('fabricante', '').strip()
        if fabricante:
            queryset = queryset.filter(fabricante__icontains=fabricante)
            
        ativo = self.request.GET.get('ativo', '').strip()
        if ativo == '1':
            queryset = queryset.filter(ativo=True)
        elif ativo == '0':
            queryset = queryset.filter(ativo=False)

        return queryset

    def get_context_data(self, **kwargs):
        if not hasattr(self, 'object_list'):
            self.object_list = self.get_queryset()
        context = super().get_context_data(**kwargs)
        context['tipo_choices'] = Product.TIPO_PRODUTO_CHOICES
        context['categoria_choices'] = Product.CATEGORIA_CHOICES
        context['filter_q'] = self.request.GET.get('q', '').strip()
        context['filter_ca'] = self.request.GET.get('ca', '').strip()
        context['filter_tipo'] = self.request.GET.get('tipo', '').strip()
        context['filter_categoria'] = self.request.GET.get('categoria', '').strip()
        context['filter_fabricante'] = self.request.GET.get('fabricante', '').strip()
        context['filter_ativo'] = self.request.GET.get('ativo', '').strip()
        return context


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "ppe/product_form.html"
    success_url = "/ppe/"

    def get_context_data(self, **kwargs):
        from .constants import CANONICAL_SIZES_BY_GROUP
        context = super().get_context_data(**kwargs)
        context['title'] = "Novo Produto / EPI"
        context['size_catalog_groups'] = CANONICAL_SIZES_BY_GROUP
        
        ca_numero = None
        if self.request.method == 'POST':
            ca_numero = self.request.POST.get('ca_numero')
            context['selected_sizes'] = self.request.POST.getlist('tamanhos')
            context['tem_variacao_tamanho'] = self.request.POST.get('tem_variacao_tamanho', 'nao')
        else:
            context['selected_sizes'] = []
            context['tem_variacao_tamanho'] = 'nao'
            
        if ca_numero:
            num_norm = "".join([c for c in str(ca_numero) if c.isdigit()])
            if num_norm:
                context['ca_obj'] = CertificadoAprovacao.objects.filter(numero=num_norm).first()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        tamanhos_list = form.cleaned_data.get('tamanhos_list')
        if not tamanhos_list:
            tamanhos_list = form.cleaned_data.get('tamanhos_str') or self.request.POST.getlist('tamanhos') or 'U'
            
        _, warnings = sync_product_variants(self.object, tamanhos_list)
        for msg in warnings:
            messages.warning(self.request, msg)
        messages.success(self.request, f"EPI '{self.object.nome}' cadastrado com sucesso!")
        return response


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "ppe/product_form.html"
    success_url = "/ppe/"

    def get_context_data(self, **kwargs):
        from .constants import CANONICAL_SIZES_BY_GROUP
        context = super().get_context_data(**kwargs)
        context['title'] = f"Editar Produto: {self.object.nome}"
        context['size_catalog_groups'] = CANONICAL_SIZES_BY_GROUP
        
        active_vars = list(self.object.variants.filter(ativo=True).values_list('tamanho', flat=True))
        non_unique = [t for t in active_vars if t != 'U']
        
        if self.request.method == 'POST':
            ca_numero = self.request.POST.get('ca_numero')
            context['selected_sizes'] = self.request.POST.getlist('tamanhos')
            context['tem_variacao_tamanho'] = self.request.POST.get('tem_variacao_tamanho', 'nao')
        else:
            ca_numero = self.object.ca_numero
            context['selected_sizes'] = non_unique
            context['tem_variacao_tamanho'] = 'sim' if non_unique else 'nao'
            
        if ca_numero:
            num_norm = "".join([c for c in str(ca_numero) if c.isdigit()])
            if num_norm:
                context['ca_obj'] = CertificadoAprovacao.objects.filter(numero=num_norm).first()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        tamanhos_list = form.cleaned_data.get('tamanhos_list')
        if not tamanhos_list:
            tamanhos_list = form.cleaned_data.get('tamanhos_str') or self.request.POST.getlist('tamanhos') or 'U'
            
        _, warnings = sync_product_variants(self.object, tamanhos_list)
        for msg in warnings:
            messages.warning(self.request, msg)
        messages.success(self.request, f"EPI '{self.object.nome}' atualizado com sucesso!")
        return response



class ProductDetailView(LoginRequiredMixin, DetailView):
    model = Product
    template_name = "ppe/product_detail.html"
    context_object_name = "product"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['variants'] = self.object.variants.all()
        
        # Load CA details if they exist
        if self.object.ca_numero:
            num_norm = "".join([c for c in str(self.object.ca_numero) if c.isdigit()])
            if num_norm:
                context['ca_obj'] = CertificadoAprovacao.objects.filter(numero=num_norm).first()

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


class ProductVariantCreateView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        product_id = self.kwargs.get('product_pk')
        messages.info(request, "O gerenciamento de tamanhos e variantes é realizado exclusivamente na tela de edição do EPI.")
        return redirect('product_update', pk=product_id)

    def post(self, request, *args, **kwargs):
        product_id = self.kwargs.get('product_pk')
        messages.info(request, "O gerenciamento de tamanhos e variantes é realizado exclusivamente na tela de edição do EPI.")
        return redirect('product_update', pk=product_id)


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
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            user_units = Unit.objects.all()
        
        queryset = PPEDelivery.objects.filter(unit__in=user_units).select_related(
            'employee', 'product_variant__product', 'ca_entregue', 'lot', 'setor', 'funcao'
        )

        data_inicio = self.request.GET.get('data_inicio', '').strip()
        if data_inicio:
            queryset = queryset.filter(data_entrega__gte=data_inicio)

        data_fim = self.request.GET.get('data_fim', '').strip()
        if data_fim:
            queryset = queryset.filter(data_entrega__lte=data_fim)

        q = self.request.GET.get('q', '').strip()
        if q:
            q_clean = "".join([c for c in q if c.isdigit()])
            queryset = queryset.filter(
                models.Q(employee__nome_completo__icontains=q) |
                models.Q(employee__matricula__icontains=q) |
                models.Q(employee__cpf__icontains=q_clean or q)
            )

        product_id = self.request.GET.get('product', '').strip()
        if product_id:
            queryset = queryset.filter(product_variant__product_id=product_id)

        setor_id = self.request.GET.get('setor', '').strip()
        if setor_id:
            queryset = queryset.filter(setor_id=setor_id)

        status_ass = self.request.GET.get('status_assinatura', '').strip()
        if status_ass:
            queryset = queryset.filter(status_assinatura=status_ass)

        return queryset.order_by('-data_entrega')

    def get_context_data(self, **kwargs):
        if not hasattr(self, 'object_list'):
            self.object_list = self.get_queryset()
        context = super().get_context_data(**kwargs)
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            user_units = Unit.objects.all()

        from organizations.models import Sector
        context['products'] = Product.objects.filter(ativo=True).order_by('nome')
        context['sectors'] = Sector.objects.filter(unit__in=user_units).order_by('nome')
        context['status_choices'] = PPEDelivery.SIGN_STATUS
        
        context['filter_data_inicio'] = self.request.GET.get('data_inicio', '').strip()
        context['filter_data_fim'] = self.request.GET.get('data_fim', '').strip()
        context['filter_q'] = self.request.GET.get('q', '').strip()
        context['filter_product'] = self.request.GET.get('product', '').strip()
        context['filter_setor'] = self.request.GET.get('setor', '').strip()
        context['filter_status_assinatura'] = self.request.GET.get('status_assinatura', '').strip()
        return context


class PPEDeliveryCreateView(LoginRequiredMixin, CreateView):
    model = PPEDelivery
    form_class = PPEDeliveryForm
    template_name = "ppe/delivery_form.html"

    def get_initial(self):
        initial = super().get_initial()
        if not initial.get('data_entrega'):
            initial['data_entrega'] = timezone.now().date()
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        user_units = user.units.all()
        if user.is_superuser and not user_units.exists():
            user_units = Unit.objects.all()

        # Filtra colaboradores da unidade permitida
        form.fields['employee'].queryset = Employee.objects.filter(unit__in=user_units, situacao='ATIVO')

        # Filtra lotes disponíveis no estoque SST das unidades permitidas
        sst_locations = InventoryLocation.objects.filter(unit__in=user_units, tipo='SST', ativo=True)
        lots_qs = Lot.objects.select_related('product_variant__product').order_by(
            'data_validade',
            'product_variant__product__nome',
            'identificador'
        )

        lot_choices = [('', 'Selecione o EPI disponível no estoque SST...')]
        available_lot_ids = []

        for lot in lots_qs:
            total_bal = 0
            for loc in sst_locations:
                total_bal += get_stock_balance(loc, lot.product_variant, lot)
            
            if total_bal > 0:
                available_lot_ids.append(lot.id)
                prod_nome = lot.product_variant.product.nome
                tam = lot.product_variant.tamanho
                val_str = lot.data_validade.strftime('%d/%m/%Y') if lot.data_validade else 'Sem validade'
                label = f"{prod_nome} — Tamanho {tam} — Lote {lot.identificador} — Validade {val_str} — Saldo: {total_bal}"
                lot_choices.append((lot.id, label))

        form.fields['lot'].queryset = Lot.objects.filter(id__in=available_lot_ids)
        form.fields['lot'].choices = lot_choices

        # Pré-seleção segura do colaborador via query param ?employee=<id>
        emp_param = self.request.GET.get('employee', '').strip()
        if emp_param:
            try:
                emp_id = int(emp_param)
                emp = Employee.objects.filter(id=emp_id, unit__in=user_units).first()
                if emp and emp.situacao == 'ATIVO':
                    form.fields['employee'].initial = emp.id
                elif emp and emp.situacao != 'ATIVO':
                    messages.warning(self.request, f"O colaborador '{emp.nome_completo}' informado está {emp.get_situacao_display().lower()} e não pode receber entregas de EPI.")
                else:
                    messages.warning(self.request, "O colaborador informado na URL não foi encontrado ou não pertence ao seu escopo de acesso.")
            except (ValueError, TypeError):
                messages.warning(self.request, "Identificador de colaborador inválido recebido na URL.")

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
                    after={'colaborador': employee.nome_completo, 'matricula': employee.matricula, 'quantidade': quantidade, 'status_assinatura': delivery.status_assinatura}
                )
                
                messages.success(request, f"EPI {product_variant.product.nome} entregue com sucesso para {employee.nome_completo}! Estoque baixado.")
                return redirect('employee_detail', pk=employee.id)
            except Exception as e:
                messages.error(request, f"Erro ao realizar entrega: {str(e)}")
        else:
            messages.error(request, f"Erro no formulário: {form.errors.as_text()}")
        return render(request, self.template_name, {'form': form})


def delivery_sign_view(request, pk):
    delivery = get_object_or_404(PPEDelivery, pk=pk)
    messages.info(request, "A etapa de assinatura manual do colaborador foi desativada temporariamente. As entregas de EPI são concluídas diretamente pelo operador.")
    return redirect('employee_detail', pk=delivery.employee.id)



@require_http_methods(["GET"])
def product_search_ajax(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Autenticação necessária.'}, status=401)

    q = request.GET.get('q', '').strip()
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (ValueError, TypeError):
        page = 1
    try:
        page_size = min(50, max(1, int(request.GET.get('page_size', 20))))
    except (ValueError, TypeError):
        page_size = 20

    tipo_produto = request.GET.get('tipo_produto', '').strip()

    products = Product.objects.filter(ativo=True)
    if tipo_produto:
        products = products.filter(tipo_produto=tipo_produto)

    if q:
        q_digits = "".join([c for c in q if c.isdigit()])
        filter_q = models.Q(nome__icontains=q) | models.Q(fabricante__icontains=q)
        if q_digits:
            filter_q |= models.Q(ca_numero__icontains=q_digits)
        else:
            filter_q |= models.Q(ca_numero__icontains=q)
        products = products.filter(filter_q)

    total_count = products.count()
    start = (page - 1) * page_size
    end = start + page_size
    page_qs = products.order_by('nome')[start:end]

    items = []
    for p in page_qs:
        text_display = f"{p.nome} — C.A. {p.ca_numero}" if p.ca_numero else p.nome
        items.append({
            'id': p.id,
            'text': text_display,
            'nome': p.nome,
            'tipo_produto': p.tipo_produto,
            'ca_numero': p.ca_numero or '',
            'unidade_medida': p.unidade_medida,
            'fabricante': p.fabricante or '',
        })

    has_more = end < total_count
    return JsonResponse({
        'success': True,
        'results': items,
        'items': items,
        'has_more': has_more,
        'total_count': total_count
    })


@require_http_methods(["GET"])
def product_variants_ajax(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Autenticação necessária.'}, status=401)

    product_id = request.GET.get('product_id')
    if not product_id:
        return JsonResponse({'error': 'Parâmetro product_id é obrigatório.'}, status=400)

    try:
        product = Product.objects.get(id=int(product_id), ativo=True)
    except (Product.DoesNotExist, ValueError):
        return JsonResponse({'error': 'Produto não encontrado ou inativo.'}, status=404)

    variants = list(ProductVariant.objects.filter(product=product, ativo=True))

    def sort_variant_key(v):
        t = v.tamanho.strip().upper()
        predefined = {'PP': 1, 'P': 2, 'M': 3, 'G': 4, 'GG': 5, 'XG': 6, 'XXG': 7, 'U': 99}
        if t in predefined:
            return (0, predefined[t], t)
        if t.isdigit():
            return (1, int(t), t)
        return (2, 0, t)

    variants.sort(key=sort_variant_key)

    items = []
    for v in variants:
        items.append({
            'id': v.id,
            'tamanho': v.tamanho,
            'text': f"Tamanho: {v.tamanho}" if v.tamanho != 'U' else 'Tamanho Único (U)'
        })

    return JsonResponse({
        'success': True,
        'product_id': product.id,
        'product_nome': product.nome,
        'ca_numero': product.ca_numero or '',
        'unidade_medida': product.unidade_medida,
        'variants': items,
        'count': len(items)
    })



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

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.instance.funcao = self.funcao
        return form

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


class SectorPPEMatrixListView(LoginRequiredMixin, ListView):
    model = Sector
    template_name = "ppe/sector_matrix_list.html"
    context_object_name = "sectors"
    paginate_by = 15

    def get_queryset(self):
        user = self.request.user
        queryset = Sector.objects.filter(ativo=True).select_related('unit', 'unit__company', 'ppe_matrix_config', 'ppe_matrix_config__ativado_por').prefetch_related('employees')
        if not user.is_superuser:
            queryset = queryset.filter(unit__in=user.units.all())

        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(models.Q(nome__icontains=q) | models.Q(unit__nome__icontains=q) | models.Q(unit__codigo__icontains=q))

        company_id = self.request.GET.get('company', '').strip()
        if company_id:
            queryset = queryset.filter(unit__company_id=company_id)

        status_filter = self.request.GET.get('status', '').strip()
        if status_filter == 'ATIVA':
            queryset = queryset.filter(ppe_matrix_config__status='ATIVA')
        elif status_filter == 'EM_ELABORACAO':
            queryset = queryset.filter(ppe_matrix_config__status='EM_ELABORACAO')
        elif status_filter == 'SEM_CONFIGURACAO':
            queryset = queryset.filter(ppe_matrix_config__isnull=True)

        return queryset.order_by('unit__company__nome_fantasia', 'unit__codigo', 'nome')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from organizations.models import Company
        user = self.request.user
        comp_qs = Company.objects.filter(ativo=True)
        if not user.is_superuser:
            comp_qs = comp_qs.filter(units__in=user.units.all()).distinct()
        context['companies'] = comp_qs.order_by('nome_fantasia')
        context['q'] = self.request.GET.get('q', '').strip()
        context['selected_company'] = self.request.GET.get('company', '').strip()
        context['selected_status'] = self.request.GET.get('status', '').strip()
        return context


class SectorPPEMatrixEditView(LoginRequiredMixin, View):
    template_name = "ppe/sector_matrix_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_tecnico() or request.user.is_admin()):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Apenas Técnicos SST ou Administradores podem gerenciar matrizes de EPI.")
        self.sector = get_object_or_404(Sector, pk=self.kwargs.get('sector_pk'))
        if not request.user.is_superuser and not request.user.units.filter(id=self.sector.unit_id).exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Você não tem acesso à Unidade deste setor.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        config, _ = SectorPPEMatrix.objects.get_or_create(sector=self.sector)
        formset = PPEMatrixSectorFormSet(instance=self.sector, queryset=PPEMatrix.objects.filter(setor=self.sector, ativo=True))
        return render(request, self.template_name, {
            'sector': self.sector,
            'config': config,
            'formset': formset,
        })

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', 'save_draft')
        config, _ = SectorPPEMatrix.objects.get_or_create(sector=self.sector)
        formset = PPEMatrixSectorFormSet(request.POST, instance=self.sector)
        if formset.is_valid():
            # Conta itens que permanecerão ativos após a submissão
            active_items_count = 0
            for form in formset.forms:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    if form.cleaned_data.get('product'):
                        active_items_count += 1

            if action == 'save_and_activate' and active_items_count == 0:
                messages.error(request, "Não foi possível ativar a matriz. Adicione pelo menos um EPI.")
                return render(request, self.template_name, {
                    'sector': self.sector,
                    'config': config,
                    'formset': formset,
                })

            with transaction.atomic():
                instances = formset.save(commit=False)
                for obj in instances:
                    obj.setor = self.sector
                    obj.ativo = True
                    if not obj.criado_por_id:
                        obj.criado_por = request.user
                    obj.save()

                for obj in formset.deleted_objects:
                    obj.delete()

                old_status = config.status
                if action == 'save_and_activate':
                    config.status = 'ATIVA'
                    config.ativado_por = request.user
                    config.ativado_em = timezone.now()
                    config.save()
                    msg = "Matriz do setor ativada com sucesso."
                elif config.status == 'ATIVA':
                    # Matriz ativa editada: mantém ativa
                    msg = f"Alterações da matriz do setor '{self.sector.nome}' salvas com sucesso!"
                else:
                    # Salvar como elaboração
                    config.status = 'EM_ELABORACAO'
                    config.save()
                    msg = "Matriz salva como elaboração. Ela ainda não está sendo utilizada nas recomendações de EPI."

                from audit.models import log_audit
                log_audit(
                    request=request,
                    action=f"Atualização da matriz de EPI do setor: {self.sector.nome} ({self.sector.unit.codigo}) - Status: {config.status}",
                    model_name="SectorPPEMatrix",
                    object_id=self.sector.id,
                    before={'status': old_status},
                    after={'setor': self.sector.nome, 'status': config.status, 'itens_salvos': len(instances)}
                )

            messages.success(request, msg)
            return redirect('sector_matrix_list')

        if action == 'save_and_activate':
            messages.error(request, "Não foi possível ativar a matriz. Adicione pelo menos um EPI.")

        return render(request, self.template_name, {
            'sector': self.sector,
            'config': config,
            'formset': formset,
        })


class SectorPPEMatrixActivateView(LoginRequiredMixin, View):
    def post(self, request, sector_pk):
        if not (request.user.is_tecnico() or request.user.is_admin()):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Apenas Técnicos SST ou Administradores podem ativar a matriz de EPI.")
        sector = get_object_or_404(Sector, pk=sector_pk)
        if not request.user.is_superuser and not request.user.units.filter(id=sector.unit_id).exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Você não tem acesso à Unidade deste setor.")

        # Valida se possui pelo menos 1 item ativo
        active_items_count = PPEMatrix.objects.filter(setor=sector, ativo=True).count()
        if active_items_count == 0:
            messages.error(request, "Não foi possível ativar a matriz. Adicione pelo menos um EPI.")
            return redirect('sector_matrix_edit', sector_pk=sector.pk)

        config, _ = SectorPPEMatrix.objects.get_or_create(sector=sector)
        old_status = config.status
        config.status = 'ATIVA'
        config.ativado_por = request.user
        config.ativado_em = timezone.now()
        config.save()

        from audit.models import log_audit
        log_audit(
            request=request,
            action=f"Ativação explícita da matriz de EPI do setor: {sector.nome} ({sector.unit.codigo})",
            model_name="SectorPPEMatrix",
            object_id=sector.id,
            before={'status': old_status},
            after={'status': 'ATIVA', 'ativado_por': request.user.username, 'itens_ativos': active_items_count}
        )

        messages.success(request, "Matriz do setor ativada com sucesso.")
        return redirect('sector_matrix_list')


class SectorPPEMatrixDeactivateView(LoginRequiredMixin, View):
    def post(self, request, sector_pk):
        if not (request.user.is_tecnico() or request.user.is_admin()):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Apenas Técnicos SST ou Administradores podem alterar o status da matriz.")
        sector = get_object_or_404(Sector, pk=sector_pk)
        if not request.user.is_superuser and not request.user.units.filter(id=sector.unit_id).exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Você não tem acesso à Unidade deste setor.")

        config = get_object_or_404(SectorPPEMatrix, sector=sector)
        old_status = config.status
        config.status = 'EM_ELABORACAO'
        config.save()

        from audit.models import log_audit
        log_audit(
            request=request,
            action=f"Retorno da matriz de EPI do setor para Em Elaboração: {sector.nome} ({sector.unit.codigo})",
            model_name="SectorPPEMatrix",
            object_id=sector.id,
            before={'status': old_status},
            after={'status': 'EM_ELABORACAO'}
        )

        messages.warning(request, f"Matriz do setor '{sector.nome}' retornada para 'Em Elaboração'. O setor permanecerá sem matriz ativa até nova ativação.")
        return redirect('sector_matrix_list')


class SectorPPEMatrixCreateView(LoginRequiredMixin, View):
    template_name = "ppe/sector_matrix_create.html"

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_tecnico() or request.user.is_admin()):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Apenas Técnicos SST ou Administradores podem gerenciar matrizes de EPI.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        sector_id = request.GET.get('setor')
        if sector_id:
            sector = Sector.objects.filter(pk=sector_id).first()
            if sector:
                if not request.user.is_superuser and not request.user.units.filter(id=sector.unit_id).exists():
                    from django.core.exceptions import PermissionDenied
                    raise PermissionDenied("Você não tem acesso à Unidade deste setor.")
                if PPEMatrix.objects.filter(setor=sector, ativo=True).exists():
                    messages.info(request, f"O setor '{sector.nome}' já possui uma Matriz de EPI cadastrada. Você foi redirecionado para a edição.")
                    return redirect('sector_matrix_edit', sector_pk=sector.pk)

        sector_form = PPEMatrixSectorChoiceForm(request.GET or None, user=request.user)
        formset = PPEMatrixSectorFormSet(queryset=PPEMatrix.objects.none())
        return render(request, self.template_name, {
            'sector_form': sector_form,
            'formset': formset,
        })

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action', 'save_draft')
        sector_form = PPEMatrixSectorChoiceForm(request.POST, user=request.user)
        if not sector_form.is_valid():
            formset = PPEMatrixSectorFormSet(request.POST)
            return render(request, self.template_name, {
                'sector_form': sector_form,
                'formset': formset,
            })

        sector = sector_form.cleaned_data['setor']
        if not request.user.is_superuser and not request.user.units.filter(id=sector.unit_id).exists():
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Você não tem acesso à Unidade deste setor.")

        if PPEMatrix.objects.filter(setor=sector, ativo=True).exists():
            messages.info(request, f"O setor '{sector.nome}' já possui uma Matriz de EPI cadastrada. Você foi redirecionado para a edição.")
            return redirect('sector_matrix_edit', sector_pk=sector.pk)

        formset = PPEMatrixSectorFormSet(request.POST, instance=sector)
        if formset.is_valid():
            active_items_count = 0
            for form in formset.forms:
                if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                    if form.cleaned_data.get('product'):
                        active_items_count += 1

            if action == 'save_and_activate' and active_items_count == 0:
                messages.error(request, "Não foi possível ativar a matriz. Adicione pelo menos um EPI.")
                return render(request, self.template_name, {
                    'sector_form': sector_form,
                    'formset': formset,
                })

            with transaction.atomic():
                config, _ = SectorPPEMatrix.objects.get_or_create(sector=sector, defaults={'status': 'EM_ELABORACAO'})
                instances = formset.save(commit=False)
                for obj in instances:
                    obj.setor = sector
                    obj.ativo = True
                    if not obj.criado_por_id:
                        obj.criado_por = request.user
                    obj.save()

                for obj in formset.deleted_objects:
                    obj.delete()

                if action == 'save_and_activate':
                    config.status = 'ATIVA'
                    config.ativado_por = request.user
                    config.ativado_em = timezone.now()
                    config.save()
                    msg = "Matriz do setor ativada com sucesso."
                else:
                    config.status = 'EM_ELABORACAO'
                    config.save()
                    msg = "Matriz salva como elaboração. Ela ainda não está sendo utilizada nas recomendações de EPI."

                from audit.models import log_audit
                log_audit(
                    request=request,
                    action=f"Criação da matriz de EPI do setor: {sector.nome} ({sector.unit.codigo}) - Status: {config.status}",
                    model_name="SectorPPEMatrix",
                    object_id=sector.id,
                    before=None,
                    after={'setor': sector.nome, 'status': config.status, 'itens_cadastrados': len(instances)}
                )

            messages.success(request, msg)
            return redirect('sector_matrix_list')

        if action == 'save_and_activate':
            messages.error(request, "Não foi possível ativar a matriz. Adicione pelo menos um EPI.")

        return render(request, self.template_name, {
            'sector_form': sector_form,
            'formset': formset,
        })


class LegacyMatrixRedirectView(LoginRequiredMixin, View):
    """
    Redireciona tentativas de acesso a URLs legadas de Matriz por Função
    para a listagem canônica de matrizes por Setor com mensagem informativa.
    """
    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "A Matriz de EPI agora é gerenciada exclusivamente por Setor.")
        return redirect('sector_matrix_list')


# Aliases para retrocompatibilidade de imports e URLs
SectorPPEMatrixCreateViewAlias = SectorPPEMatrixCreateView
PPEMatrixBulkCreateView = SectorPPEMatrixCreateView
PPEMatrixListView = LegacyMatrixRedirectView
PPEMatrixBulkUpdateView = LegacyMatrixRedirectView
PPEMatrixBulkDeleteView = LegacyMatrixRedirectView


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
        
    # Check if CA is already registered in an existing Product in the system
    exclude_id = request.GET.get('exclude_id')
    existing_qs = Product.objects.filter(ca_numero=q_clean)
    if exclude_id and exclude_id.isdigit():
        existing_qs = existing_qs.exclude(id=int(exclude_id))
        
    existing_product = existing_qs.first()
    if existing_product:
        variantes = list(existing_product.variants.filter(ativo=True).values_list('tamanho', flat=True))
        if not variantes:
            variantes = [existing_product.tamanho_padrao] if existing_product.tamanho_padrao else ['Único']
        return JsonResponse({
            'success': True,
            'already_registered': True,
            'existing_product': {
                'id': existing_product.id,
                'nome': existing_product.nome,
                'ca_numero': existing_product.ca_numero,
                'variantes': variantes,
                'variantes_str': ', '.join(variantes) if variantes else 'Único',
                'edit_url': reverse('product_update', args=[existing_product.id]),
            },
            'message': (
                f"Este C.A. já está cadastrado no sistema.\n\n"
                f"EPI: {existing_product.nome}\n"
                f"Tamanhos atuais: {', '.join(variantes)}\n\n"
                f"Para incluir outro tamanho, edite o cadastro existente. Não crie um novo EPI para cada tamanho."
            )
        })

    from .ca_services import ConsultaCAService
    
    force = request.GET.get('force') == 'true'
    
    try:
        result = ConsultaCAService.get_or_query(q_clean, force=force)
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



