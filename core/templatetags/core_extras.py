from django import template

register = template.Library()


@register.filter
def telefone(value):
    if not value:
        return ''
    v = ''.join(filter(str.isdigit, value))
    if len(v) == 11:
        return f'({v[0:2]}) {v[2:7]}-{v[7:11]}'
    elif len(v) == 10:
        return f'({v[0:2]}) {v[2:6]}-{v[6:10]}'
    return value


@register.filter
def documento(value):
    if not value:
        return ''
    v = ''.join(filter(str.isdigit, value))
    if len(v) == 11:
        return f'{v[0:3]}.{v[3:6]}.{v[6:9]}-{v[9:11]}'
    elif len(v) == 14:
        return f'{v[0:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:14]}'
    return value


@register.filter
def moeda(value):
    if value is None:
        return 'R$ 0,00'
    try:
        value = float(value)
        formatted = f'{value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
        return f'R$ {formatted}'
    except (ValueError, TypeError):
        return 'R$ 0,00'


@register.filter
def unidade_abrev(produto):
    abreviacoes = {
        'un': 'un',
        'kg': 'kg',
        'g': 'g',
        'm': 'm',
        'm2': 'm²',
        'cm': 'cm',
        'l': 'L',
        'ml': 'mL',
        'cx': 'cx',
        'pct': 'pct',
        'chp': 'un',
        'rolo': 'rolo',
        'tubo': 'tubo',
    }
    return abreviacoes.get(produto.unidade_medida, produto.unidade_medida)

@register.filter
def formato_telefone(numero):
    if not numero:
        return ''

    if numero.startswith('+'):
        digitos = ''.join(filter(str.isdigit, numero))

        # Brasil: +55 11 99999-9999
        if digitos.startswith('55') and len(digitos) == 13:
            n = digitos[2:]
            return f'({n[:2]}) {n[2:7]}-{n[7:]}'

        # EUA/Canadá: +1 (201) 111-1118
        if digitos.startswith('1') and len(digitos) == 11:
            n = digitos[1:]
            return f'+1 ({n[:3]}) {n[3:6]}-{n[6:]}'

        # Argentina: +54 11 1234-5678
        if digitos.startswith('54') and len(digitos) == 12:
            n = digitos[2:]
            return f'+54 ({n[:2]}) {n[2:6]}-{n[6:]}'

        # Chile: +56 9 1234-5678
        if digitos.startswith('56') and len(digitos) == 11:
            n = digitos[2:]
            return f'+56 {n[:1]} {n[1:5]}-{n[5:]}'

        # Outros — exibe como veio
        return numero

    # Sem DDI — tenta BR
    digitos = ''.join(filter(str.isdigit, numero))
    if len(digitos) == 11:
        return f'({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}'
    elif len(digitos) == 10:
        return f'({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}'

    return numero