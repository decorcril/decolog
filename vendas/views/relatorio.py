from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import HttpResponse
from decimal import Decimal
import calendar
import csv

from core.mixins import financeiro_ou_gerente
from vendas.models import Pedido


MESES_PT = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março',    4: 'Abril',
    5: 'Maio',    6: 'Junho',     7: 'Julho',     8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro',
}

BONUS_MINIMO = Decimal('10000')
BONUS_VALOR  = Decimal('100')

FAIXAS = [
    (Decimal('0'),      Decimal('40000'),  Decimal('0.01')),
    (Decimal('40000'),  Decimal('80000'),  Decimal('0.015')),
    (Decimal('80000'),  Decimal('150000'), Decimal('0.02')),
    (Decimal('150000'), None,              Decimal('0.025')),
]


def calcular_bonus(pedidos_qs):
    vendas_por_dia = (
        pedidos_qs
        .annotate(dia=TruncDate('criado_em'))
        .values('dia')
        .annotate(total_dia=Sum('total_produtos') - Sum('total_desconto'))
        .order_by('dia')
    )

    dias_com_bonus = []
    for v in vendas_por_dia:
        total = v['total_dia'] or Decimal('0')
        if total > BONUS_MINIMO:
            dias_com_bonus.append({
                'dia':   v['dia'],
                'total': total,
            })

    return len(dias_com_bonus) * BONUS_VALOR, dias_com_bonus


def calcular_comissao(total, bonus):
    for minimo, maximo, percentual in FAIXAS:
        if maximo is None or total <= maximo:
            return (total * percentual).quantize(Decimal('0.01')) + bonus
    return Decimal('0')


@financeiro_ou_gerente
def relatorio_comissoes(request):
    hoje        = timezone.localdate()
    mes         = int(request.GET.get('mes', hoje.month))
    ano         = int(request.GET.get('ano', hoje.year))
    vendedor_id = request.GET.get('vendedor', '')

    primeiro_dia = hoje.replace(year=ano, month=mes, day=1)
    ultimo_dia   = hoje.replace(
        year=ano, month=mes,
        day=calendar.monthrange(ano, mes)[1]
    )

    todos_vendedores = User.objects.filter(
        groups__name='Vendedor', is_active=True
    ).order_by('first_name', 'last_name', 'username')

    vendedores = todos_vendedores
    if vendedor_id:
        vendedores = vendedores.filter(pk=vendedor_id)

    relatorio             = []
    total_geral_comissoes = Decimal('0')

    for vendedor in vendedores:
        pedidos_qs = Pedido.objects.filter(
            criado_por=vendedor,
            criado_em__date__gte=primeiro_dia,
            criado_em__date__lte=ultimo_dia,
            pagamentos__isnull=False,
        ).distinct()

        total_liquido = pedidos_qs.aggregate(
            total=Sum('total_produtos') - Sum('total_desconto')
        )['total'] or Decimal('0')

        if total_liquido < 0:
            total_liquido = Decimal('0')

        percentual = Decimal('0')
        for minimo, maximo, perc in FAIXAS:
            if maximo is None or total_liquido <= maximo:
                percentual = perc
                break

        bonus, dias_com_bonus = calcular_bonus(pedidos_qs)
        comissao              = calcular_comissao(total_liquido, bonus)
        dias_bonus            = len(dias_com_bonus)

        page_param = f'page_{vendedor.pk}'
        paginator  = Paginator(
            pedidos_qs.select_related('cliente').order_by('-criado_em'), 10
        )
        page_obj = paginator.get_page(request.GET.get(page_param, 1))

        relatorio.append({
            'vendedor':       vendedor,
            'nome':           vendedor.get_full_name() or vendedor.username,
            'total_liquido':  total_liquido,
            'percentual':     percentual * 100,
            'comissao':       comissao,
            'bonus':          bonus,
            'dias_bonus':     dias_bonus,
            'dias_com_bonus': dias_com_bonus,
            'tem_bonus':      bonus > 0,
            'qtd_pedidos':    pedidos_qs.count(),
            'pedidos':        page_obj,
            'page_obj':       page_obj,
            'page_param':     page_param,
        })

        total_geral_comissoes += comissao

    meses = [(i, MESES_PT[i]) for i in range(1, 13)]
    anos  = list(range(hoje.year - 2, hoje.year + 1))

    return render(request, 'vendas/relatorio_comissoes.html', {
        'relatorio':             relatorio,
        'total_geral_comissoes': total_geral_comissoes,
        'mes':                   mes,
        'ano':                   ano,
        'meses':                 meses,
        'anos':                  anos,
        'primeiro_dia':          primeiro_dia,
        'ultimo_dia':            ultimo_dia,
        'todos_vendedores':      todos_vendedores,
        'vendedor_id':           vendedor_id,
    })


@financeiro_ou_gerente
def exportar_comissoes_csv(request):
    hoje        = timezone.localdate()
    mes         = int(request.GET.get('mes', hoje.month))
    ano         = int(request.GET.get('ano', hoje.year))
    vendedor_id = request.GET.get('vendedor', '')

    primeiro_dia = hoje.replace(year=ano, month=mes, day=1)
    ultimo_dia   = hoje.replace(
        year=ano, month=mes,
        day=calendar.monthrange(ano, mes)[1]
    )

    vendedores = User.objects.filter(
        groups__name='Vendedor', is_active=True
    ).order_by('first_name', 'last_name', 'username')

    if vendedor_id:
        vendedores = vendedores.filter(pk=vendedor_id)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="comissoes_{ano}_{mes:02d}.csv"'
    )
    response.write('\ufeff')

    writer = csv.writer(response, delimiter=';')
    writer.writerow([
        'Vendedor',
        'Número do Pedido',
        'Cliente',
        'Tipo de Venda',
        'Data do Pedido',
        'Data do Pagamento',
        'Total Produtos',
        'Desconto',
        'Frete',
        'Total Líquido',
        'Total Pago',
        'Status',
    ])

    for vendedor in vendedores:
        pedidos_qs = Pedido.objects.filter(
            criado_por=vendedor,
            criado_em__date__gte=primeiro_dia,
            criado_em__date__lte=ultimo_dia,
            pagamentos__isnull=False,
        ).distinct().select_related(
            'cliente'
        ).prefetch_related('pagamentos').order_by('criado_em')

        for pedido in pedidos_qs:
            primeiro_pagamento = pedido.pagamentos.order_by('pago_em').first()
            data_pagamento     = (
                primeiro_pagamento.pago_em.strftime('%d/%m/%Y')
                if primeiro_pagamento and primeiro_pagamento.pago_em else '—'
            )
            total_liquido = pedido.total_produtos - pedido.total_desconto

            writer.writerow([
                vendedor.get_full_name() or vendedor.username,
                pedido.numero,
                pedido.cliente.nome,
                pedido.get_tipo_venda_display(),
                pedido.criado_em.strftime('%d/%m/%Y'),
                data_pagamento,
                str(pedido.total_produtos).replace('.', ','),
                str(pedido.total_desconto).replace('.', ','),
                str(pedido.frete).replace('.', ','),
                str(total_liquido).replace('.', ','),
                str(pedido.total_pago).replace('.', ','),
                pedido.get_status_display(),
            ])

    return response