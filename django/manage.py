#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import warnings

import dotenv


def main() -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings(
            'ignore', category=UserWarning, message=r"^Not reading.+ - it doesn't exist\.$"
        )
        dotenv.read_dotenv()

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joist.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            'available on your PYTHONPATH environment variable? Did you '
            'forget to activate a virtual environment?'
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
