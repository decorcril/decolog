from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from decimal import Decimal
import calendar
import json

from vendas.models import Pedido
from vendas.models.pagamento import Pagamento


MESES_PT = {
    1: 'Jan', 2: 'Fev', 3: 'Mar',  4: 'Abr',
    5: 'Mai', 6: 'Jun', 7: 'Jul',  8: 'Ago',
    9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez',
}

MESES_NOME = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março',    4: 'Abril',
    5: 'Maio',    6: 'Junho',     7: 'Julho',     8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro',
}


@login_required
def dashboard_financeiro(request):
    user  = request.user
    hoje  = timezone.localdate()
    agora = timezone.now()
    mes   = hoje.month
    ano   = hoje.year

    inicio_mes    = hoje.replace(day=1)
    inicio_semana = hoje - timezone.timedelta(days=hoje.weekday())

    # ── Pagamentos recebidos ──
    pag_hoje   = Pagamento.objects.filter(
        pago_em__date=hoje
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0')

    pag_semana = Pagamento.objects.filter(
        pago_em__date__gte=inicio_semana,
        pago_em__date__lte=hoje,
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0')

    pag_mes    = Pagamento.objects.filter(
        pago_em__date__gte=inicio_mes,
        pago_em__date__lte=hoje,
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0')

    # ── Total a receber (inadimplência) ──
    pedidos_pendentes = Pedido.objects.filter(
        status__in=['open', 'aguard_pagamento', 'aguard_producao',
                    'cutting', 'assembling', 'picking', 'shipped'],
    ).exclude(status='canceled').select_related('cliente', 'criado_por')

    total_a_receber = Decimal('0')
    pendentes_lista = []
    for pedido in pedidos_pendentes:
        saldo = pedido.saldo_restante
        if saldo > 0:
            total_a_receber += saldo
            pendentes_lista.append(pedido)

    pendentes_lista.sort(key=lambda p: p.saldo_restante, reverse=True)

    # ── Pedidos com pagamento vencido (data_entrega < hoje e saldo > 0) ──
    vencidos = [
        p for p in pendentes_lista
        if p.data_entrega and p.data_entrega < hoje
    ]

    # ── Pedidos cancelados recentes ──
    cancelados_recentes = Pedido.objects.filter(
        status='canceled',
        cancelado_em__isnull=False,
    ).select_related('cliente', 'criado_por', 'cancelado_por').order_by('-cancelado_em')[:10]

    # ── Gráfico: recebimentos por mês (últimos 6 meses) ──
    meses_labels = []
    meses_data   = []

    for i in range(5, -1, -1):
        m = mes - i
        a = ano
        while m <= 0:
            m += 12
            a -= 1

        primeiro = hoje.replace(year=a, month=m, day=1)
        ultimo   = hoje.replace(year=a, month=m, day=calendar.monthrange(a, m)[1])

        total = Pagamento.objects.filter(
            pago_em__date__gte=primeiro,
            pago_em__date__lte=ultimo,
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0')

        meses_labels.append(f'{MESES_PT[m]}/{str(a)[2:]}')
        meses_data.append(float(total))

    # ── Contadores gerais ──
    total_pedidos_abertos   = Pedido.objects.filter(status='open').count()
    total_aguard_pagamento  = Pedido.objects.filter(status='aguard_pagamento').count()
    total_cancelados_mes    = Pedido.objects.filter(
        status='canceled',
        cancelado_em__date__gte=inicio_mes,
    ).count()

    return render(request, 'core/dashboard_financeiro.html', {
        # Pagamentos
        'pag_hoje':   pag_hoje,
        'pag_semana': pag_semana,
        'pag_mes':    pag_mes,

        # Inadimplência
        'total_a_receber':  total_a_receber,
        'qtd_pendentes':    len(pendentes_lista),
        'pendentes_lista':  pendentes_lista[:10],
        'vencidos':         vencidos[:10],
        'qtd_vencidos':     len(vencidos),

        # Cancelados
        'cancelados_recentes': cancelados_recentes,
        'total_cancelados_mes': total_cancelados_mes,

        # Contadores
        'total_pedidos_abertos':  total_pedidos_abertos,
        'total_aguard_pagamento': total_aguard_pagamento,

        # Gráfico
        'meses_labels': json.dumps(meses_labels),
        'meses_data':   json.dumps(meses_data),

        'mes_nome': MESES_NOME[mes],
        'ano':      ano,
        'hoje':     hoje,
    })