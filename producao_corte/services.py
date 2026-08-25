from django.utils import timezone

from movimentacoes.models import Movimentacao
from estoque.models import Estoque
from core.models import Local


def disponibilidade_produto_final(produto, quantidade):
    """
    Verifica quantas unidades de `produto` (produto_final) já estão prontas
    como ProdutoCortado avulso (peça física com QR), sem precisar cortar
    de novo.

    Combina duas fontes, nessa ordem:
    1. Peças cortadas diretamente como esse produto — vale tanto pra
       produto simples quanto pra Kit cortado como peça única.
    2. Se sobrar quantidade e o produto for Kit (`produto.is_kit`): peças
       avulsas dos componentes, decompostas via FichaTecnica.

    Retorna (ok, n_diretas, componentes):
    - ok: True se a quantidade pedida está totalmente coberta
    - n_diretas: quantas peças diretas (já prontas como o próprio produto) usar
    - componentes: disponibilidade de cada material do Kit (vazia se não
      precisou decompor / não é Kit)
    """
    from producao_corte.models import ProdutoCortado

    diretas_qs = ProdutoCortado.objects.filter(
        produto=produto, status='montado', pedido=None,
    ).order_by('id')

    n_diretas = min(diretas_qs.count(), quantidade)
    restante  = quantidade - n_diretas

    if restante <= 0:
        return True, n_diretas, []

    if not produto.is_kit:
        return False, n_diretas, []

    ficha = produto.ficha_tecnica
    componentes = []
    ok = True
    for item in ficha.itens.select_related('material').all():
        necessario = item.quantidade * restante
        disponivel = ProdutoCortado.objects.filter(
            produto=item.material, status='montado', pedido=None,
        ).count()
        item_ok = disponivel >= necessario
        if not item_ok:
            ok = False
        componentes.append({
            'nome':       item.material.nome,
            'necessario': necessario,
            'disponivel': disponivel,
            'ok':         item_ok,
        })

    return ok, n_diretas, componentes


def _local_com_saldo(produto, local_preferido, local_fallback, quantidade):
    """
    Usa o local preferido se ele tiver saldo suficiente do produto;
    caso contrário, cai para o local de fallback (fábrica). Evita tentar
    debitar de um local que nunca recebeu o material.
    """
    if local_preferido:
        saldo = Estoque.objects.filter(produto=produto, local=local_preferido).first()
        if saldo and saldo.quantidade >= quantidade:
            return local_preferido
    return local_fallback


def debitar_componentes_ficha(peca, pedido, usuario):
    """
    Ao separar uma peça (ProdutoCortado) — seja via escaneamento manual do
    QR (montagem/views/confirmar_montagem.py), seja via resolução
    automática de pedido com peças avulsas (consumir_produto_final,
    abaixo) — debita do Estoque agregado:

    1. A própria peça pronta (produto final), fechando o ciclo aberto na
       montagem (onde ela deu entrada). PULADO se a peça for um Kit — ela
       não tem estoque próprio (ver Produto.is_kit).
    2. Os materiais/peças da ficha técnica, se houver (receita normal de
       produção — não confundir com a decomposição de Kit em peças
       avulsas, que já aconteceu antes desta função ser chamada).

    Existe pra manter o Estoque agregado sincronizado com o ProdutoCortado
    individual, que é quem efetivamente controla a existência física da
    peça — as duas rotas de separação (manual e automática) precisam
    gerar exatamente os mesmos efeitos colaterais, ou o agregado desvia
    do real.
    """
    fabrica_padrao  = Local.objects.filter(tipo='fabrica').first()
    local_preferido = pedido.local_saida if pedido else None

    ficha  = getattr(peca.produto, 'ficha_tecnica', None)
    eh_kit = peca.produto.is_kit

    # ── 1. Saída da peça pronta (pulado se for Kit) ──
    if not eh_kit:
        local_peca = _local_com_saldo(peca.produto, local_preferido, fabrica_padrao, 1)
        Movimentacao.objects.create(
            produto    = peca.produto,
            local      = local_peca,
            tipo       = 'saida',
            motivo     = 'venda',
            quantidade = 1,
            observacao = (
                f'Separação — Pedido {pedido.numero} ({peca.produto.nome})'
                if pedido else f'Separação — {peca.produto.nome}'
            ),
            usuario    = usuario,
        )

    # ── 2. Materiais/peças da ficha técnica ──
    if ficha:
        for componente in ficha.itens.select_related('material').all():
            local_usar = _local_com_saldo(
                componente.material, local_preferido, fabrica_padrao, componente.quantidade
            )
            Movimentacao.objects.create(
                produto    = componente.material,
                local      = local_usar,
                tipo       = 'saida',
                motivo     = 'venda',
                quantidade = componente.quantidade,
                observacao = (
                    f'Separação — Pedido {pedido.numero} ({peca.produto.nome})'
                    if pedido else f'Separação — {peca.produto.nome}'
                ),
                usuario    = usuario,
            )


