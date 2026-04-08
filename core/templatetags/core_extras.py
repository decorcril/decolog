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