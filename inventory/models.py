from django.db import models
from django.conf import settings
from organizations.models import Company, Unit, CostCenter, InventoryLocation

class Supplier(models.Model):
    razao_social = models.CharField(max_length=255, verbose_name="Razão Social")
    cnpj_cpf = models.CharField(max_length=18, unique=True, verbose_name="CNPJ/CPF")
    contato = models.CharField(max_length=100, blank=True, null=True, verbose_name="Nome de Contato")
    telefone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Telefone")
    email = models.EmailField(blank=True, null=True, verbose_name="E-mail")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Fornecedor"
        verbose_name_plural = "Fornecedores"

    def __str__(self):
        return self.razao_social


class FiscalNote(models.Model):
    TIPO_CHOICES = (
        ('NOTA_FISCAL', 'Nota Fiscal'),
        ('RECIBO', 'Recibo'),
        ('SEM_DOCUMENTO', 'Sem documento'),
        ('OUTRO', 'Outro'),
    )

    STATUS_CHOICES = (
        ('RASCUNHO', 'Rascunho'),
        ('CONFERIDA', 'Conferida (Confirmada)'),
        ('CANCELADA', 'Cancelada'),
    )

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='fiscal_notes', verbose_name="Fornecedor")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='fiscal_notes', verbose_name="Unidade Recebedora")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='NOTA_FISCAL', verbose_name="Tipo de Documento")
    numero = models.CharField(max_length=50, blank=True, null=True, verbose_name="Número do Documento")
    serie = models.CharField(max_length=10, blank=True, null=True, verbose_name="Série")
    chave_acesso = models.CharField(max_length=44, blank=True, null=True, verbose_name="Chave de Acesso")
    
    data_emissao = models.DateField(verbose_name="Data de Emissão")
    data_recebimento = models.DateField(verbose_name="Data de Recebimento")
    centro_custo = models.ForeignKey(CostCenter, on_delete=models.PROTECT, related_name='fiscal_notes', verbose_name="Centro de Custo")
    
    frete = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Valor do Frete")
    desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Valor do Desconto")
    valor_total = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Valor Total")
    
    documento_anexo = models.FileField(upload_to='uploads/nfs/', blank=True, null=True, verbose_name="Documento Anexado")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='RASCUNHO', verbose_name="Status")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='fiscal_notes', verbose_name="Registrado por")
    
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Nota Fiscal"
        verbose_name_plural = "Notas Fiscais"
        unique_together = ('supplier', 'numero', 'serie')

    def __str__(self):
        doc_num = self.numero if self.numero else f"S/N (ID {self.id})"
        return f"{self.get_tipo_display()} {doc_num} - {self.supplier.razao_social}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.tipo == 'NOTA_FISCAL':
            errors = {}
            if not self.numero:
                errors['numero'] = "O número é obrigatório para Nota Fiscal."
            if not self.serie:
                errors['serie'] = "A série é obrigatória para Nota Fiscal."
            if errors:
                raise ValidationError(errors)


class Lot(models.Model):
    product_variant = models.ForeignKey('ppe.ProductVariant', on_delete=models.PROTECT, related_name='lots', verbose_name="Variante de EPI")
    fiscal_note = models.ForeignKey(FiscalNote, on_delete=models.PROTECT, blank=True, null=True, related_name='lots', verbose_name="Nota Fiscal")
    ca = models.ForeignKey('ppe.CertificadoAprovacao', on_delete=models.PROTECT, blank=True, null=True, verbose_name="C.A. (Certificado de Aprovação)")
    identificador = models.CharField(max_length=100, verbose_name="Lote do Fabricante")
    
    data_fabricacao = models.DateField(blank=True, null=True, verbose_name="Data de Fabricação")
    data_validade = models.DateField(verbose_name="Validade Física do Produto")
    
    quantidade_inicial = models.IntegerField(verbose_name="Quantidade Inicial")
    custo_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Custo Unitário")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    @property
    def subtotal(self):
        return self.quantidade_inicial * self.custo_unitario

    class Meta:
        verbose_name = "Lote"
        verbose_name_plural = "Lotes"
        unique_together = ('product_variant', 'identificador')

    def __str__(self):
        return f"Lote {self.identificador} ({self.product_variant.product.nome})"


