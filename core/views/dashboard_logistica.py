from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

from vendas.models import Pedido, UnidadePedido
from producao_corte.models import ProdutoCortado


@login_required
def dashboard_logistica(request):
    user   = request.user
    hoje   = timezone.localdate()
    semana = hoje - timedelta(days=hoje.weekday())

    # ── Pedidos em separação ──
    pedidos_picking = Pedido.objects.filter(
        status='picking',
    ).select_related('cliente', 'criado_por').prefetch_related(
        'itens__produto'
    ).order_by('criado_em')

    pedidos_com_info = []
    for pedido in pedidos_picking:
        # ProdutoCortado — produto_final
        total_pc     = ProdutoCortado.objects.filter(pedido=pedido).count()
        separadas_pc = ProdutoCortado.objects.filter(pedido=pedido, status='separado').count()

        # UnidadePedido — insumos
        total_uni     = UnidadePedido.objects.filter(item__pedido=pedido).count()
        separadas_uni = UnidadePedido.objects.filter(item__pedido=pedido, separada=True).count()

        total_geral     = total_pc + total_uni
        separadas_geral = separadas_pc + separadas_uni
        tudo_separado   = total_geral > 0 and separadas_geral >= total_geral

        pedidos_com_info.append({
            'pedido':        pedido,
            'is_retirada':   pedido.transportadora == 'Retirada na Loja',
            'total':         total_geral,
            'separadas':     separadas_geral,
            'tudo_separado': tudo_separado,
        })

    aguardando_separacao = [p for p in pedidos_com_info if not p['tudo_separado']]
    aguardando_envio     = [p for p in pedidos_com_info if p['tudo_separado']]

    # ── Enviados hoje ──
    enviados_hoje = Pedido.objects.filter(
        status__in=['shipped', 'delivered'],
        atualizado_em__date=hoje,
    ).count()

    # ── Enviados na semana ──
    enviados_semana = Pedido.objects.filter(
        status__in=['shipped', 'delivered'],
        atualizado_em__date__gte=semana,
        atualizado_em__date__lte=hoje,
    ).count()

    # ── Histórico recente ──
    historico = Pedido.objects.filter(
        status__in=['shipped', 'delivered'],
    ).select_related('cliente', 'criado_por').order_by('-atualizado_em')[:10]

    return render(request, 'core/dashboard_logistica.html', {
        'aguardando_separacao': aguardando_separacao,
        'aguardando_envio':     aguardando_envio,
        'enviados_hoje':        enviados_hoje,
        'enviados_semana':      enviados_semana,
        'historico':            historico,
        'hoje':                 hoje,
    })