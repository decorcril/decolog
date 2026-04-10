from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from movimentacoes.models import Movimentacao
from movimentacoes.forms import TransferenciaForm


@login_required
def transferencia_create(request):
    form = TransferenciaForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        Movimentacao.objects.create(
            produto=form.cleaned_data['produto'],
            local=form.cleaned_data['local_origem'],
            local_destino=form.cleaned_data['local_destino'],
            tipo=Movimentacao.TIPO_TRANSFERENCIA,
            quantidade=form.cleaned_data['quantidade'],
            observacao=form.cleaned_data['observacao'],
            usuario=request.user,
        )
        messages.success(request, 'Transferência realizada com sucesso!')
        return redirect('movimentacoes:transferencia')

    return render(request, 'movimentacoes/transferencia/form.html', {
        'form': form,
        'titulo': 'Transferência entre Locais',
    })