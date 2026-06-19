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
    return grupo_requerido('Vendedor', 'Financeiro', 'Gerente')(view_func)

def laser_ou_gerente(view_func):
    return grupo_requerido('Operador de Laser', 'Supervisor de Laser', 'Gerente')(view_func)

def producao_ou_gerente(view_func):
    return grupo_requerido('Operador de Laser', 'Supervisor de Laser', 'Gerente')(view_func)

def supervisor_laser_ou_admin(view_func):
    return grupo_requerido('Supervisor de Laser')(view_func)

def montagem_ou_gerente(view_func):
    return grupo_requerido('Operador de Montagem', 'Supervisor de Montagem', 'Gerente')(view_func)