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
from .services import deliver_ppe, confirm_delivery_signature, return_ppe, write_off_ppe, sync_product_variants
from .forms import ProductForm, PPEMatrixForm, PPEMatrixBulkForm, PPEMatrixFormSet, PPEMatrixFunctionForm, PPEDeliveryForm

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
        context = super().get_context_data(**kwargs)
        context['title'] = "Novo Produto / EPI"
        
        ca_numero = None
        if self.request.method == 'POST':
            ca_numero = self.request.POST.get('ca_numero')
            
        if ca_numero:
            num_norm = "".join([c for c in str(ca_numero) if c.isdigit()])
            if num_norm:
                context['ca_obj'] = CertificadoAprovacao.objects.filter(numero=num_norm).first()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        tamanhos_str = form.cleaned_data.get('tamanhos_str')
        if tamanhos_str is None:
            tamanhos_str = self.request.POST.get('tamanhos_str', '').strip()
            
        _, warnings = sync_product_variants(self.object, tamanhos_str)
        for msg in warnings:
            messages.warning(self.request, msg)
        return response


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "ppe/product_form.html"
    success_url = "/ppe/"

    def get_initial(self):
        initial = super().get_initial()
        if hasattr(self, 'object') and self.object:
            active_vars = self.object.variants.filter(ativo=True).order_by('id')
            if active_vars.exists():
                initial['tamanhos_str'] = ", ".join([v.tamanho for v in active_vars])
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f"Editar Produto: {self.object.nome}"
        
        if 'form' in context and hasattr(self, 'object') and self.object and not context['form'].is_bound:
            active_vars = self.object.variants.filter(ativo=True).order_by('id')
            if active_vars.exists():
                context['form'].fields['tamanhos_str'].initial = ", ".join([v.tamanho for v in active_vars])

        ca_numero = None
        if self.request.method == 'POST':
            ca_numero = self.request.POST.get('ca_numero')
        elif hasattr(self, 'object') and self.object:
            ca_numero = self.object.ca_numero
            
        if ca_numero:
            num_norm = "".join([c for c in str(ca_numero) if c.isdigit()])
            if num_norm:
                context['ca_obj'] = CertificadoAprovacao.objects.filter(numero=num_norm).first()
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        tamanhos_str = form.cleaned_data.get('tamanhos_str')
        if tamanhos_str is None:
            tamanhos_str = self.request.POST.get('tamanhos_str', '').strip()
            
        _, warnings = sync_product_variants(self.object, tamanhos_str)
        for msg in warnings:
            messages.warning(self.request, msg)
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

        funcao_id = self.request.GET.get('funcao', '').strip()
        if funcao_id:
            queryset = queryset.filter(funcao_id=funcao_id)

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

        from organizations.models import Sector, Function
        context['products'] = Product.objects.filter(ativo=True).order_by('nome')
        context['sectors'] = Sector.objects.filter(unit__in=user_units).order_by('nome')
        context['functions'] = Function.objects.filter(ativo=True).order_by('nome')
        context['status_choices'] = PPEDelivery.SIGN_STATUS
        
        context['filter_data_inicio'] = self.request.GET.get('data_inicio', '').strip()
        context['filter_data_fim'] = self.request.GET.get('data_fim', '').strip()
        context['filter_q'] = self.request.GET.get('q', '').strip()
        context['filter_product'] = self.request.GET.get('product', '').strip()
        context['filter_setor'] = self.request.GET.get('setor', '').strip()
        context['filter_funcao'] = self.request.GET.get('funcao', '').strip()
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


class PPEMatrixBulkCreateView(LoginRequiredMixin, View):
    template_name = "ppe/matrix_bulk_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_tecnico() or request.user.is_admin()):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Apenas Técnicos SST ou Administradores podem gerenciar a matriz de EPI.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        function_form = PPEMatrixFunctionForm(request.GET or None)
        funcao_id = request.GET.get('funcao')
        funcao = None
        formset = None
        if funcao_id:
            funcao = Function.objects.filter(pk=funcao_id).first()
            if funcao:
                formset = PPEMatrixFormSet(instance=funcao, queryset=PPEMatrix.objects.filter(funcao=funcao, ativo=True))
        
        if not formset:
            formset = PPEMatrixFormSet(queryset=PPEMatrix.objects.none())

        return render(request, self.template_name, {
            'title': "Nova Matriz de EPI por Função",
            'is_create': True,
            'function_form': function_form,
            'formset': formset,
            'funcao': funcao,
        })

    def post(self, request, *args, **kwargs):
        function_form = PPEMatrixFunctionForm(request.POST)
        funcao_id = request.POST.get('funcao')
        funcao = get_object_or_404(Function, pk=funcao_id) if funcao_id else None
        
        formset = PPEMatrixFormSet(request.POST, instance=funcao) if funcao else PPEMatrixFormSet(request.POST)

        if function_form.is_valid() and funcao and formset.is_valid():
            with transaction.atomic():
                instances = formset.save(commit=False)
                for obj in instances:
                    obj.funcao = funcao
                    obj.ativo = True
                    if not obj.criado_por_id:
                        obj.criado_por = request.user
                    obj.save()

                for obj in formset.deleted_objects:
                    obj.delete()

                from audit.models import log_audit
                log_audit(
                    request=request,
                    action=f"Criação/Atualização individual da matriz de EPI para a função: {funcao.nome}",
                    model_name="PPEMatrix",
                    object_id=funcao.id,
                    before=None,
                    after={'funcao': funcao.nome}
                )

            messages.success(request, f"Matriz da função {funcao.nome} salva com sucesso!")
            return redirect('function_detail', pk=funcao.id)

        return render(request, self.template_name, {
            'title': "Nova Matriz de EPI por Função",
            'is_create': True,
            'function_form': function_form,
            'formset': formset,
            'funcao': funcao,
        })


class PPEMatrixBulkUpdateView(LoginRequiredMixin, View):
    template_name = "ppe/matrix_bulk_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.is_tecnico() or request.user.is_admin()):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Apenas Técnicos SST ou Administradores podem gerenciar a matriz de EPI.")
        self.funcao = get_object_or_404(Function, pk=self.kwargs.get('function_pk'))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        formset = PPEMatrixFormSet(instance=self.funcao, queryset=PPEMatrix.objects.filter(funcao=self.funcao, ativo=True))
        return render(request, self.template_name, {
            'title': f"Editar Matriz de EPI por Função: {self.funcao.nome}",
            'is_create': False,
            'funcao': self.funcao,
            'formset': formset,
        })

    def post(self, request, *args, **kwargs):
        formset = PPEMatrixFormSet(request.POST, instance=self.funcao)
        if formset.is_valid():
            with transaction.atomic():
                instances = formset.save(commit=False)
                for obj in instances:
                    obj.funcao = self.funcao
                    obj.ativo = True
                    if not obj.criado_por_id:
                        obj.criado_por = request.user
                    obj.save()

                for obj in formset.deleted_objects:
                    obj.delete()

                from audit.models import log_audit
                log_audit(
                    request=request,
                    action=f"Atualização individual da matriz de EPI para a função: {self.funcao.nome}",
                    model_name="PPEMatrix",
                    object_id=self.funcao.id,
                    before=None,
                    after={'funcao': self.funcao.nome}
                )

            messages.success(request, f"Matriz da função {self.funcao.nome} atualizada com sucesso!")
            return redirect('function_detail', pk=self.funcao.id)

        return render(request, self.template_name, {
            'title': f"Editar Matriz de EPI por Função: {self.funcao.nome}",
            'is_create': False,
            'funcao': self.funcao,
            'formset': formset,
        })


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



