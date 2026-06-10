from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Cliente

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nome', 'tipo_pessoa', 'documento', 'cidade', 'estado', 'ativo']
    search_fields = ['nome', 'documento', 'codigo']
    list_filter = ['tipo_pessoa', 'ativo', 'estado']