from django.apps import AppConfig


class JoistConfig(AppConfig):
    name = 'joist'

    def ready(self):
        from . import checks
