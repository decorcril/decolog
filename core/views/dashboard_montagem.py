from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from itertools import chain

from vendas.models import Pedido, UnidadePedido


@login_required
def dashboard_montagem(request):
    from producao_corte.models import ProdutoCortado

    user   = request.user
    hoje   = timezone.localdate()
    semana = hoje - timedelta(days=hoje.weekday())

    # ── Pedidos em montagem ──
    pedidos_montagem = Pedido.objects.filter(
        status='assembling',
    ).select_related('cliente').prefetch_related('itens__produto').order_by('criado_em')

    pedidos_com_progresso = []
    for pedido in pedidos_montagem:
        pedidos_com_progresso.append({
            'pedido':             pedido,
            'progresso_montagem': pedido.progresso_montagem,
        })

    # ── Peças avulsas aguardando montagem (sem pedido vinculado) ──
    pecas_avulsas = ProdutoCortado.objects.filter(
        pedido__isnull=True,
        status='aguardando',
    ).select_related('produto', 'cortada_por').order_by('item_corte__registro__criado_em')

    # ── Montagens do dia (insumos + peças cortadas) ──
    # NOTA: usa montada_em (fato histórico) em vez de status='montado', porque
    # o status da peça avança para 'separado'/'enviado' depois da montagem —
    # filtrar por status atual fazia peças já separadas somem da contagem.
    montagens_hoje = (
        UnidadePedido.objects.filter(montada=True, montada_em__date=hoje).count()
        + ProdutoCortado.objects.filter(montada_em__date=hoje).count()
    )

    # ── Montagens da semana (insumos + peças cortadas) ──
    montagens_semana = (
        UnidadePedido.objects.filter(
            montada=True, montada_em__date__gte=semana, montada_em__date__lte=hoje,
        ).count()
        + ProdutoCortado.objects.filter(
            montada_em__date__gte=semana, montada_em__date__lte=hoje,
        ).count()
    )

    # ── Histórico recente (insumos + peças cortadas, unificado) ──
    historico_insumos = UnidadePedido.objects.filter(
        montada=True,
    ).select_related(
        'montada_por', 'item__pedido__cliente', 'item__produto'
    ).order_by('-montada_em')[:10]

    historico_pecas = ProdutoCortado.objects.filter(
        montada_em__isnull=False,
    ).select_related('montada_por', 'pedido__cliente', 'produto').order_by('-montada_em')[:10]

    historico_unificado = []
    for reg in historico_insumos:
        historico_unificado.append({
            'montada_em':  reg.montada_em,
            'montada_por': reg.montada_por,
            'pedido':      reg.item.pedido,
            'cliente':     reg.item.pedido.cliente if reg.item.pedido else None,
            'produto':     reg.item.produto,
            'unidade':     f'{reg.numero}/{reg.item.quantidade}',
        })
    for reg in historico_pecas:
        historico_unificado.append({
            'montada_em':  reg.montada_em,
            'montada_por': reg.montada_por,
            'pedido':      reg.pedido,
            'cliente':     reg.pedido.cliente if reg.pedido else None,
            'produto':     reg.produto,
            'unidade':     '—',
        })

    historico_unificado.sort(key=lambda r: r['montada_em'] or timezone.now(), reverse=True)
    historico_unificado = historico_unificado[:10]

    return render(request, 'core/dashboard_montagem.html', {
        'pedidos':          pedidos_com_progresso,
        'pecas_avulsas':    pecas_avulsas,
        'montagens_hoje':   montagens_hoje,
        'montagens_semana': montagens_semana,
        'historico':        historico_unificado,
        'hoje':             hoje,
    })