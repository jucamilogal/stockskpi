# core/management/commands/clearcache.py
from django.core.cache import cache
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Limpia la caché de Django."
    def handle(self, *args, **kwargs):
        cache.clear()
        self.stdout.write(self.style.SUCCESS("Caché limpiada."))
