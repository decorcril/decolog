from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from estoque.models import Estoque
from produtos.models import Produto
from ..models import RegistroCorte, ItemCorteEntrada, ItemCorteSaida
import json


@login_required
def registro_corte_create(request):
    produtos_materiais = Produto.objects.filter(
        categoria ='materia_prima'
    ).order_by('nome')
    produtos_finais = Produto.objects.filter(
        categoria ='produto_final'
    ).order_by('nome')

    if request.method == 'POST':
        data = request.POST.get('data')
        observacao = request.POST.get('observacao', '')

        # Valida data
        from datetime import date
        try:
            data_parsed = date.fromisoformat(data)
        except (ValueError, TypeError):
            messages.error(request, 'Data inválida.')
            return redirect('producao_corte:create')

        if data_parsed > timezone.localdate():
            messages.error(request, 'A data não pode ser no futuro.')
            return redirect('producao_corte:create')

        # Coleta itens do POST
        entradas = []  # chapas consumidas
        saidas = []    # produtos cortados

        i = 0
        while f'entrada_produto_{i}' in request.POST:
            prod_id = request.POST.get(f'entrada_produto_{i}')
            qty = request.POST.get(f'entrada_quantidade_{i}')
            if prod_id and qty:
                entradas.append((prod_id, qty))
            i += 1

        i = 0
        while f'saida_produto_{i}' in request.POST:
            prod_id = request.POST.get(f'saida_produto_{i}')
            qty = request.POST.get(f'saida_quantidade_{i}')
            if prod_id and qty:
                saidas.append((prod_id, qty))
            i += 1

        if not entradas:
            messages.error(request, 'Informe ao menos uma chapa utilizada.')
            return redirect('producao_corte:create')

        if not saidas:
            messages.error(request, 'Informe ao menos um produto cortado.')
            return redirect('producao_corte:create')

        # Valida estoque das chapas
        from django.db import transaction
        try:
            with transaction.atomic():
                registro = RegistroCorte.objects.create(
                    data=data_parsed,
                    operador=request.user,
                    observacao=observacao,
                )

                for prod_id, qty in entradas:
                    produto = Produto.objects.get(pk=prod_id)
                    quantidade = float(qty)

                    # Baixa no estoque (soma de todos os locais)
                    estoque_total = sum(
                        e.quantidade for e in Estoque.objects.filter(produto=produto)
                    )
                    if estoque_total < quantidade:
                        raise ValueError(
                            f'Estoque insuficiente para {produto.nome}: '
                            f'disponível {estoque_total}, solicitado {quantidade}.'
                        )

                    # Abate proporcional dos locais
                    restante = quantidade
                    for estoque in Estoque.objects.filter(produto=produto).order_by('-quantidade'):
                        if restante <= 0:
                            break
                        abate = min(estoque.quantidade, restante)
                        estoque.quantidade -= abate
                        estoque.save()
                        restante -= abate

                    ItemCorteEntrada.objects.create(
                        registro=registro,
                        produto=produto,
                        quantidade=quantidade,
                    )

                for prod_id, qty in saidas:
                    produto = Produto.objects.get(pk=prod_id)
                    ItemCorteSaida.objects.create(
                        registro=registro,
                        produto=produto,
                        quantidade=float(qty),
                    )

                messages.success(request, 'Registro de corte salvo com sucesso!')
                return redirect('producao_corte:list')

        except ValueError as e:
            messages.error(request, str(e))
            return redirect('producao_corte:create')

    context = {
        'produtos_materiais': produtos_materiais,
        'produtos_finais': produtos_finais,
        'hoje': timezone.localdate().isoformat(),
    }
    return render(request, 'producao_corte/registro_corte_form.html', context)


@login_required
def registro_corte_list(request):
    registros = RegistroCorte.objects.prefetch_related(
        'entradas__produto', 'saidas__produto'
    ).select_related('operador').all()
    return render(request, 'producao_corte/registro_corte_list.html', {'registros': registros})