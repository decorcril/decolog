from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date

from produtos.models import Produto
from movimentacoes.models import Movimentacao
from estoque.models import Estoque
from core.mixins import operador_laser_ou_acima, producao_ou_gerente
from ..models import RegistroCorte, ItemCorte, ProdutoCortado


@producao_ou_gerente
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

        chapas = []
        i = 0
        while f'entrada_produto_{i}' in request.POST:
            prod_id = request.POST.get(f'entrada_produto_{i}')
            qty = request.POST.get(f'entrada_quantidade_{i}')
            if prod_id and qty:
                chapas.append((i, prod_id, Decimal(qty)))
            i += 1

        produtos_por_chapa = {}
        for chapa_idx, _, _ in chapas:
            produtos_por_chapa[chapa_idx] = []
            j = 0
            while f'saida_chapa_{chapa_idx}_produto_{j}' in request.POST:
                prod_id = request.POST.get(f'saida_chapa_{chapa_idx}_produto_{j}')
                qty = request.POST.get(f'saida_chapa_{chapa_idx}_quantidade_{j}')
                if prod_id and qty:
                    produtos_por_chapa[chapa_idx].append((prod_id, Decimal(qty)))
                j += 1

        if not chapas:
            messages.error(request, 'Informe ao menos uma chapa utilizada.')
            return redirect('producao_corte:create')

        tem_produtos = any(produtos_por_chapa.get(idx) for idx, _, _ in chapas)
        if not tem_produtos:
            messages.error(request, 'Informe ao menos um produto cortado.')
            return redirect('producao_corte:create')

        try:
            with transaction.atomic():
                for _, prod_id, quantidade in chapas:
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

                for chapa_idx, prod_id, quantidade in chapas:
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

                    item_corte = ItemCorte.objects.create(
                        registro=registro,
                        chapa=produto,
                        quantidade_chapa=quantidade,
                    )

                    for prod_id_saida, qty_saida in produtos_por_chapa.get(chapa_idx, []):
                        ProdutoCortado.objects.create(
                            item_corte=item_corte,
                            produto=Produto.objects.get(pk=prod_id_saida),
                            quantidade=qty_saida,
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


@producao_ou_gerente
def registro_corte_list(request):
    is_supervisor = (
        request.user.is_staff or
        request.user.groups.filter(
            name__in=['Supervisor de Laser', 'Gerente']
        ).exists()
    )

    if is_supervisor:
        registros = RegistroCorte.objects.all()
    else:
        registros = RegistroCorte.objects.filter(operador=request.user)

    operador_id = request.GET.get('operador')
    if is_supervisor and operador_id:
        registros = registros.filter(operador__id=operador_id)

    registros = registros.prefetch_related(
        'itens__chapa', 'itens__produtos_cortados__produto'
    ).select_related('operador')

    operadores = User.objects.filter(
        registrocorte__isnull=False
    ).distinct() if is_supervisor else None

    return render(request, 'producao_corte/registro_corte_list.html', {
        'registros': registros,
        'is_supervisor': is_supervisor,
        'operadores': operadores,
        'operador_id': operador_id,
    })