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
    # Para adicionar novos indicadores, crie uma query aqui
    # e passe no return render abaixo
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

    # ── Gera lista de dias do período ──
    dias_labels = []
    for i in range(dias):
        dia = (data_inicio + timedelta(days=i+1)).date()
        dias_labels.append(dia.strftime('%d/%m'))

    # ── Dados para gráficos ──
    # Para adicionar novos gráficos:
    # 1. Crie a query aqui
    # 2. Monte o dict com strftime('%d/%m') como chave
    # 3. Gere a lista com list comprehension usando dias_labels
    # 4. Passe no return render com json.dumps()
    # 5. Adicione data-atributo no <script id="dashboard-data"> no template
    # 6. Leia e renderize no dashboard.js

    # Entradas
    entradas = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_ENTRADA,
        data_hora__gte=data_inicio
    ).annotate(dia=TruncDate('data_hora')).values('dia').annotate(
        total=Count('id')
    ).order_by('dia')
    entradas_dict = {e['dia'].strftime('%d/%m'): e['total'] for e in entradas}
    entradas_data = [entradas_dict.get(d, 0) for d in dias_labels]

    # Saídas
    saidas = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_SAIDA,
        data_hora__gte=data_inicio
    ).annotate(dia=TruncDate('data_hora')).values('dia').annotate(
        total=Count('id')
    ).order_by('dia')
    saidas_dict = {s['dia'].strftime('%d/%m'): s['total'] for s in saidas}
    saidas_data = [saidas_dict.get(d, 0) for d in dias_labels]

    # Transferências (visível só para Gerente/Admin no template)
    transferencias = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_TRANSFERENCIA,
        data_hora__gte=data_inicio
    ).annotate(dia=TruncDate('data_hora')).values('dia').annotate(
        total=Count('id'),
        volume=Sum('quantidade')
    ).order_by('dia')
    transferencias_count_dict = {t['dia'].strftime('%d/%m'): t['total'] for t in transferencias}
    transferencias_volume_dict = {t['dia'].strftime('%d/%m'): float(t['volume']) for t in transferencias}
    transferencias_count_data = [transferencias_count_dict.get(d, 0) for d in dias_labels]
    transferencias_volume_data = [transferencias_volume_dict.get(d, 0) for d in dias_labels]

    # ── Últimas movimentações ──
    # Para mostrar mais ou menos itens, altere o [:8] abaixo
    ultimas_movimentacoes = Movimentacao.objects.select_related(
        'produto', 'local', 'usuario'
    ).order_by('-data_hora')[:8]

    return render(request, 'core/dashboard.html', {
        # Indicadores
        'total_produtos': total_produtos,
        'total_itens_estoque': total_itens_estoque,
        'total_criticos': total_criticos,
        'total_alerta': total_alerta,
        # Gráficos
        'dias_labels': json.dumps(dias_labels),
        'entradas_data': json.dumps(entradas_data),
        'saidas_data': json.dumps(saidas_data),
        'transferencias_count_data': json.dumps(transferencias_count_data),
        'transferencias_volume_data': json.dumps(transferencias_volume_data),
        # Tabela
        'ultimas_movimentacoes': ultimas_movimentacoes,
        'periodo': periodo,
        'is_gerente': request.user.is_staff or request.user.groups.filter(name='Gerente').exists(),
    })