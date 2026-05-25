"""Legacy compatibility module.

Prefer importing from `config.settings` for new code.
This file stays so older imports continue to work during the migration.
"""

from config.settings import *  # noqa: F401,F403

