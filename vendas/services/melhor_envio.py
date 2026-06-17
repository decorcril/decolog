import os
import requests
from decimal import Decimal


MELHOR_ENVIO_TOKEN    = os.getenv('MELHOR_ENVIO_TOKEN')
MELHOR_ENVIO_CEP_FROM = os.getenv('MELHOR_ENVIO_CEP_ORIGEM', '').replace('-', '')

API_URL = 'https://melhorenvio.com.br/api/v2/me/shipment/calculate'
# Em produção: https://melhorenvio.com.br/api/v2/me/shipment/calculate


def calcular_frete(cep_destino: str, produtos: list[dict]) -> list[dict]:
    """
    produtos: lista de dicts com:
        {
            'id':         str,   # id do produto
            'width':      float, # largura em cm
            'height':     float, # altura em cm
            'length':     float, # comprimento em cm
            'weight':     float, # peso em kg
            'quantity':   int,
            'unitary_value': float, # valor unitário em R$
        }
    Retorna lista de opções de frete.
    """
    headers = {
        'Authorization': f'Bearer {MELHOR_ENVIO_TOKEN}',
        'Content-Type':  'application/json',
        'Accept':        'application/json',
        'User-Agent':    'Decolog/1.0 (suporte@decorcril.com.br)',
    }

    payload = {
        'from': {'postal_code': MELHOR_ENVIO_CEP_FROM},
        'to':   {'postal_code': cep_destino.replace('-', '')},
        'products': produtos,
        'options': {
            'insurance_value': sum(p['unitary_value'] * p['quantity'] for p in produtos),
            'receipt':         False,
            'own_hand':        False,
        },
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return [{'erro': str(e)}]

    opcoes = []
    for servico in data:
        if 'error' in servico:
            continue
        opcoes.append({
            'id':           servico.get('id'),
            'nome':         servico.get('name'),
            'transportadora': servico.get('company', {}).get('name'),
            'preco':        servico.get('price'),
            'prazo':        servico.get('delivery_time'),
            'logo':         servico.get('company', {}).get('picture'),
        })

    return sorted(opcoes, key=lambda x: float(x['preco'] or 999999))