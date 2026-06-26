from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

from vendas.models import Pedido
from montagem.models import RegistroMontagem


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
    montagens_hoje = RegistroMontagem.objects.filter(
        criado_em__date=hoje,
    ).count()

    # ── Montagens da semana ──
    montagens_semana = RegistroMontagem.objects.filter(
        criado_em__date__gte=semana,
        criado_em__date__lte=hoje,
    ).count()

    # ── Histórico recente ──
    historico = RegistroMontagem.objects.select_related(
        'operador', 'pedido__cliente'
    ).prefetch_related(
        'itens__produto'
    ).order_by('-criado_em')[:10]

    return render(request, 'core/dashboard_montagem.html', {
        'pedidos':          pedidos_com_progresso,
        'montagens_hoje':   montagens_hoje,
        'montagens_semana': montagens_semana,
        'historico':        historico,
        'hoje':             hoje,
    })