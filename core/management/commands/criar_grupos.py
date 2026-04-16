from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Cria os grupos de usuários do sistema'

    def handle(self, *args, **kwargs):
        # ── Gerente ──
        gerente, _ = Group.objects.get_or_create(name='Gerente')
        # Somente leitura — sem permissões de escrita

        # ── Estoquista ──
        estoquista, _ = Group.objects.get_or_create(name='Estoquista')

        # ── Logística ──
        logistica, _ = Group.objects.get_or_create(name='Logística')
        # Somente leitura — sem permissões de escrita

        self.stdout.write(self.style.SUCCESS('Grupos criados com sucesso!'))
        self.stdout.write('  ✓ Gerente')
        self.stdout.write('  ✓ Estoquista')
        self.stdout.write('  ✓ Logística')