"""Allow ``python -m docket``."""

import sys

from .cli import main

sys.exit(main())
