def perfis_usuario(request):
    if not request.user.is_authenticated:
        return {}

    grupos = list(request.user.groups.values_list('name', flat=True))

    is_gerente             = request.user.is_staff or 'Gerente' in grupos
    is_estoquista          = 'Estoquista' in grupos
    is_supervisor_laser    = request.user.is_staff or 'Supervisor de Laser' in grupos
    is_operador_laser      = 'Operador de Laser' in grupos
    is_supervisor_montagem = request.user.is_staff or 'Supervisor de Montagem' in grupos
    is_operador_montagem   = 'Operador de Montagem' in grupos
    is_vendedor            = 'Vendedor' in grupos
    is_financeiro          = 'Financeiro' in grupos
    is_logistica           = 'Logística' in grupos

    return {
        'is_gerente':             is_gerente,
        'is_estoquista':          is_estoquista,
        'is_supervisor_laser':    is_supervisor_laser,
        'is_operador_laser':      is_operador_laser,
        'is_laser':               is_supervisor_laser or is_operador_laser,
        'is_supervisor_montagem': is_supervisor_montagem,
        'is_operador_montagem':   is_operador_montagem,
        'is_montagem':            is_supervisor_montagem or is_operador_montagem,
        'is_vendedor':            is_vendedor,
        'is_financeiro':          is_financeiro,
        'is_logistica':           is_logistica,
    }