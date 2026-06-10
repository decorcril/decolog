from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q, CharField
from django.db.models.functions import Cast

from clientes.models import Cliente
from clientes.forms import ClienteForm
from core.mixins import vendedor_ou_gerente


@vendedor_ou_gerente
def cliente_list(request):
    q = request.GET.get('q', '')
    ativo = request.GET.get('ativo', 'true')

    clientes = Cliente.objects.all()

    if q:
        clientes = clientes.annotate(
            codigo_str=Cast('codigo', output_field=CharField())
        ).filter(
            Q(nome__icontains=q) |
            Q(nome_fantasia__icontains=q) |
            Q(documento__icontains=q) |
            Q(codigo_str__icontains=q)
        )

    if ativo == 'true':
        clientes = clientes.filter(ativo=True)
    elif ativo == 'false':
        clientes = clientes.filter(ativo=False)

    paginator = Paginator(clientes, 20)
    page = request.GET.get('page', 1)
    clientes = paginator.get_page(page)

    return render(request, 'clientes/list.html', {
        'clientes': clientes,
        'q': q,
        'ativo': ativo,
    })


@vendedor_ou_gerente
def cliente_create(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.criado_por = request.user
            cliente.save()
            messages.success(request, f'Cliente {cliente.nome} cadastrado com sucesso!')
            return redirect('clientes:list')
    else:
        form = ClienteForm()

    return render(request, 'clientes/form.html', {
        'form': form,
        'titulo': 'Novo Cliente',
    })


@vendedor_ou_gerente
def cliente_edit(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)

    if not request.user.is_staff:
        grupos = request.user.groups.values_list('name', flat=True)
        if 'Gerente' not in grupos and cliente.criado_por != request.user:
            raise PermissionDenied

    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cliente {cliente.nome} atualizado com sucesso!')
            return redirect('clientes:detail', pk=cliente.pk)
    else:
        form = ClienteForm(instance=cliente)

    return render(request, 'clientes/form.html', {
        'form': form,
        'titulo': f'Editar — {cliente.nome}',
        'cliente': cliente,
    })


@vendedor_ou_gerente
def cliente_detail(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    return render(request, 'clientes/detail.html', {'cliente': cliente})