import os
import sys
import django
import random

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from clientes.models import Cliente

NOMES = [
    'Alfa Móveis', 'Beta Decorações', 'Gama Design', 'Delta Interiores',
    'Epsilon Casa', 'Zeta Ambientes', 'Eta Projetos', 'Theta Espaços',
    'Iota Soluções', 'Kappa Reformas', 'Lambda Construções', 'Mu Arquitetura',
    'Nu Engenharia', 'Xi Acabamentos', 'Omicron Revestimentos', 'Pi Materiais',
    'Rho Instalações', 'Sigma Pintura', 'Tau Elétrica', 'Upsilon Hidráulica',
    'Phi Climatização', 'Chi Automação', 'Psi Segurança', 'Omega Tecnologia',
    'Aurora Móveis', 'Boreal Design', 'Crisol Interiores', 'Duna Decorações',
    'Esfera Projetos', 'Fênix Ambientes', 'Gaia Espaços', 'Hélio Reformas',
    'Íris Construções', 'Jade Arquitetura', 'Karma Engenharia', 'Lotus Acabamentos',
    'Marte Revestimentos', 'Neon Materiais', 'Ópala Instalações', 'Prism Pintura',
]

SUFIXOS = ['Ltda', 'ME', 'EPP', 'S/A', 'EIRELI', 'SS', 'SA']

CIDADES_BR = [
    ('São Paulo', 'SP'), ('Rio de Janeiro', 'RJ'), ('Belo Horizonte', 'MG'),
    ('Curitiba', 'PR'), ('Porto Alegre', 'RS'), ('Salvador', 'BA'),
    ('Fortaleza', 'CE'), ('Manaus', 'AM'), ('Recife', 'PE'), ('Goiânia', 'GO'),
    ('Florianópolis', 'SC'), ('Vitória', 'ES'), ('Natal', 'RN'), ('Maceió', 'AL'),
    ('Campo Grande', 'MS'), ('Cuiabá', 'MT'), ('Teresina', 'PI'), ('João Pessoa', 'PB'),
]

CIDADES_INTL = [
    ('Buenos Aires', 'AR'), ('Santiago', 'CL'), ('Assunção', 'PY'),
    ('Montevidéu', 'UY'), ('Lima', 'PE'), ('Bogotá', 'CO'),
    ('Miami', 'US'), ('Lisboa', 'PT'), ('Madrid', 'ES'),
]

LOGRADOUROS = [
    'Rua das Flores', 'Av. Paulista', 'Rua do Comércio', 'Av. Brasil',
    'Rua São João', 'Av. Central', 'Rua das Acácias', 'Rua dos Ipês',
    'Av. das Nações', 'Rua Industrial', 'Av. do Contorno', 'Rua Nova',
]


def gerar_cnpj():
    def calc_digito(cnpj, pesos):
        soma = sum(int(cnpj[i]) * pesos[i] for i in range(len(pesos)))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    base = [random.randint(0, 9) for _ in range(12)]
    base[8], base[9], base[10], base[11] = 0, 0, 0, 1
    d1 = calc_digito(base, [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    d2 = calc_digito(base + [d1], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    nums = base + [d1, d2]
    return f"{''.join(map(str, nums[:2]))}.{''.join(map(str, nums[2:5]))}.{''.join(map(str, nums[5:8]))}/{''.join(map(str, nums[8:12]))}-{''.join(map(str, nums[12:]))}"


def gerar_cpf():
    def calc_digito(cpf, peso_inicial):
        soma = sum(int(cpf[i]) * (peso_inicial - i) for i in range(peso_inicial - 1))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    base = [random.randint(0, 9) for _ in range(9)]
    d1 = calc_digito(base, 10)
    d2 = calc_digito(base + [d1], 11)
    nums = base + [d1, d2]
    s = ''.join(map(str, nums))
    return f'{s[:3]}.{s[3:6]}.{s[6:9]}-{s[9:]}'


if __name__ == '__main__':
    try:
        admin = User.objects.get(username='RobertoAdmin')
    except User.DoesNotExist:
        print('Usuário RobertoAdmin não encontrado.')
        sys.exit(1)

    try:
        vendedor = User.objects.get(username='Vendedor')
    except User.DoesNotExist:
        print('Usuário Vendedor não encontrado.')
        sys.exit(1)

    criados = 0
    documentos_usados = set(
        Cliente.objects.values_list('documento', flat=True)
    )

    for usuario in [admin, vendedor]:
        for i in range(150):
            tipo_pessoa = random.choice(['PF', 'PJ'])
            internacional = random.random() < 0.1

            while True:
                doc = gerar_cpf() if tipo_pessoa == 'PF' else gerar_cnpj()
                if doc not in documentos_usados:
                    documentos_usados.add(doc)
                    break

            nome_base = random.choice(NOMES)
            if tipo_pessoa == 'PJ':
                nome = f'{nome_base} {random.choice(SUFIXOS)} {i}'
                nome_fantasia = nome_base
            else:
                nome = f'Cliente {usuario.username} {i + 1}'
                nome_fantasia = ''

            if internacional:
                cidade, pais = random.choice(CIDADES_INTL)
                estado = ''
                cep = ''
                codigo_postal = f'{random.randint(1000, 99999):05d}'
                regiao = f'Região {random.randint(1, 20)}'
            else:
                cidade, estado = random.choice(CIDADES_BR)
                pais = 'BR'
                cep = f'{random.randint(10000, 99999):05d}-{random.randint(0, 999):03d}'
                codigo_postal = ''
                regiao = ''

            Cliente.objects.create(
                tipo_pessoa=tipo_pessoa,
                nome=nome,
                nome_fantasia=nome_fantasia,
                documento=doc,
                email=f'cliente{criados + 1}@exemplo.com.br',
                telefone=f'+55119{random.randint(10000000, 99999999)}',
                whatsapp=f'+55119{random.randint(10000000, 99999999)}',
                contato=f'Contato {i + 1}',
                pais=pais,
                cep=cep,
                logradouro=random.choice(LOGRADOUROS),
                numero=str(random.randint(1, 9999)),
                bairro=f'Bairro {random.randint(1, 50)}',
                cidade=cidade,
                estado=estado,
                codigo_postal=codigo_postal,
                regiao=regiao,
                ativo=random.random() > 0.1,
                criado_por=usuario,
            )
            criados += 1

    print(f'{criados} clientes criados com sucesso!')