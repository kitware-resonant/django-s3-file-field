import django
import pytest


# Session scope, as execution has global state side effects
@pytest.fixture(scope='session')
def django_settings_init() -> None:
    """Make Django settings available for reading, without initializing Django apps."""
    from django.conf import settings

    settings.configure()
    django.setup()
