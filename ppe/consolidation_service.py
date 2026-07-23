import json
import logging
from django.db import transaction, models
from django.core.exceptions import ValidationError
from ppe.models import Product, ProductVariant, PPEMatrix, PPEDelivery, ExtraordinaryPPE
from inventory.models import Lot, StockMovement, StockTransferItem, LocationStockMinimo
from inventory.services import get_stock_balance
from organizations.models import InventoryLocation
from audit.models import log_action

logger = logging.getLogger('ppe.consolidation')

class EPIConsolidationService:
    @staticmethod
    def normalize_ca(ca_str):
        if not ca_str:
            return ""
        return "".join([c for c in str(ca_str) if c.isdigit()])

    @classmethod
    def get_duplicate_groups(cls, ca_filter=None):
        """
        Localiza todos os grupos de EPIs cadastrados separadamente com o mesmo CA normalizado.
        """
        all_epis = Product.objects.filter(tipo_produto='EPI', ca_numero__isnull=False).exclude(ca_numero='')
        
        ca_groups = {}
        for epi in all_epis:
            norm_ca = cls.normalize_ca(epi.ca_numero)
            if not norm_ca:
                continue
            if ca_filter:
                norm_filter = cls.normalize_ca(ca_filter)
                if norm_ca != norm_filter:
                    continue
            if norm_ca not in ca_groups:
                ca_groups[norm_ca] = []
            ca_groups[norm_ca].append(epi)

        # Filtra apenas grupos com mais de 1 EPI
        duplicate_groups = {ca: epis for ca, epis in ca_groups.items() if len(epis) > 1}
        return duplicate_groups

    @classmethod
    def generate_report(cls, ca_filter=None):
        """
        Gera relatório detalhado de auditoria de duplicidades por CA sem alterar o banco de dados.
        """
        groups = cls.get_duplicate_groups(ca_filter)
        report_data = []

        locations = list(InventoryLocation.objects.filter(ativo=True))

        for ca_norm, epis in groups.items():
            group_info = {
                'ca_normalizado': ca_norm,
                'ca_original': epis[0].ca_numero,
                'total_epis': len(epis),
                'epis': [],
                'conflitos': [],
                'candidato_canonico_sugerido': None
            }

            fabricantes = set()
            categorias = set()
            skus_vistos = set()
            tamanhos_vistos = set()
            total_stock_grupo = 0

            candidate = None
            max_relations = -1

            for epi in epis:
                fabricantes.add(epi.fabricante or 'Não informado')
                categorias.add(epi.categoria or 'OUTRO')

                variants = list(epi.variants.all())
                variants_info = []
                epi_stock_total = 0
                epi_stock_by_loc = {}

                for v in variants:
                    if v.tamanho in tamanhos_vistos:
                        group_info['conflitos'].append(f"Tamanho duplicado no grupo: '{v.tamanho}'")
                    tamanhos_vistos.add(v.tamanho)

                    if v.sku:
                        if v.sku in skus_vistos:
                            group_info['conflitos'].append(f"SKU repetido no grupo: '{v.sku}'")
                        skus_vistos.add(v.sku)

                    v_bal_total = 0
                    for loc in locations:
                        b = get_stock_balance(loc, v)
                        if b > 0:
                            v_bal_total += b
                            epi_stock_by_loc[loc.nome] = epi_stock_by_loc.get(loc.nome, 0) + b

                    variants_info.append({
                        'id': v.id,
                        'tamanho': v.tamanho,
                        'sku': v.sku,
                        'estoque_minimo': v.estoque_minimo,
                        'ativo': v.ativo,
                        'saldo_estoque': v_bal_total
                    })
                    epi_stock_total += v_bal_total

                total_stock_grupo += epi_stock_total

                # Contagem de relacionamentos
                deliveries_count = PPEDelivery.objects.filter(product_variant__product=epi).count()
                movements_count = StockMovement.objects.filter(product_variant__product=epi).count()
                lots_count = Lot.objects.filter(product_variant__product=epi).count()
                matrices_count = PPEMatrix.objects.filter(product=epi).count()
                total_rel = deliveries_count + movements_count + lots_count + matrices_count

                if total_rel > max_relations:
                    max_relations = total_rel
                    candidate = epi

                group_info['epis'].append({
                    'id': epi.id,
                    'nome': epi.nome,
                    'fabricante': epi.fabricante,
                    'categoria': epi.categoria,
                    'ativo': epi.ativo,
                    'variantes': variants_info,
                    'saldo_estoque_total': epi_stock_total,
                    'saldo_por_local': epi_stock_by_loc,
                    'total_relacionamentos': total_rel,
                    'entregas': deliveries_count,
                    'movimentacoes': movements_count,
                    'lotes': lots_count,
                    'matrizes': matrices_count
                })

            if len(fabricantes) > 1:
                group_info['conflitos'].append(f"Fabricantes divergentes no grupo: {', '.join(fabricantes)}")
            if len(categorias) > 1:
                group_info['conflitos'].append(f"Categorias divergentes no grupo: {', '.join(categorias)}")

            group_info['saldo_total_grupo'] = total_stock_grupo
            if candidate:
                group_info['candidato_canonico_sugerido'] = {
                    'id': candidate.id,
                    'nome': candidate.nome,
                    'motivo': f"Maior número de relacionamentos/completude ({max_relations} vínculos)"
                }

            report_data.append(group_info)

        return report_data

    @classmethod
    @transaction.atomic
    def consolidate_group(cls, ca_number, canonical_id, size_map=None, dry_run=True, user=None):
        """
        Executa a consolidação controlada de EPIs duplicados pelo CA para um EPI canônico.
        Retorna dicionário com o resumo completo e grava auditoria.
        """
        if not ca_number or not canonical_id:
            raise ValidationError("Número do CA e ID do EPI Canônico são obrigatórios para a consolidação.")

        size_map = size_map or {}
        ca_norm = cls.normalize_ca(ca_number)

        # 1. Carrega e valida EPI Canônico
        canonical_product = Product.objects.select_for_update().filter(id=canonical_id).first()
        if not canonical_product:
            raise ValidationError(f"EPI Canônico com ID {canonical_id} não foi localizado.")

        if cls.normalize_ca(canonical_product.ca_numero) != ca_norm:
            raise ValidationError(f"O EPI Canônico ID {canonical_id} possui CA '{canonical_product.ca_numero}' que diverge do CA informado '{ca_number}'.")

        # 2. Carrega todos os EPIs do grupo
        group_products = list(Product.objects.select_for_update().filter(tipo_produto='EPI', ca_numero__icontains=ca_norm))
        group_products = [p for p in group_products if cls.normalize_ca(p.ca_numero) == ca_norm]

        if len(group_products) <= 1:
            raise ValidationError(f"Não há duplicidades para consolidar no CA {ca_norm}.")

        duplicate_products = [p for p in group_products if p.id != canonical_id]

        # 3. Mapeia tamanhos para cada produto duplicado
        target_size_mapping = {}
        for dup in duplicate_products:
            if dup.id in size_map:
                target_size_mapping[dup.id] = size_map[dup.id]
            else:
                # Tenta obter das variantes existentes no próprio registro duplicado
                active_vars = list(dup.variants.all())
                if len(active_vars) == 1 and active_vars[0].tamanho != 'U':
                    target_size_mapping[dup.id] = active_vars[0].tamanho
                else:
                    # Tenta extrair sugestão pelo nome
                    nome_parts = dup.nome.strip().split()
                    last_word = nome_parts[-1].upper() if nome_parts else ''
                    if last_word in ['P', 'M', 'G', 'GG', 'XG', 'XXG', '35', '36', '37', '38', '39', '40', '41', '42', '43', '44']:
                        target_size_mapping[dup.id] = last_word
                    else:
                        raise ValidationError(
                            f"Mapeamento de tamanho ambíguo ou ausente para o EPI duplicado ID {dup.id} ('{dup.nome}'). "
                            f"Forneça o argumento --size-map \"{dup.id}=<TAMANHO>\"."
                        )

        # 4. Captura totais e saldos ANTES da consolidação (Invariantes)
        locations = list(InventoryLocation.objects.filter(ativo=True))
        all_group_variants_before = ProductVariant.objects.filter(product__in=group_products)
        
        total_stock_before = 0
        stock_by_loc_before = {}
        for loc in locations:
            loc_sum = 0
            for v in all_group_variants_before:
                b = get_stock_balance(loc, v)
                loc_sum += b
            stock_by_loc_before[loc.id] = loc_sum
            total_stock_before += loc_sum

        total_deliveries_before = PPEDelivery.objects.filter(product_variant__in=all_group_variants_before).count()
        total_movements_before = StockMovement.objects.filter(product_variant__in=all_group_variants_before).count()
        total_lots_before = Lot.objects.filter(product_variant__in=all_group_variants_before).count()

        # 5. Processa variantes no EPI Canônico
        variant_redirection_map = {} # dup_variant_id -> canonical_variant_obj
        variants_created_count = 0
        variants_reused_count = 0

        for dup in duplicate_products:
            target_size = target_size_mapping[dup.id]
            
            # Localiza ou cria a variante equivalente no Canônico
            canon_var = canonical_product.variants.filter(tamanho__iexact=target_size).first()
            if not canon_var:
                # Procura se havia com SKU/outro atributo
                dup_var = dup.variants.first()
                sku_val = dup_var.sku if dup_var else None
                min_val = dup_var.estoque_minimo if dup_var else 0
                canon_var = ProductVariant.objects.create(
                    product=canonical_product,
                    tamanho=target_size,
                    sku=sku_val,
                    estoque_minimo=min_val,
                    ativo=True
                )
                variants_created_count += 1
            else:
                if not canon_var.ativo:
                    canon_var.ativo = True
                    canon_var.save(update_fields=['ativo'])
                variants_reused_count += 1

            for dup_v in dup.variants.all():
                variant_redirection_map[dup_v.id] = canon_var

        # 6. Transfere Relacionamentos
        relationships_updated = {
            'PPEDelivery': 0,
            'StockMovement': 0,
            'Lot': 0,
            'StockTransferItem': 0,
            'LocationStockMinimo': 0,
            'PPEMatrix': 0,
            'ExtraordinaryPPE': 0
        }

        # 6.1 Lotes (Trata restrição única 'product_variant', 'identificador')
        dup_lots = Lot.objects.filter(product_variant_id__in=variant_redirection_map.keys())
        for lot in dup_lots:
            target_var = variant_redirection_map[lot.product_variant_id]
            existing_canon_lot = Lot.objects.filter(product_variant=target_var, identificador=lot.identificador).first()
            if existing_canon_lot and existing_canon_lot.id != lot.id:
                # Transfere movimentações e entregas do lote duplicado para o lote canônico existente
                StockMovement.objects.filter(lot=lot).update(lot=existing_canon_lot)
                PPEDelivery.objects.filter(lot=lot).update(lot=existing_canon_lot)
                StockTransferItem.objects.filter(lot=lot).update(lot=existing_canon_lot)
                lot.delete()
            else:
                lot.product_variant = target_var
                lot.save(update_fields=['product_variant'])
            relationships_updated['Lot'] += 1

        # 6.2 Movimentações de Estoque
        for dup_v_id, canon_v in variant_redirection_map.items():
            count = StockMovement.objects.filter(product_variant_id=dup_v_id).update(product_variant=canon_v)
            relationships_updated['StockMovement'] += count

        # 6.3 Entregas de EPI
        for dup_v_id, canon_v in variant_redirection_map.items():
            count = PPEDelivery.objects.filter(product_variant_id=dup_v_id).update(product_variant=canon_v)
            relationships_updated['PPEDelivery'] += count

        # 6.4 Transferências
        for dup_v_id, canon_v in variant_redirection_map.items():
            count = StockTransferItem.objects.filter(product_variant_id=dup_v_id).update(product_variant=canon_v)
            relationships_updated['StockTransferItem'] += count

        # 6.5 Estoques Mínimos por Local
        for dup_v_id, canon_v in variant_redirection_map.items():
            dup_mins = LocationStockMinimo.objects.filter(product_variant_id=dup_v_id)
            for m in dup_mins:
                existing_m = LocationStockMinimo.objects.filter(product_variant=canon_v, location=m.location).first()
                if existing_m:
                    if m.estoque_minimo > existing_m.estoque_minimo:
                        existing_m.estoque_minimo = m.estoque_minimo
                        existing_m.save(update_fields=['estoque_minimo'])
                    m.delete()
                else:
                    m.product_variant = canon_v
                    m.save(update_fields=['product_variant'])
                relationships_updated['LocationStockMinimo'] += 1

        # 6.6 Matriz de EPI por Função
        for dup in duplicate_products:
            dup_matrices = PPEMatrix.objects.filter(product=dup)
            for mat in dup_matrices:
                canon_target_var = variant_redirection_map.get(mat.variant_id)
                existing_mat = PPEMatrix.objects.filter(funcao=mat.funcao, product=canonical_product).first()
                if existing_mat:
                    if canon_target_var and not existing_mat.variant:
                        existing_mat.variant = canon_target_var
                        existing_mat.save(update_fields=['variant'])
                    mat.delete()
                else:
                    mat.product = canonical_product
                    if canon_target_var:
                        mat.variant = canon_target_var
                    mat.save(update_fields=['product', 'variant'])
                relationships_updated['PPEMatrix'] += 1

        # 6.7 EPI Extraordinário
        for dup in duplicate_products:
            dup_exts = ExtraordinaryPPE.objects.filter(product=dup)
            for ext in dup_exts:
                canon_target_var = variant_redirection_map.get(ext.variant_id)
                ext.product = canonical_product
                if canon_target_var:
                    ext.variant = canon_target_var
                ext.save(update_fields=['product', 'variant'])
                relationships_updated['ExtraordinaryPPE'] += 1

        # 7. Inativa os EPIs duplicados e suas variantes (sem exclusão física)
        for dup in duplicate_products:
            dup.ativo = False
            dup.descricao = ((dup.descricao or '') + f"\n[INCORPORADO AO EPI CANÔNICO ID {canonical_id} - CA {ca_norm}]").strip()
            dup.save(update_fields=['ativo', 'descricao'])
            dup.variants.update(ativo=False)

        # 8. Valida Invariantes de Estoque DEPOIS da consolidação
        all_canonical_vars_after = canonical_product.variants.all()
        total_stock_after = 0
        stock_by_loc_after = {}
        for loc in locations:
            loc_sum = 0
            for v in all_canonical_vars_after:
                b = get_stock_balance(loc, v)
                loc_sum += b
            stock_by_loc_after[loc.id] = loc_sum
            total_stock_after += loc_sum

        total_deliveries_after = PPEDelivery.objects.filter(product_variant__in=all_canonical_vars_after).count()
        total_movements_after = StockMovement.objects.filter(product_variant__in=all_canonical_vars_after).count()

        if total_stock_before != total_stock_after:
            raise ValidationError(
                f"INVARIANTE VIOLADO: O saldo total do grupo divergiu após a consolidação. "
                f"Antes: {total_stock_before}, Depois: {total_stock_after}. Operação cancelada com rollback."
            )

        if stock_by_loc_before != stock_by_loc_after:
            raise ValidationError(
                f"INVARIANTE VIOLADO: O saldo por local de estoque divergiu após a consolidação. Operação cancelada com rollback."
            )

        if total_deliveries_before != total_deliveries_after:
            raise ValidationError(
                f"INVARIANTE VIOLADO: O total de entregas vinculadas divergiu ({total_deliveries_before} -> {total_deliveries_after}). Rollback disparado."
            )

        summary = {
            'ca_normalizado': ca_norm,
            'canonical_id': canonical_id,
            'canonical_nome': canonical_product.nome,
            'incorporated_ids': [dup.id for dup in duplicate_products],
            'variantes_criadas': variants_created_count,
            'variantes_reutilizadas': variants_reused_count,
            'relacionamentos_atualizados': relationships_updated,
            'estoque_total_antes': total_stock_before,
            'estoque_total_depois': total_stock_after,
            'dry_run': dry_run
        }

        # 9. Grava Registro de Auditoria
        log_action(
            user=user,
            action=f"{'[DRY-RUN] ' if dry_run else ''}Consolidação de EPIs duplicados pelo CA {ca_norm} no EPI Canônico ID {canonical_id}",
            model_name="Product",
            object_id=canonical_id,
            before={'epis_duplicados_ids': [dup.id for dup in duplicate_products], 'estoque_total': total_stock_before},
            after=summary
        )

        # 10. Rollback automático se for dry-run
        if dry_run:
            transaction.set_rollback(True)

        return summary
