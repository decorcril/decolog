from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

from vendas.models import Pedido


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
        pedidos_com_info.append({
            'pedido':      pedido,
            'is_retirada': pedido.transportadora == 'Retirada na Loja',
        })

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
        'pedidos':          pedidos_com_info,
        'enviados_hoje':    enviados_hoje,
        'enviados_semana':  enviados_semana,
        'historico':        historico,
        'hoje':             hoje,
    })