class StockMovement(models.Model):
    TYPE_CHOICES = (
        ('ENTRADA_COMPRA', 'Entrada por Nota Fiscal'),
        ('TRANSFERENCIA_SAIDA', 'Transferência (Saída)'),
        ('TRANSFERENCIA_ENTRADA', 'Transferência (Entrada)'),
        ('ENTREGA_COLABORADOR', 'Entrega a Colaborador'),
        ('DEVOLUCAO_COLABORADOR', 'Devolução de Colaborador'),
        ('AJUSTE_POSITIVO', 'Ajuste de Entrada Manual'),
        ('AJUSTE_NEGATIVO', 'Ajuste de Saída Manual'),
        ('BAIXA_DANO', 'Baixa por Dano'),
        ('BAIXA_PERDA', 'Baixa por Perda'),
        ('BAIXA_VENCIMENTO', 'Baixa por Vencimento'),
        ('ESTORNO', 'Estorno Controlado'),
    )

    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='stock_movements', verbose_name="Unidade")
    location = models.ForeignKey(InventoryLocation, on_delete=models.PROTECT, related_name='stock_movements', verbose_name="Local de Estoque")
    product_variant = models.ForeignKey('ppe.ProductVariant', on_delete=models.PROTECT, related_name='stock_movements', verbose_name="Variante de EPI")
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT, related_name='stock_movements', verbose_name="Lote")
    
    # Entradas são quantidades positivas, saídas são quantidades negativas
    quantity = models.IntegerField(verbose_name="Quantidade")
    cost_unit = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Custo Unitário Histórico")
    
    movement_type = models.CharField(max_length=30, choices=TYPE_CHOICES, verbose_name="Tipo de Movimento")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='stock_movements', verbose_name="Usuário Responsável")
    notes = models.TextField(blank=True, null=True, verbose_name="Observações/Justificativa")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data/Hora do Registro")
    idempotency_key = models.CharField(max_length=100, blank=True, null=True, verbose_name="Chave de Idempotência")
    correlation_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID de Correlação")

    class Meta:
        verbose_name = "Movimentação de Estoque"
        verbose_name_plural = "Movimentações de Estoque"
        ordering = ['-created_at']

    def __str__(self):
        sign = "+" if self.quantity > 0 else ""
        return f"{self.get_movement_type_display()}: {sign}{self.quantity} {self.product_variant.product.nome} em {self.location.nome}"


class StockTransfer(models.Model):
    STATUS_CHOICES = (
        ('RASCUNHO', 'Rascunho'),
        ('EXPEDIDA', 'Expedida (Em Trânsito)'),
        ('RECEBIDA', 'Recebida'),
        ('RECEBIDA_COM_DIVERGENCIA', 'Recebida com Divergência'),
        ('CANCELADA', 'Cancelada'),
    )

    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='transfers', verbose_name="Unidade")
    source_location = models.ForeignKey(InventoryLocation, on_delete=models.PROTECT, related_name='source_transfers', verbose_name="Local de Origem")
    dest_location = models.ForeignKey(InventoryLocation, on_delete=models.PROTECT, related_name='dest_transfers', verbose_name="Local de Destino")
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='RASCUNHO', verbose_name="Status")
    
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_transfers', verbose_name="Expedido por")
    recebido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, blank=True, null=True, related_name='received_transfers', verbose_name="Recebido por")
    
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Data de Expedição")
    recebido_em = models.DateTimeField(blank=True, null=True, verbose_name="Data de Recebimento")
    
    justificativa_divergencia = models.TextField(blank=True, null=True, verbose_name="Justificativa de Divergência/Observações")

    class Meta:
        verbose_name = "Transferência de Estoque"
        verbose_name_plural = "Transferências de Estoque"

    def __str__(self):
        return f"TR {self.id} de {self.source_location.nome} para {self.dest_location.nome} - {self.get_status_display()}"


class StockTransferItem(models.Model):
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name='items', verbose_name="Transferência")
    product_variant = models.ForeignKey('ppe.ProductVariant', on_delete=models.PROTECT, verbose_name="Variante de EPI")
    lot = models.ForeignKey(Lot, on_delete=models.PROTECT, verbose_name="Lote")
    
    quantity_sent = models.IntegerField(verbose_name="Quantidade Enviada")
    quantity_received = models.IntegerField(blank=True, null=True, verbose_name="Quantidade Recebida")

    class Meta:
        verbose_name = "Item da Transferência"
        verbose_name_plural = "Itens da Transferência"
        unique_together = ('transfer', 'product_variant', 'lot')

    def __str__(self):
        return f"{self.product_variant.product.nome} (Lote {self.lot.identificador}) - Enviado: {self.quantity_sent}"


class LocationStockMinimo(models.Model):
    product_variant = models.ForeignKey('ppe.ProductVariant', on_delete=models.CASCADE, related_name='location_minimums', verbose_name="Variante de EPI")
    location = models.ForeignKey(InventoryLocation, on_delete=models.CASCADE, related_name='variant_minimums', verbose_name="Local de Estoque")
    estoque_minimo = models.IntegerField(default=0, verbose_name="Estoque Mínimo")
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Estoque Mínimo por Local"
        verbose_name_plural = "Estoques Mínimos por Local"
        unique_together = ('product_variant', 'location')

    def __str__(self):
        return f"Mínimo: {self.estoque_minimo} para {self.product_variant} em {self.location.nome}"

