from django.core.management.base import BaseCommand
from django.core.cache import cache, caches
from django.conf import settings

class Command(BaseCommand):
    help = "Limpia el caché de Django. Por defecto limpia el 'default'. Usa --all para limpiar todos los alias definidos en CACHES."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Limpia todos los alias de caché definidos en settings.CACHES",
        )

    def handle(self, *args, **options):
        cleared = []

        if options.get("all"):
            # Limpiar todos los alias definidos en settings.CACHES
            for alias in getattr(settings, "CACHES", {}).keys():
                caches[alias].clear()
                cleared.append(alias)
        else:
            # Limpiar solo el alias 'default'
            cache.clear()
            cleared.append("default")

        self.stdout.write(self.style.SUCCESS(f"Caché limpiado: {', '.join(cleared)}"))