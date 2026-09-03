from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from core.models.perfil_vendedor import PerfilVendedor
from core.models import Local


class PerfilVendedorInline(admin.StackedInline):
    model = PerfilVendedor
    can_delete = False
    verbose_name_plural = 'Perfil do Vendedor (Loja)'
    fk_name = 'user'


class UserAdmin(DjangoUserAdmin):
    inlines = (PerfilVendedorInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Local)
class LocalAdmin(admin.ModelAdmin):
    list_display  = ['nome', 'tipo', 'ativo']
    list_filter   = ['tipo', 'ativo']
    search_fields = ['nome']