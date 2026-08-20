from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect
from functools import wraps


def grupo_requerido(*grupos):
    """
    Decorator que verifica se o usuário pertence a um dos grupos especificados.
    Admin (is_staff) sempre tem acesso.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.is_staff:
                return view_func(request, *args, **kwargs)
            if request.user.groups.filter(name__in=grupos).exists():
                return view_func(request, *args, **kwargs)
            messages.error(request, 'Você não tem permissão para acessar esta página.')
            return redirect('core:dashboard')
        return wrapper
    return decorator


def admin_required(view_func):
    return grupo_requerido()(view_func)

def gerente_ou_admin(view_func):
    return grupo_requerido('Gerente')(view_func)

def estoquista_ou_admin(view_func):
    return grupo_requerido('Estoquista')(view_func)

def estoque_ou_gerente(view_func):
    return grupo_requerido('Estoquista', 'Gerente')(view_func)

def vendedor_ou_gerente(view_func):
    return grupo_requerido('Vendedor', 'Gerente')(view_func)

def financeiro_ou_gerente(view_func):
    return grupo_requerido('Financeiro', 'Gerente')(view_func)

def acesso_vendas(view_func):
    return grupo_requerido(
        'Vendedor', 'Financeiro', 'Gerente', 'Logística',
        'Supervisor de Montagem', 'Operador de Montagem', 'Logistica Loja'
    )(view_func)

def laser_ou_gerente(view_func):
    return grupo_requerido('Operador de Laser', 'Supervisor de Laser', 'Gerente')(view_func)

def producao_ou_gerente(view_func):
    return grupo_requerido('Operador de Laser', 'Supervisor de Laser', 'Gerente')(view_func)

def supervisor_laser_ou_admin(view_func):
    return grupo_requerido('Supervisor de Laser')(view_func)

def montagem_ou_gerente(view_func):
    return grupo_requerido('Operador de Montagem', 'Supervisor de Montagem', 'Gerente')(view_func)

def logistica_ou_gerente(view_func):
    return grupo_requerido('Logística', 'Gerente')(view_func)

def logistica_loja_ou_gerente(view_func):
    return grupo_requerido('Logistica Loja', 'Gerente')(view_func)

def estoque_ou_logistica(view_func):
    return grupo_requerido(
        'Estoquista', 'Gerente', 'Logistica Loja',
        'Vendedor', 'Operador de Laser', 'Supervisor de Laser'
    )(view_func)


def loja_do_usuario(user):
    """
    Retorna a loja (Local) vinculada ao usuário via PerfilVendedor, ou None
    se ele for staff/Gerente, ou não tiver loja definida — nesses casos,
    o usuário enxerga o estoque de todas as lojas normalmente.
    """
    if user.is_staff:
        return None

    grupos = user.groups.values_list('name', flat=True)
    if 'Gerente' in grupos:
        return None

    perfil = getattr(user, 'perfil_vendedor', None)
    if perfil and perfil.loja:
        return perfil.loja

    return None