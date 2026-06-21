"""GreenRoute HTTP route handlers.

Public submodules
-----------------
- appliance : GET /api/appliances, POST /api/appliances/estimate
- ask       : POST /api/ask  (follow-up AI assistant)
- compare   : POST /api/compare  (commute mode comparison)
- logs      : POST /api/log/commute, POST /api/log/appliance
- stats     : GET /api/stats/weekly
"""

__all__ = ["appliance", "ask", "compare", "logs", "stats"]
