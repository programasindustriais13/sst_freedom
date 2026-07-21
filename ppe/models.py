from django.db import models
from django.conf import settings
from organizations.models import Unit, Sector, CostCenter, Function
from employees.models import Employee

class Product(models.Model):
    TIPO_PRODUTO_CHOICES = (
        ('EPI', 'EPI'),
        ('MATERIAL_SEGURANCA', 'Material de Segurança'),
        ('MATERIAL_CONSUMO', 'Material de Consumo'),
        ('FERRAMENTA', 'Ferramenta'),
        ('UNIFORME', 'Uniforme'),
        ('OUTRO', 'Outro'),
    )

    CATEGORIA_CHOICES = (
        ('PROTECAO_CABECA', 'Proteção da Cabeça'),
        ('PROTECAO_AUDITIVA', 'Proteção Auditiva'),
        ('PROTECAO_RESPIRATORIA', 'Proteção Respiratória'),
        ('PROTECAO_OCULAR', 'Proteção Ocular e Facial'),
        ('PROTECAO_TRONCO', 'Proteção do Tronco'),
        ('PROTECAO_MEMBROS_SUP', 'Proteção dos Membros Superiores'),
        ('PROTECAO_MEMBROS_INF', 'Proteção dos Membros Inferiores'),
        ('VESTUARIO', 'Vestuário / Fardamento'),
        ('OUTRO', 'Outro'),
    )

    nome = models.CharField(max_length=255, verbose_name="Nome do Produto")
    tipo_produto = models.CharField(max_length=50, choices=TIPO_PRODUTO_CHOICES, default='EPI', verbose_name="Tipo de Produto")
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES, blank=True, null=True, default='OUTRO', verbose_name="Categoria de Proteção")
    ca_numero = models.CharField(max_length=50, blank=True, null=True, verbose_name="C.A. (Certificado de Aprovação)")
    descricao = models.TextField(blank=True, null=True, verbose_name="Descrição")
    unidade_medida = models.CharField(max_length=20, default="UND", verbose_name="Unidade de Medida")
    fabricante = models.CharField(max_length=255, blank=True, null=True, verbose_name="Fabricante Padrão")
    
    exige_ca = models.BooleanField(default=True, verbose_name="Exige C.A. (Certificado de Aprovação)")
    controlado_individualmente = models.BooleanField(default=True, verbose_name="Controlado Individualmente")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "EPI / Produto"
        verbose_name_plural = "EPIs / Produtos"

    def __str__(self):
        return self.nome


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants', verbose_name="Produto")
    tamanho = models.CharField(max_length=20, default="U", verbose_name="Tamanho/Numeração/Grade")
    sku = models.CharField(max_length=100, blank=True, null=True, verbose_name="SKU / Código Interno")
    codigo_barras = models.CharField(max_length=100, blank=True, null=True, verbose_name="Código de Barras")
    
    estoque_minimo = models.IntegerField(default=0, verbose_name="Estoque Mínimo")
    estoque_maximo = models.IntegerField(blank=True, null=True, verbose_name="Estoque Máximo")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Variante de EPI"
        verbose_name_plural = "Variantes de EPI"
        unique_together = ('product', 'tamanho')

    def __str__(self):
        if self.tamanho == "U":
            return self.product.nome
        return f"{self.product.nome} (Tam: {self.tamanho})"


class CertificadoAprovacao(models.Model):
    STATUS_VERIFICACAO = (
        ('VERIFICADO_BASE_OFICIAL', 'Verificado na Base Oficial CAEPI'),
        ('INFORMADO_MANUALMENTE', 'Informado Manualmente (com justificativa)'),
        ('NAO_ENCONTRADO', 'Não Encontrado na Base MTE'),
        ('DESATUALIZADO', 'Desatualizado'),
    )

    numero = models.CharField(max_length=50, unique=True, verbose_name="Número Normalizado (Dígitos)")
    numero_exibicao = models.CharField(max_length=50, verbose_name="Número de Exibição (ex: CA 12345)")
    
    equipamento = models.CharField(max_length=255, blank=True, null=True, verbose_name="Descrição Oficial do Equipamento")
    fabricante = models.CharField(max_length=255, blank=True, null=True, verbose_name="Fabricante/Importador Oficial")
    cnpj = models.CharField(max_length=20, blank=True, null=True, verbose_name="CNPJ do Fabricante/Importador")
    natureza_protecao = models.TextField(blank=True, null=True, verbose_name="Natureza da Proteção")
    grupo_protecao = models.CharField(max_length=255, blank=True, null=True, verbose_name="Grupo de Proteção")
    processo = models.CharField(max_length=100, blank=True, null=True, verbose_name="Número do Processo")
    natureza = models.CharField(max_length=100, blank=True, null=True, verbose_name="Natureza")
    nome_fantasia = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nome Fantasia")
    cidade = models.CharField(max_length=100, blank=True, null=True, verbose_name="Cidade")
    uf = models.CharField(max_length=10, blank=True, null=True, verbose_name="UF")
    aprovado_para = models.TextField(blank=True, null=True, verbose_name="Aprovado Para")
    situacao = models.CharField(max_length=100, blank=True, null=True, verbose_name="Situação do C.A.")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Restrições ou Observações")
    
    data_emissao = models.DateField(blank=True, null=True, verbose_name="Data de Emissão")
    data_validade = models.DateField(verbose_name="Data de Validade do C.A.")
    
    fonte = models.CharField(max_length=100, default="CAEPI_MTE", verbose_name="Fonte de Dados")
    ultima_sincronizacao = models.DateTimeField(auto_now=True, verbose_name="Última Sincronização")
    
    status_verificacao = models.CharField(max_length=30, choices=STATUS_VERIFICACAO, default='INFORMADO_MANUALMENTE', verbose_name="Status de Verificação")
    justificativa_manual = models.TextField(blank=True, null=True, verbose_name="Justificativa (Se cadastrado manualmente)")
    
    presente_na_fonte = models.BooleanField(default=True, verbose_name="Presente na Fonte Oficial")
    versao_importacao = models.BigIntegerField(default=0, verbose_name="Versão da Última Importação")

    class Meta:
        verbose_name = "Certificado de Aprovação (C.A.)"
        verbose_name_plural = "Certificados de Aprovação (C.A.)"

    def __str__(self):
        return f"{self.numero_exibicao} - {self.fabricante or 'MTE'}"


