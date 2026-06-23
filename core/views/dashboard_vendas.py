from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count
from django.utils import timezone
from decimal import Decimal
import calendar
import json

from vendas.models import Pedido
from vendas.views.relatorio import FAIXAS, calcular_bonus, calcular_comissao


MESES_PT = {
    1: 'Jan', 2: 'Fev', 3: 'Mar',  4: 'Abr',
    5: 'Mai', 6: 'Jun', 7: 'Jul',  8: 'Ago',
    9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez',
}

MESES_NOME = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro',
}


FAIXAS_INFO = [
    {'label': 'Até R$ 40.000',        'meta': 40000,  'percentual': 1.0},
    {'label': 'R$ 40.001–R$ 80.000',  'meta': 80000,  'percentual': 1.5},
    {'label': 'R$ 80.001–R$ 150.000', 'meta': 150000, 'percentual': 2.0},
    {'label': 'Acima de R$ 150.000',  'meta': 150000, 'percentual': 2.5},
]


@login_required
def dashboard_vendas(request):
    user  = request.user
    hoje  = timezone.localdate()
    mes   = hoje.month
    ano   = hoje.year

    primeiro_dia = hoje.replace(day=1)
    ultimo_dia   = hoje.replace(day=calendar.monthrange(ano, mes)[1])

    # ── Pedidos do mês com pagamento ──
    pedidos_mes = Pedido.objects.filter(
        criado_por=user,
        criado_em__date__gte=primeiro_dia,
        criado_em__date__lte=ultimo_dia,
        pagamentos__isnull=False,
    ).distinct()

    # ── Total líquido do mês ──
    total_liquido = pedidos_mes.aggregate(
        total=Sum('total_produtos') - Sum('total_desconto')
    )['total'] or Decimal('0')
    if total_liquido < 0:
        total_liquido = Decimal('0')

    # ── Comissão estimada ──
    bonus, dias_com_bonus = calcular_bonus(pedidos_mes)
    comissao_estimada     = calcular_comissao(total_liquido, bonus)
    dias_bonus            = len(dias_com_bonus)

    # ── Percentual da faixa atual ──
    percentual      = Decimal('0')
    faixa_atual_idx = 0
    for i, (minimo, maximo, perc) in enumerate(FAIXAS):
        if maximo is None or total_liquido <= maximo:
            percentual      = perc * 100
            faixa_atual_idx = i
            break

    # ── Progresso para próxima faixa ──
    _, _, _ = FAIXAS[faixa_atual_idx]
    proxima_meta  = FAIXAS[faixa_atual_idx][1]  # maximo da faixa atual
    if proxima_meta is None:
        proxima_meta   = total_liquido
        falta_proxima  = Decimal('0')
        progresso_pct  = 100.0
    else:
        proxima_meta  = Decimal(str(proxima_meta))
        falta_proxima = max(Decimal('0'), proxima_meta - total_liquido)
        progresso_pct = min(100.0, float(total_liquido / proxima_meta * 100))

    # ── Pedidos em aberto ──
    pedidos_abertos = Pedido.objects.filter(
        criado_por=user,
        status='open',
    ).select_related('cliente').order_by('-criado_em')

    # ── Contadores por status ──
    contadores = Pedido.objects.filter(
        criado_por=user,
    ).exclude(status='canceled').values('status').annotate(total=Count('id'))
    contadores_dict = {c['status']: c['total'] for c in contadores}

    # ── Gráfico: vendas por mês (últimos 6 meses) ──
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

        total = Pedido.objects.filter(
            criado_por=user,
            criado_em__date__gte=primeiro,
            criado_em__date__lte=ultimo,
            pagamentos__isnull=False,
        ).distinct().aggregate(
            total=Sum('total_produtos') - Sum('total_desconto')
        )['total'] or Decimal('0')

        meses_labels.append(f'{MESES_PT[m]}/{str(a)[2:]}')
        meses_data.append(float(max(Decimal('0'), total)))

    # ── Últimos 5 pedidos ──
    ultimos_pedidos = Pedido.objects.filter(
        criado_por=user,
    ).select_related('cliente').order_by('-criado_em')[:5]

    return render(request, 'core/dashboard_vendas.html', {
        # Métricas do mês
        'total_liquido':     total_liquido,
        'comissao_estimada': comissao_estimada,
        'percentual':        percentual,
        'bonus':             bonus,
        'dias_bonus':        dias_bonus,
        'tem_bonus':         bonus > 0,
        'qtd_pedidos_mes':   pedidos_mes.count(),
        'mes_nome': MESES_NOME[mes],
        
        # Progresso meta
        'faixas_info':     FAIXAS_INFO,
        'proxima_meta':    proxima_meta,
        'falta_proxima':   falta_proxima,
        'progresso_pct':   progresso_pct,
        'faixa_atual_idx': faixa_atual_idx,

        # Pedidos em aberto
        'pedidos_abertos': pedidos_abertos,

        # Contadores
        'total_open':             contadores_dict.get('open', 0),
        'total_aguard_pagamento': contadores_dict.get('aguard_pagamento', 0),
        'total_aguard_producao':  contadores_dict.get('aguard_producao', 0),
        'total_cutting':          contadores_dict.get('cutting', 0),
        'total_assembling':       contadores_dict.get('assembling', 0),
        'total_picking':          contadores_dict.get('picking', 0),
        'total_shipped':          contadores_dict.get('shipped', 0),
        'total_delivered':        contadores_dict.get('delivered', 0),

        # Gráfico
        'meses_labels': json.dumps(meses_labels),
        'meses_data':   json.dumps(meses_data),

        # Últimos pedidos
        'ultimos_pedidos': ultimos_pedidos,

        'hoje': hoje,
        'mes':  mes,
        'ano':  ano,
    })