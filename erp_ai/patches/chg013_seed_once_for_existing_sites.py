"""CHG-013: a site that already had the app gets the data seed once.

A new site gets it from `after_install`; Frappe marks every patch done on a fresh install, so this runs
only on existing sites. After it, `after_migrate` never seeds data again. Fills only what is missing.
"""

from erp_ai import install


def execute():
	install.seed_once()
	install._mark_agent_enabled_at()
