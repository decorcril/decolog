from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from producao_corte.models import ProdutoCortado
from movimentacoes.models import Movimentacao
from estoque.models import Estoque
from core.models import Local


def _ficha_e_kit(ficha):
    """
    True se a ficha técnica é composta por outros produtos finais (ex: um
    'trio' feito de peças já rastreadas individualmente), e não por matéria-
    prima/insumo. Nesse caso, a peça-container não tem estoque próprio — só
    os componentes movimentam.
    """
    return any(
        componente.material.categoria == 'produto_final'
        for componente in ficha.itens.select_related('material').all()
    )


def _local_com_saldo(produto, local_preferido, local_fallback, quantidade):
    """
    Usa o local preferido se ele tiver saldo suficiente do produto;
    caso contrário, cai para o local de fallback (fábrica).
    Evita tentar debitar de um local que nunca recebeu o material.
    """
    if local_preferido:
        saldo = Estoque.objects.filter(produto=produto, local=local_preferido).first()
        if saldo and saldo.quantidade >= quantidade:
            return local_preferido
    return local_fallback


def _debitar_componentes_ficha(peca, pedido, usuario):
    """
    Ao separar a peça, debita:
    1. A própria peça pronta (produto final) do estoque de peças montadas —
       fecha o ciclo aberto na montagem, onde ela deu entrada no Estoque.
       PULADO quando a peça é um kit de outras peças finais (ex: "Trio de
       cubos" feito de P, M, G) — nesse caso ela não tem estoque próprio.
    2. Os materiais/peças da ficha técnica (comportamento já existente,
       mantido como estava).
    """
    fabrica_padrao  = Local.objects.filter(tipo='fabrica').first()
    local_preferido = pedido.local_saida if pedido else None

    try:
        ficha = peca.produto.ficha_tecnica
        eh_kit = _ficha_e_kit(ficha)
    except peca.produto.__class__.ficha_tecnica.RelatedObjectDoesNotExist:
        ficha  = None
        eh_kit = False

    # ── 1. Saída da peça pronta (pulado se for kit) ──
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


@login_required
def confirmar_montagem(request, token):
    peca = get_object_or_404(ProdutoCortado, token=token)

    # ── Peça já separada ──
    if peca.status == 'separado':
        return render(request, 'vendas/peca_ja_separada.html', {'peca': peca})

    # ── Peça montada — separação ──
    if peca.status == 'montado':

        # Peça avulsa — vincular a um pedido
        if not peca.pedido:
            from vendas.models import Pedido

            pedidos_precisando = Pedido.objects.filter(
                status__in=['picking', 'aguard_producao'],
                itens__produto=peca.produto,
            ).distinct().select_related('cliente')

            if request.method == 'POST':
                pedido_pk = request.POST.get('pedido_pk')
                if pedido_pk:
                    pedido = get_object_or_404(
                        Pedido,
                        pk=pedido_pk,
                        status__in=['picking', 'aguard_producao']
                    )

                    _debitar_componentes_ficha(peca, pedido, request.user)

                    peca.pedido       = pedido
                    peca.status       = 'separado'
                    peca.separada_por = request.user
                    peca.separada_em  = timezone.now()
                    peca.save(update_fields=['pedido', 'status', 'separada_por', 'separada_em'])

                    # Se pedido estava em aguard_producao, vai para picking
                    if pedido.status == 'aguard_producao':
                        pedido.status = pedido.Status.PICKING
                        pedido.save(update_fields=['status', 'atualizado_em'])

                    # Verifica se todas as peças do pedido foram separadas
                    total     = ProdutoCortado.objects.filter(pedido=pedido).count()
                    separadas = ProdutoCortado.objects.filter(pedido=pedido, status='separado').count()

                    return render(request, 'vendas/peca_separada.html', {
                        'peca':   peca,
                        'pedido': pedido,
                    })

            return render(request, 'vendas/peca_vincular_pedido.html', {
                'peca':               peca,
                'pedidos_precisando': pedidos_precisando,
            })

        # Peça com pedido — confirmar separação
        if request.method == 'POST':
            pedido = peca.pedido

            _debitar_componentes_ficha(peca, pedido, request.user)

            peca.status       = 'separado'
            peca.separada_por = request.user
            peca.separada_em  = timezone.now()
            peca.save(update_fields=['status', 'separada_por', 'separada_em'])

            return render(request, 'vendas/peca_separada.html', {
                'peca':   peca,
                'pedido': pedido,
            })

        return render(request, 'vendas/peca_confirmar_separacao.html', {'peca': peca})

    # ── Peça aguardando montagem ──
    if request.method == 'POST':
        fabrica = Local.objects.filter(tipo='fabrica').first()

        try:
            ficha  = peca.produto.ficha_tecnica
            eh_kit = _ficha_e_kit(ficha)
            for componente in ficha.itens.select_related('material').all():
                Movimentacao.objects.create(
                    produto    = componente.material,
                    local      = fabrica,
                    tipo       = 'entrada',
                    motivo     = 'producao',
                    quantidade = componente.quantidade,
                    observacao = f'Montagem — {peca.produto.nome}',
                    usuario    = request.user,
                )
        except peca.produto.__class__.ficha_tecnica.RelatedObjectDoesNotExist:
            eh_kit = False

        # ── Dá entrada na peça pronta no estoque (pulado se for kit) ──
        if not eh_kit:
            Movimentacao.objects.create(
                produto    = peca.produto,
                local      = fabrica,
                tipo       = 'entrada',
                motivo     = 'producao',
                quantidade = 1,
                observacao = f'Montagem — {peca.produto.nome} (peça pronta)',
                usuario    = request.user,
            )

        peca.status      = 'montado'
        peca.montada_por = request.user
        peca.montada_em  = timezone.now()
        peca.save(update_fields=['status', 'montada_por', 'montada_em'])

        # Verifica se todas as peças do pedido foram montadas
        if peca.pedido:
            pedido   = peca.pedido
            total    = ProdutoCortado.objects.filter(pedido=pedido).count()
            montadas = ProdutoCortado.objects.filter(pedido=pedido, status='montado').count()

            if total > 0 and montadas >= total:
                pedido.status = pedido.Status.PICKING
                pedido.save(update_fields=['status', 'atualizado_em'])

        return render(request, 'montagem/peca_montada.html', {
            'peca':   peca,
            'pedido': peca.pedido,
        })

    return render(request, 'montagem/peca_confirmar.html', {'peca': peca})