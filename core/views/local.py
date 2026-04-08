from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.models import Local
from core.forms import LocalForm


@login_required
def local_list(request):
    locais = Local.objects.all()
    return render(request, 'core/local/list.html', {'locais': locais})


@login_required
def local_create(request):
    form = LocalForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Local cadastrado com sucesso!')
        return redirect('core:local_list')
    return render(request, 'core/local/form.html', {'form': form, 'titulo': 'Novo Local'})


@login_required
def local_update(request, pk):
    local = get_object_or_404(Local, pk=pk)
    form = LocalForm(request.POST or None, instance=local)
    if form.is_valid():
        form.save()
        messages.success(request, 'Local atualizado com sucesso!')
        return redirect('core:local_list')
    return render(request, 'core/local/form.html', {'form': form, 'titulo': 'Editar Local'})


@login_required
def local_delete(request, pk):
    local = get_object_or_404(Local, pk=pk)
    if request.method == 'POST':
        local.delete()
        messages.success(request, 'Local removido com sucesso!')
        return redirect('core:local_list')
    return render(request, 'core/local/confirm_delete.html', {'local': local})