from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from movimentacoes.models import Movimentacao
from estoque.models import Estoque
from produtos.models import Produto
import json

@login_required
def dashboard(request):
    periodo = request.GET.get('periodo', '30')
    try:
        dias = int(periodo)
    except ValueError:
        dias = 30

    data_inicio = timezone.now() - timedelta(days=dias)

    # ── Indicadores gerais ──
    total_produtos = Produto.objects.filter(ativo=True).count()
    total_itens_estoque = Estoque.objects.filter(quantidade__gt=0).count()
    total_criticos = Estoque.objects.filter(
    estoque_minimo__gt=0,
    quantidade__lte=F('estoque_minimo')
    ).count()
    total_alerta = Estoque.objects.filter(
    estoque_minimo__gt=0,
    quantidade__gt=F('estoque_minimo'),
    quantidade__lte=F('estoque_minimo') * 2
    ).count()

    # ── Entradas por dia ──
    entradas = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_ENTRADA,
        data_hora__gte=data_inicio
    ).annotate(
        dia=TruncDate('data_hora')
    ).values('dia').annotate(
        total=Count('id')
    ).order_by('dia')

    # ── Saídas por dia ──
    saidas = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_SAIDA,
        data_hora__gte=data_inicio
    ).annotate(
        dia=TruncDate('data_hora')
    ).values('dia').annotate(
        total=Count('id')
    ).order_by('dia')

    # ── Últimas movimentações ──
    ultimas_movimentacoes = Movimentacao.objects.select_related(
        'produto', 'local', 'usuario'
    ).order_by('-data_hora')[:8]

    # ── Prepara dados para o gráfico ──
    # Gera todos os dias do período
    dias_labels = []
    entradas_dict = {e['dia'].strftime('%d/%m'): e['total'] for e in entradas}
    saidas_dict = {s['dia'].strftime('%d/%m'): s['total'] for s in saidas}

    for i in range(dias):
        dia = (data_inicio + timedelta(days=i+1)).date()
        dias_labels.append(dia.strftime('%d/%m'))

    entradas_data = [entradas_dict.get(d, 0) for d in dias_labels]
    saidas_data = [saidas_dict.get(d, 0) for d in dias_labels]

    return render(request, 'core/dashboard.html', {
    'total_produtos': total_produtos,
    'total_itens_estoque': total_itens_estoque,
    'total_criticos': total_criticos,
    'total_alerta': total_alerta,
    'dias_labels': json.dumps(dias_labels),
    'entradas_data': json.dumps(entradas_data),
    'saidas_data': json.dumps(saidas_data),
    'ultimas_movimentacoes': ultimas_movimentacoes,
    'periodo': periodo,
})