from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction

from core.mixins import producao_ou_gerente
from producao_corte.models import RegistroCorte, ProdutoCortado
from producao_corte.services import confirmar_montagem_peca


@producao_ou_gerente
def confirmar_montagem_lote(request, pk):
    registro = get_object_or_404(RegistroCorte, pk=pk)

    if request.method == 'POST':
        pecas = ProdutoCortado.objects.filter(
            item_corte__registro=registro, status='aguardando',
        ).select_related('produto', 'pedido')

        with transaction.atomic():
            count = 0
            for peca in pecas:
                confirmar_montagem_peca(peca, request.user)
                count += 1

        if count:
            messages.success(request, f'{count} peça(s) confirmada(s) como montada(s).')
        else:
            messages.info(request, 'Nenhuma peça aguardando montagem neste registro.')

    return redirect('producao_corte:detail', pk=registro.pk)