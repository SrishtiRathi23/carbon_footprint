"""GreenRoute services: external API clients and data persistence.

Public submodules
-----------------
- firestore_client : Firestore reads/writes (logs + weekly totals)
- gemini_client    : Gemini tip generation and follow-up Q&A
- maps_client      : Google Maps Routes API (parallel mode fetch)
"""

__all__ = ["firestore_client", "gemini_client", "maps_client"]
