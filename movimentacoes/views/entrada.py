from django.shortcuts import render, redirect
from django.contrib import messages
from movimentacoes.models import Movimentacao
from movimentacoes.forms import EntradaForm
from core.mixins import estoquista_ou_admin


@estoquista_ou_admin
def entrada_create(request):
    form = EntradaForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        Movimentacao.objects.create(
            produto=form.cleaned_data['produto'],
            local=form.cleaned_data['local'],
            tipo=Movimentacao.TIPO_ENTRADA,
            quantidade=form.cleaned_data['quantidade'],
            fornecedor=form.cleaned_data['fornecedor'],
            nota_fiscal=form.cleaned_data['nota_fiscal'],
            observacao=form.cleaned_data['observacao'],
            usuario=request.user,
        )
        messages.success(request, 'Entrada registrada com sucesso!')
        return redirect('movimentacoes:entrada')

    return render(request, 'movimentacoes/entrada/form.html', {
        'form': form,
        'titulo': 'Entrada de Estoque',
    })