class CAEPISyncLog(models.Model):
    STATUS_CHOICES = (
        ('INICIADO', 'Iniciado'),
        ('BAIXANDO', 'Baixando'),
        ('PROCESSANDO', 'Processando'),
        ('CONCLUIDO', 'Concluído'),
        ('CONCLUIDO_ALERTAS', 'Concluído com Alertas'),
        ('FALHOU', 'Falhou'),
        ('IGNORADO', 'Ignorado por não haver nova versão'),
    )

    start_time = models.DateTimeField(auto_now_add=True, verbose_name="Data e Hora de Início")
    end_time = models.DateTimeField(blank=True, null=True, verbose_name="Data e Hora de Conclusão")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='INICIADO', verbose_name="Status")
    tipo_execucao = models.CharField(max_length=20, choices=(('MANUAL', 'Manual'), ('AUTOMATICA', 'Automática')), default='MANUAL', verbose_name="Tipo de Execução")
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Usuário Responsável")
    fonte = models.CharField(max_length=255, verbose_name="Fonte Consultada")
    arquivo_nome = models.CharField(max_length=255, blank=True, null=True, verbose_name="Arquivo Processado")
    arquivo_tamanho = models.BigIntegerField(blank=True, null=True, verbose_name="Tamanho do Arquivo (Bytes)")
    arquivo_hash = models.CharField(max_length=64, blank=True, null=True, verbose_name="Hash SHA-256 do Arquivo")
    
    total_lido = models.IntegerField(default=0, verbose_name="Total Lido")
    total_valido = models.IntegerField(default=0, verbose_name="Total Válido")
    total_invalido = models.IntegerField(default=0, verbose_name="Total Inválido")
    total_criados = models.IntegerField(default=0, verbose_name="Total Criados")
    total_atualizados = models.IntegerField(default=0, verbose_name="Total Atualizados")
    total_inalterados = models.IntegerField(default=0, verbose_name="Total Inalterados")
    total_desativados = models.IntegerField(default=0, verbose_name="Total Desativados")
    
    erro_mensagem = models.TextField(blank=True, null=True, verbose_name="Mensagem de Erro")
    traceback = models.TextField(blank=True, null=True, verbose_name="Traceback Técnico")
    duracao_segundos = models.FloatField(blank=True, null=True, verbose_name="Duração (Segundos)")

    class Meta:
        verbose_name = "Log de Sincronização CAEPI"
        verbose_name_plural = "Logs de Sincronização CAEPI"
        ordering = ['-start_time']

    def __str__(self):
        return f"Sincronização {self.id} ({self.start_time.strftime('%d/%m/%Y %H:%M')}) - {self.status}"



class PPEMatrix(models.Model):
    funcao = models.ForeignKey(Function, on_delete=models.CASCADE, related_name='ppe_matrix_entries', verbose_name="Função/Cargo")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="EPI")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, blank=True, null=True, verbose_name="Variante Específica")
    
    obrigatorio = models.BooleanField(default=True, verbose_name="Obrigatório")
    principal = models.BooleanField(default=True, verbose_name="EPI Principal da Função")
    quantidade_padrao = models.IntegerField(default=1, verbose_name="Quantidade Padrão")
    vida_util_dias = models.IntegerField(verbose_name="Vida Útil Padrão (Dias)")
    
    prazo_troca_preventiva = models.IntegerField(blank=True, null=True, verbose_name="Prazo de Troca Preventiva (Dias)")
    orientacoes = models.TextField(blank=True, null=True, verbose_name="Orientações e Instruções de Uso")
    
    ativo = models.BooleanField(default=True, verbose_name="Ativo")
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Criado por")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Matriz de EPI por Função"
        verbose_name_plural = "Matrizes de EPI por Função"
        unique_together = ('funcao', 'product')

    def __str__(self):
        return f"{self.product.nome} para {self.funcao.nome}"


