from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q, CharField
from django.db.models.functions import Cast

from clientes.models import Cliente
from clientes.forms import ClienteForm
from core.mixins import gerente_ou_admin, vendedor_ou_gerente


@vendedor_ou_gerente
def cliente_list(request):
    q     = request.GET.get('q', '')
    ativo = request.GET.get('ativo', 'true')

    clientes = Cliente.objects.all()

    if q:
        q_limpo = q.replace('.', '').replace('-', '').replace('/', '').replace(' ', '')
        
        # Tenta formatar como CPF (11 dígitos)
        if len(q_limpo) == 11 and q_limpo.isdigit():
            q_formatado = f'{q_limpo[:3]}.{q_limpo[3:6]}.{q_limpo[6:9]}-{q_limpo[9:]}'
        # Tenta formatar como CNPJ (14 dígitos)
        elif len(q_limpo) == 14 and q_limpo.isdigit():
            q_formatado = f'{q_limpo[:2]}.{q_limpo[2:5]}.{q_limpo[5:8]}/{q_limpo[8:12]}-{q_limpo[12:]}'
        else:
            q_formatado = q

        clientes = clientes.filter(
            Q(nome__icontains=q) |
            Q(nome_fantasia__icontains=q) |
            Q(documento__icontains=q) |
            Q(documento__icontains=q_formatado) |
            Q(codigo__icontains=q)
        )

    if ativo == 'true':
        clientes = clientes.filter(ativo=True)
    elif ativo == 'false':
        clientes = clientes.filter(ativo=False)

    paginator = Paginator(clientes, 20)
    page      = request.GET.get('page', 1)
    clientes  = paginator.get_page(page)

    return render(request, 'clientes/list.html', {
        'clientes': clientes,
        'q':        q,
        'ativo':    ativo,
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

@gerente_ou_admin
def cliente_anonimizar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)

    if request.method == 'POST':
        cliente.nome = f'Cliente Anonimizado {cliente.codigo}'
        cliente.nome_fantasia = ''
        cliente.documento = ''
        cliente.inscricao_estadual = ''
        cliente.inscricao_municipal = ''
        cliente.email = ''
        cliente.telefone = ''
        cliente.whatsapp = ''
        cliente.contato = ''
        cliente.cep = ''
        cliente.logradouro = ''
        cliente.numero = ''
        cliente.complemento = ''
        cliente.bairro = ''
        cliente.cidade = ''
        cliente.estado = ''
        cliente.codigo_postal = ''
        cliente.regiao = ''
        cliente.ativo = False
        cliente.save()
        messages.success(request, f'Dados pessoais do cliente {cliente.codigo} foram anonimizados.')
        return redirect('clientes:list')

    return render(request, 'clientes/anonimizar_confirm.html', {'cliente': cliente})