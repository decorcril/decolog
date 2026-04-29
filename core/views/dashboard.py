from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from movimentacoes.models import Movimentacao
from estoque.models import Estoque
from produtos.models import Produto
from core.models import Local
from producao_corte.models import RegistroCorte
import json


@login_required
def dashboard(request):
    periodo = request.GET.get('periodo', '30')
    try:
        dias = int(periodo)
    except ValueError:
        dias = 30

    data_inicio = timezone.now() - timedelta(days=dias)

    user = request.user
    is_gerente = user.is_staff or user.groups.filter(name='Gerente').exists()
    is_supervisor_laser = user.is_staff or user.groups.filter(name='Supervisor de Laser').exists()
    is_operador_laser = user.groups.filter(name='Operador laser').exists()
    is_laser = is_supervisor_laser or is_operador_laser

    # ── Indicadores gerais ──
    total_produtos = Produto.objects.filter(ativo=True).count()
    total_itens_estoque = Estoque.objects.filter(quantidade__gt=0).count()
    total_criticos = Estoque.objects.filter(
        estoque_minimo__gt=0, quantidade__lte=F('estoque_minimo')
    ).count()
    total_alerta = Estoque.objects.filter(
        estoque_minimo__gt=0,
        quantidade__gt=F('estoque_minimo'),
        quantidade__lte=F('estoque_minimo') * 2
    ).count()

    # ── Indicadores laser ──
    total_chapas_estoque = Estoque.objects.filter(
        produto__categoria='chapa', quantidade__gt=0
    ).count()
    total_cortes_periodo = RegistroCorte.objects.filter(
        data__gte=data_inicio.date()
    ).count()
    meus_cortes_periodo = RegistroCorte.objects.filter(
        operador=user, data__gte=data_inicio.date()
    ).count()

    # ── Eixo de datas ──
    dias_labels = [
        (data_inicio + timedelta(days=i+1)).date().strftime('%d/%m')
        for i in range(dias)
    ]

    # ── Gráfico 1: Entradas vs Vendas por dia ──
    entradas_qs = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_ENTRADA, data_hora__gte=data_inicio
    ).annotate(dia=TruncDate('data_hora')).values('dia').annotate(
        total=Count('id')
    ).order_by('dia')
    entradas_dict = {e['dia'].strftime('%d/%m'): e['total'] for e in entradas_qs}
    entradas_data = [entradas_dict.get(d, 0) for d in dias_labels]

    vendas_qs = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_SAIDA, motivo='venda', data_hora__gte=data_inicio
    ).annotate(dia=TruncDate('data_hora')).values('dia').annotate(
        total=Count('id')
    ).order_by('dia')
    vendas_dict = {v['dia'].strftime('%d/%m'): v['total'] for v in vendas_qs}
    vendas_data = [vendas_dict.get(d, 0) for d in dias_labels]

    # ── Gráfico 2: Saídas por motivo no período ──
    saidas_por_motivo = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_SAIDA, data_hora__gte=data_inicio
    ).values('motivo').annotate(total=Count('id')).order_by('-total')

    motivo_labels = []
    motivo_data = []
    motivo_display = dict(Movimentacao.MOTIVO_CHOICES)
    for s in saidas_por_motivo:
        motivo_labels.append(motivo_display.get(s['motivo'], s['motivo'] or 'Sem motivo'))
        motivo_data.append(s['total'])

    # ── Gráfico 3: Top 10 produtos mais vendidos ──
    top_produtos = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_SAIDA, motivo='venda', data_hora__gte=data_inicio
    ).values('produto__nome').annotate(
        total=Sum('quantidade')
    ).order_by('-total')[:10]

    # ── Gráfico 4: Cortes por operador ──
    cortes_por_operador = RegistroCorte.objects.filter(
        data__gte=data_inicio.date()
    ).values(
        'operador__first_name', 'operador__last_name', 'operador__username'
    ).annotate(total=Count('id')).order_by('-total')

    cortes_operador_labels = []
    for c in cortes_por_operador:
        nome = f"{c['operador__first_name']} {c['operador__last_name']}".strip()
        cortes_operador_labels.append(nome or c['operador__username'])
    cortes_operador_data = [c['total'] for c in cortes_por_operador]

    # ── Últimas movimentações ──
    ultimas_movimentacoes = Movimentacao.objects.select_related(
        'produto', 'local', 'usuario'
    ).order_by('-data_hora')[:8]

    # ── Cortes recentes ──
    if is_gerente or is_supervisor_laser:
        cortes_recentes = RegistroCorte.objects.prefetch_related(
            'itens__chapa', 'itens__produtos_cortados__produto'
        ).select_related('operador').order_by('-data', '-criado_em')[:8]
    elif is_operador_laser:
        cortes_recentes = RegistroCorte.objects.filter(
            operador=user
        ).prefetch_related(
            'itens__chapa', 'itens__produtos_cortados__produto'
        ).select_related('operador').order_by('-data', '-criado_em')[:8]
    else:
        cortes_recentes = None

    return render(request, 'core/dashboard.html', {
        'total_produtos': total_produtos,
        'total_itens_estoque': total_itens_estoque,
        'total_criticos': total_criticos,
        'total_alerta': total_alerta,
        'total_chapas_estoque': total_chapas_estoque,
        'total_cortes_periodo': total_cortes_periodo,
        'meus_cortes_periodo': meus_cortes_periodo,
        'dias_labels': json.dumps(dias_labels),
        'entradas_data': json.dumps(entradas_data),
        'vendas_data': json.dumps(vendas_data),
        'saidas_por_motivo': json.dumps({
            'labels': motivo_labels,
            'data': motivo_data,
        }),
        'top_produtos': json.dumps({
            'labels': [p['produto__nome'] for p in top_produtos],
            'data': [float(p['total']) for p in top_produtos],
        }),
        'cortes_por_operador': json.dumps({
            'labels': cortes_operador_labels,
            'data': cortes_operador_data,
        }),
        'ultimas_movimentacoes': ultimas_movimentacoes,
        'cortes_recentes': cortes_recentes,
        'periodo': periodo,
        'is_gerente': is_gerente,
        'is_supervisor_laser': is_supervisor_laser,
        'is_operador_laser': is_operador_laser,
        'is_laser': is_laser,
    })