def consumir_produto_final(produto, quantidade, pedido, usuario):
    """
    Vincula ao `pedido` peças ProdutoCortado reais que resolvem `quantidade`
    unidades de `produto` — direta e/ou via componentes de Kit — marcando
    cada uma como 'separado' e debitando o Estoque agregado correspondente
    (via debitar_componentes_ficha), exatamente como a separação manual via
    QR já faz.

    Pressupõe que disponibilidade_produto_final(produto, quantidade) já
    retornou ok=True para esse produto/quantidade; não revalida.

    Retorna a lista de ProdutoCortado vinculados.
    """
    from producao_corte.models import ProdutoCortado

    agora      = timezone.now()
    vinculadas = []

    _, n_diretas, _ = disponibilidade_produto_final(produto, quantidade)

    diretas = ProdutoCortado.objects.filter(
        produto=produto, status='montado', pedido=None,
    ).order_by('id')[:n_diretas]
    for peca in diretas:
        debitar_componentes_ficha(peca, pedido, usuario)
        peca.pedido       = pedido
        peca.status       = 'separado'
        peca.separada_por = usuario
        peca.separada_em  = agora
        peca.save(update_fields=['pedido', 'status', 'separada_por', 'separada_em'])
        vinculadas.append(peca)

    restante = quantidade - n_diretas
    if restante > 0 and produto.is_kit:
        ficha = produto.ficha_tecnica
        for comp in ficha.itens.select_related('material').all():
            qtd_necessaria = int(comp.quantidade * restante)
            pecas_comp = ProdutoCortado.objects.filter(
                produto=comp.material, status='montado', pedido=None,
            ).order_by('id')[:qtd_necessaria]
            for peca in pecas_comp:
                debitar_componentes_ficha(peca, pedido, usuario)
                peca.pedido       = pedido
                peca.status       = 'separado'
                peca.separada_por = usuario
                peca.separada_em  = agora
                peca.save(update_fields=['pedido', 'status', 'separada_por', 'separada_em'])
                vinculadas.append(peca)

    return vinculadas

def pedidos_precisando_peca(peca):
    """
    Encontra pedidos (picking/aguard_producao) que precisam desta peça
    avulsa — direto (item do pedido = produto da peça) OU como componente
    de um Kit ainda não totalmente resolvido (ex: peça = Cubo P avulso,
    pedido pede "Trio de Cubos" e ainda falta vincular Cubo P suficiente).

    Pra Kit, só inclui o pedido se ele ainda PRECISA de mais unidades desse
    componente especificamente — evita reoferecer um pedido cujo Cubo P já
    foi todo resolvido, mas que ainda espera Cubo M/G.
    """
    from vendas.models import Pedido
    from producao_corte.models import ProdutoCortado

    diretos = Pedido.objects.filter(
        status__in=['picking', 'aguard_producao'],
        itens__produto=peca.produto,
    )

    candidatos_kit = Pedido.objects.filter(
        status__in=['picking', 'aguard_producao'],
        itens__produto__ficha_tecnica__itens__material=peca.produto,
    ).distinct().prefetch_related('itens__produto')

    kits_ids = []
    for pedido in candidatos_kit:
        for item in pedido.itens.select_related('produto').all():
            if not item.produto.is_kit:
                continue
            componente = item.produto.ficha_tecnica.itens.filter(material=peca.produto).first()
            if not componente:
                continue
            necessario = int(componente.quantidade * item.quantidade)
            ja_vinculadas = ProdutoCortado.objects.filter(
                pedido=pedido, produto=peca.produto,
            ).exclude(status='desmembrado').count()
            if ja_vinculadas < necessario:
                kits_ids.append(pedido.pk)
                break

    return (diretos | Pedido.objects.filter(pk__in=kits_ids)).distinct().select_related('cliente')

def confirmar_montagem_peca(peca, usuario):
    """
    Confirma a montagem de uma peça (ProdutoCortado): aguardando -> montado.

    Dá entrada no Estoque agregado — peça pronta (pulado se Kit, que não
    tem estoque próprio) + componentes da ficha técnica, se houver. Espelho
    de debitar_componentes_ficha, mas na direção de entrada em vez de saída.

    Se a peça já pertence a um pedido e essa foi a última peça faltando
    montar, avança o pedido para PICKING.

    Usada tanto pelo escaneamento individual (montagem/views/confirmar_montagem.py)
    quanto pela confirmação em lote (producao_corte/views/montagem_lote.py).
    """
    from producao_corte.models import ProdutoCortado

    fabrica = Local.objects.filter(tipo='fabrica').first()
    eh_kit  = peca.produto.is_kit

    ficha = getattr(peca.produto, 'ficha_tecnica', None)
    if ficha:
        for componente in ficha.itens.select_related('material').all():
            Movimentacao.objects.create(
                produto    = componente.material,
                local      = fabrica,
                tipo       = 'entrada',
                motivo     = 'producao',
                quantidade = componente.quantidade,
                observacao = f'Montagem — {peca.produto.nome}',
                usuario    = usuario,
            )

    # ── Dá entrada na peça pronta (pulado se for Kit) ──
    if not eh_kit:
        Movimentacao.objects.create(
            produto    = peca.produto,
            local      = fabrica,
            tipo       = 'entrada',
            motivo     = 'producao',
            quantidade = 1,
            observacao = f'Montagem — {peca.produto.nome} (peça pronta)',
            usuario    = usuario,
        )

    peca.status      = 'montado'
    peca.montada_por = usuario
    peca.montada_em  = timezone.now()
    peca.save(update_fields=['status', 'montada_por', 'montada_em'])

    if peca.pedido:
        pedido   = peca.pedido
        total    = ProdutoCortado.objects.filter(pedido=pedido).count()
        montadas = ProdutoCortado.objects.filter(pedido=pedido, status='montado').count()
        if total > 0 and montadas >= total:
            pedido.status = pedido.Status.PICKING
            pedido.save(update_fields=['status', 'atualizado_em'])

    return peca