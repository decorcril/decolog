from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

from vendas.models import Pedido
from producao_corte.models import RegistroCorte


@login_required
def dashboard_laser(request):
    user  = request.user
    hoje  = timezone.localdate()
    semana = hoje - timedelta(days=hoje.weekday())

    # ── Pedidos atribuídos ao operador ──
    pedidos_atribuidos = Pedido.objects.filter(
        operador_corte=user,
        status__in=['aguard_producao', 'cutting'],
    ).select_related('cliente').prefetch_related('itens__produto').order_by('criado_em')

    # ── Cortes do dia ──
    cortes_hoje = RegistroCorte.objects.filter(
        operador=user,
        data=hoje,
    ).count()

    # ── Cortes da semana ──
    cortes_semana = RegistroCorte.objects.filter(
        operador=user,
        data__gte=semana,
        data__lte=hoje,
    ).count()

    # ── Pedidos com progresso ──
    pedidos_com_progresso = []
    for pedido in pedidos_atribuidos:
        pedidos_com_progresso.append({
            'pedido':          pedido,
            'progresso_corte': pedido.progresso_corte,
            'status':          pedido.status,
        })

    return render(request, 'core/dashboard_laser.html', {
        'pedidos':       pedidos_com_progresso,
        'cortes_hoje':   cortes_hoje,
        'cortes_semana': cortes_semana,
        'hoje':          hoje,
    })