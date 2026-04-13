from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from movimentacoes.models import Movimentacao
from movimentacoes.forms import AjusteForm
from estoque.models import Estoque


@login_required
def ajuste_create(request):
    form = AjusteForm(request.POST or None)
    saldo_atual = None

    if request.method == 'GET':
        produto_id = request.GET.get('produto')
        local_id = request.GET.get('local')
        if produto_id and local_id:
            try:
                saldo_atual = Estoque.objects.get(
                    produto_id=produto_id,
                    local_id=local_id
                ).quantidade
            except Estoque.DoesNotExist:
                saldo_atual = 0

    if request.method == 'POST' and form.is_valid():
        Movimentacao.objects.create(
            produto=form.cleaned_data['produto'],
            local=form.cleaned_data['local'],
            tipo=Movimentacao.TIPO_AJUSTE,
            quantidade=form.cleaned_data['quantidade'],
            observacao=form.cleaned_data['observacao'],
            usuario=request.user,
        )
        messages.success(request, 'Ajuste de estoque realizado com sucesso!')
        return redirect('movimentacoes:ajuste')

    return render(request, 'movimentacoes/ajuste/form.html', {
        'form': form,
        'saldo_atual': saldo_atual,
    })