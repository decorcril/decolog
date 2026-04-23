from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import date

from produtos.models import Produto
from movimentacoes.models import Movimentacao
from estoque.models import Estoque
from core.mixins import operador_laser_ou_acima, supervisor_laser_ou_admin
from ..models import RegistroCorte, ItemCorteEntrada, ItemCorteSaida


@operador_laser_ou_acima
def registro_corte_create(request):
    produtos_materiais = Produto.objects.filter(
        categoria__in=['chapa'], ativo=True
    ).order_by('nome')
    produtos_finais = Produto.objects.filter(
        categoria='produto_final', ativo=True
    ).order_by('nome')

    if request.method == 'POST':
        data_str = request.POST.get('data')
        observacao = request.POST.get('observacao', '')

        try:
            data_parsed = date.fromisoformat(data_str)
        except (ValueError, TypeError):
            messages.error(request, 'Data inválida.')
            return redirect('producao_corte:create')

        if data_parsed > timezone.localdate():
            messages.error(request, 'A data não pode ser no futuro.')
            return redirect('producao_corte:create')

        entradas, saidas = [], []

        i = 0
        while f'entrada_produto_{i}' in request.POST:
            prod_id = request.POST.get(f'entrada_produto_{i}')
            qty = request.POST.get(f'entrada_quantidade_{i}')
            if prod_id and qty:
                entradas.append((prod_id, Decimal(qty)))
            i += 1

        i = 0
        while f'saida_produto_{i}' in request.POST:
            prod_id = request.POST.get(f'saida_produto_{i}')
            qty = request.POST.get(f'saida_quantidade_{i}')
            if prod_id and qty:
                saidas.append((prod_id, Decimal(qty)))
            i += 1

        if not entradas:
            messages.error(request, 'Informe ao menos uma chapa utilizada.')
            return redirect('producao_corte:create')

        if not saidas:
            messages.error(request, 'Informe ao menos um produto cortado.')
            return redirect('producao_corte:create')

        try:
            with transaction.atomic():
                # Valida estoque antes de qualquer operação
                from django.db.models import Sum
                for prod_id, quantidade in entradas:
                    produto = Produto.objects.get(pk=prod_id)
                    estoque_total = Estoque.objects.filter(
                        produto=produto
                    ).aggregate(total=Sum('quantidade'))['total'] or Decimal('0')

                    if estoque_total < quantidade:
                        raise ValueError(
                            f'Estoque insuficiente para {produto.nome}: '
                            f'disponível {estoque_total}, solicitado {quantidade}.'
                        )

                registro = RegistroCorte.objects.create(
                    data=data_parsed,
                    operador=request.user,
                    observacao=observacao,
                )

                for prod_id, quantidade in entradas:
                    produto = Produto.objects.get(pk=prod_id)
                    restante = quantidade

                    for estoque in Estoque.objects.filter(
                        produto=produto, quantidade__gt=0
                    ).order_by('-quantidade'):
                        if restante <= 0:
                            break
                        abate = min(estoque.quantidade, restante)

                        Movimentacao.objects.create(
                            produto=produto,
                            local=estoque.local,
                            tipo='saida',
                            motivo='uso_interno',
                            quantidade=abate,
                            observacao=f'Corte em {data_parsed.strftime("%d/%m/%Y")}',
                            usuario=request.user,
                        )

                        restante -= abate

                    ItemCorteEntrada.objects.create(
                        registro=registro,
                        produto=produto,
                        quantidade=quantidade,
                    )

                for prod_id, quantidade in saidas:
                    produto = Produto.objects.get(pk=prod_id)
                    ItemCorteSaida.objects.create(
                        registro=registro,
                        produto=produto,
                        quantidade=quantidade,
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


@operador_laser_ou_acima
def registro_corte_list(request):
    is_supervisor = (
        request.user.is_staff or
        request.user.groups.filter(name='Supervisor de Laser').exists()
    )

    if is_supervisor:
        registros = RegistroCorte.objects.all()
    else:
        registros = RegistroCorte.objects.filter(operador=request.user)

    registros = registros.prefetch_related(
        'entradas__produto', 'saidas__produto'
    ).select_related('operador')

    return render(request, 'producao_corte/registro_corte_list.html', {
        'registros': registros,
        'is_supervisor': is_supervisor,
    })