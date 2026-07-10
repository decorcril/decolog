from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

from vendas.models import Pedido, UnidadePedido


@login_required
def dashboard_logistica(request):
    user   = request.user
    hoje   = timezone.localdate()
    semana = hoje - timedelta(days=hoje.weekday())

    # ── Pedidos em separação ──
    pedidos_picking = Pedido.objects.filter(
        status='picking',
    ).select_related('cliente', 'criado_por').prefetch_related(
        'itens__produto', 'itens__unidades'
    ).order_by('criado_em')

    pedidos_com_info = []
    for pedido in pedidos_picking:
        total         = UnidadePedido.objects.filter(item__pedido=pedido).count()
        separadas     = UnidadePedido.objects.filter(item__pedido=pedido, separada=True).count()
        tudo_separado = total > 0 and separadas >= total
        pedidos_com_info.append({
            'pedido':        pedido,
            'is_retirada':   pedido.transportadora == 'Retirada na Loja',
            'total':         total,
            'separadas':     separadas,
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