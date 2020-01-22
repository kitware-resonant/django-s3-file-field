from django.apps import AppConfig


class JoistConfig(AppConfig):
    name = 'joist'

    def ready(self):
        # import checks to register them
        from . import checks  # noqa: F401