class ExtraordinaryPPE(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='extraordinary_ppes', verbose_name="Colaborador")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="EPI")
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, blank=True, null=True, verbose_name="Variante")
    
    motivo = models.TextField(verbose_name="Motivo do Fornecimento Extraordinário")
    atividade_risco = models.CharField(max_length=255, blank=True, null=True, verbose_name="Atividade Temporária ou Risco Específico")
    
    data_inicio = models.DateField(verbose_name="Data Inicial de Vigência")
    data_fim = models.DateField(blank=True, null=True, verbose_name="Data Final de Vigência")
    
    quantidade = models.IntegerField(default=1, verbose_name="Quantidade")
    vida_util_dias = models.IntegerField(verbose_name="Vida Útil/Prazo de Troca (Dias)")
    
    autorizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Autorizado por")
    observacoes = models.TextField(blank=True, null=True, verbose_name="Observações")
    ativo = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "EPI Extraordinário"
        verbose_name_plural = "EPIs Extraordinários"

    def __str__(self):
        return f"{self.product.nome} (Extraordinário) para {self.employee.nome_completo}"


class PPEDelivery(models.Model):
    NATUREZA_CHOICES = (
        ('INICIAL', 'Entrega Inicial'),
        ('SUBSTITUICAO_VIDA_UTIL', 'Substituição por Vida Útil'),
        ('DANO', 'Substituição por Dano'),
        ('EXTRAVIO', 'Substituição por Extravio/Perda'),
        ('MUDANCA_FUNCAO', 'Mudança de Função/Setor'),
        ('EXTRAORDINARIA', 'Necessidade Extraordinária'),
        ('OUTRA', 'Outra'),
    )

    SIGN_STATUS = (
        ('PENDENTE', 'Pendente de Ciência'),
        ('ASSINADO', 'Ciência Confirmada'),
        ('REJEITADO', 'Rejeitado pelo Colaborador'),
        ('REGISTRADO_OPERADOR', 'Registrado pelo Operador (Sem Assinatura)'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name='ppe_deliveries', verbose_name="Colaborador")
    
    # Snapshot funcional no momento da entrega
    funcao = models.ForeignKey(Function, on_delete=models.PROTECT, verbose_name="Função no Momento da Entrega")
    setor = models.ForeignKey(Sector, on_delete=models.PROTECT, verbose_name="Setor no Momento da Entrega")
    centro_custo = models.ForeignKey(CostCenter, on_delete=models.PROTECT, verbose_name="Centro de Custo no Momento da Entrega")
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, verbose_name="Unidade no Momento da Entrega")
    
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, verbose_name="EPI Entregue (Variante)")
    ca_entregue = models.ForeignKey(CertificadoAprovacao, on_delete=models.PROTECT, blank=True, null=True, verbose_name="C.A. Entregue")
    lot = models.ForeignKey('inventory.Lot', on_delete=models.PROTECT, verbose_name="Lote do Fabricante")
    
    validade_fisica = models.DateField(verbose_name="Validade Física do Lote")
    quantidade = models.IntegerField(verbose_name="Quantidade Entregue")
    custo_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Custo Unitário da Compra")
    
    data_entrega = models.DateField(verbose_name="Data de Fornecimento")
    vida_util_aplicada = models.IntegerField(verbose_name="Vida Útil Aplicada (Dias)")
    data_prevista_troca = models.DateField(verbose_name="Próxima Troca Prevista")
    
    origem_necessidade = models.CharField(max_length=20, choices=(('MATRIZ', 'Matriz da Função'), ('EXTRAORDINARIA', 'EPI Extraordinário')), default='MATRIZ', verbose_name="Origem da Necessidade")
    natureza_entrega = models.CharField(max_length=30, choices=NATUREZA_CHOICES, default='INICIAL', verbose_name="Natureza da Entrega")
    motivo_substituicao = models.TextField(blank=True, null=True, verbose_name="Motivo de Substituição/Observações")
    
    usuario_responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='responsible_deliveries', verbose_name="Técnico/Entregador")
    
    # Assinatura digital simples / ciência do trabalhador
    nome_trabalhador_confirmacao = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nome de Confirmação")
    confirmacao_data_hora = models.DateTimeField(blank=True, null=True, verbose_name="Data/Hora da Ciência")
    recibo_hash = models.CharField(max_length=100, blank=True, null=True, verbose_name="Hash do Recibo")
    status_assinatura = models.CharField(max_length=20, choices=SIGN_STATUS, default='PENDENTE', verbose_name="Status da Ciência")

    class Meta:
        verbose_name = "Entrega de EPI"
        verbose_name_plural = "Entregas de EPIs"
        ordering = ['-data_entrega']

    def __str__(self):
        return f"Entrega {self.product_variant.product.nome} para {self.employee.nome_completo} em {self.data_entrega.strftime('%d/%m/%Y')}"
