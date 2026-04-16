from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.mixins import estoquista_ou_admin
from movimentacoes.models import Movimentacao
from movimentacoes.forms import SaidaForm


@estoquista_ou_admin
def saida_create(request):
    form = SaidaForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        Movimentacao.objects.create(
            produto=form.cleaned_data['produto'],
            local=form.cleaned_data['local'],
            tipo=Movimentacao.TIPO_SAIDA,
            quantidade=form.cleaned_data['quantidade'],
            motivo=form.cleaned_data['motivo'],
            observacao=form.cleaned_data['observacao'],
            usuario=request.user,
        )
        messages.success(request, 'Saída registrada com sucesso!')
        return redirect('movimentacoes:saida')

    return render(request, 'movimentacoes/saida/form.html', {
        'form': form,
        'titulo': 'Saída de Estoque',
    })