from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

from vendas.models import Pedido, UnidadePedido


@login_required
def dashboard_montagem(request):
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

    # ── Montagens do dia ──
    montagens_hoje = UnidadePedido.objects.filter(
        montada=True,
        montada_em__date=hoje,
    ).count()

    # ── Montagens da semana ──
    montagens_semana = UnidadePedido.objects.filter(
        montada=True,
        montada_em__date__gte=semana,
        montada_em__date__lte=hoje,
    ).count()

    # ── Histórico recente ──
    historico = UnidadePedido.objects.filter(
        montada=True,
    ).select_related(
        'montada_por', 'item__pedido__cliente', 'item__produto'
    ).order_by('-montada_em')[:10]

    return render(request, 'core/dashboard_montagem.html', {
        'pedidos':          pedidos_com_progresso,
        'montagens_hoje':   montagens_hoje,
        'montagens_semana': montagens_semana,
        'historico':        historico,
        'hoje':             hoje,
    })