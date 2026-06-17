import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from vendas.services.melhor_envio import calcular_frete


@login_required
def calcular_frete_view(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'erro': 'Método não permitido.'})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'erro': 'JSON inválido.'})

    cep_destino = data.get('cep_destino', '').replace('-', '').replace('.', '')
    produtos    = data.get('produtos', [])

    if not cep_destino or len(cep_destino) != 8:
        return JsonResponse({'ok': False, 'erro': 'CEP de destino inválido.'})

    if not produtos:
        return JsonResponse({'ok': False, 'erro': 'Nenhum produto informado.'})

    opcoes = calcular_frete(cep_destino, produtos)

    if opcoes and 'erro' in opcoes[0]:
        return JsonResponse({'ok': False, 'erro': opcoes[0]['erro']})

    return JsonResponse({'ok': True, 'opcoes': opcoes})