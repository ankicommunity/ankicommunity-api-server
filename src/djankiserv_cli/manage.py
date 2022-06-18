#!/usr/bin/env python
"""Django's command-line utility for administrative tasks.

This should typically always be used via the djankiserv cli. However,
a manage.py is maintained to follow django convension and for legacy reasons.

This may be removed in the future if not needed.
"""

import os
import sys

from django.core.management import execute_from_command_line


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djankiserv_api.settings")
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
