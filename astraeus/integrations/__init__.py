"""
External integrations for Astraeus Apertura.

Provides interfaces to external services like Notion, Airtable, and other databases
for parameter management and data exchange.
"""

from .notion_integration import NotionClient, NotionDatabase, NotionPage

__all__ = [
    'NotionClient',
    'NotionDatabase',
    'NotionPage',
]
