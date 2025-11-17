"""
Notion database integration for antenna design parameters.

Provides interface to Notion databases for:
- Fetching mission requirements
- Loading design parameters
- Storing simulation results
- Tracking design iterations
"""

import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from loguru import logger


@dataclass
class NotionPage:
    """
    Represents a Notion page/row in a database.

    Attributes:
        page_id: Notion page ID
        properties: Dictionary of page properties
        created_time: When page was created
        last_edited_time: When page was last edited
    """
    page_id: str
    properties: Dict[str, Any]
    created_time: Optional[datetime] = None
    last_edited_time: Optional[datetime] = None

    def get_property(self, property_name: str, default: Any = None) -> Any:
        """
        Get property value from Notion page.

        Args:
            property_name: Name of the property
            default: Default value if property not found

        Returns:
            Property value
        """
        return self.properties.get(property_name, default)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'page_id': self.page_id,
            'properties': self.properties,
            'created_time': self.created_time.isoformat() if self.created_time else None,
            'last_edited_time': self.last_edited_time.isoformat() if self.last_edited_time else None,
        }


class NotionDatabase:
    """
    Represents a Notion database with antenna design data.

    Provides methods to query and manipulate Notion database content.
    """

    def __init__(self, client: 'NotionClient', database_id: str):
        """
        Initialize Notion database.

        Args:
            client: NotionClient instance
            database_id: Notion database ID
        """
        self.client = client
        self.database_id = database_id
        logger.info(f"Initialized Notion database: {database_id}")

    def query(
        self,
        filter_conditions: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, str]]] = None,
        limit: Optional[int] = None
    ) -> List[NotionPage]:
        """
        Query database for pages matching conditions.

        Args:
            filter_conditions: Notion filter object
            sorts: List of sort conditions
            limit: Maximum number of results

        Returns:
            List of NotionPage objects
        """
        return self.client.query_database(
            self.database_id,
            filter_conditions=filter_conditions,
            sorts=sorts,
            limit=limit
        )

    def get_all(self, limit: Optional[int] = 100) -> List[NotionPage]:
        """
        Get all pages from database.

        Args:
            limit: Maximum number of pages

        Returns:
            List of NotionPage objects
        """
        return self.query(limit=limit)

    def get_page(self, page_id: str) -> Optional[NotionPage]:
        """
        Get a specific page by ID.

        Args:
            page_id: Notion page ID

        Returns:
            NotionPage or None if not found
        """
        return self.client.get_page(page_id)

    def create_page(self, properties: Dict[str, Any]) -> NotionPage:
        """
        Create a new page in the database.

        Args:
            properties: Page properties

        Returns:
            Created NotionPage
        """
        return self.client.create_page(self.database_id, properties)

    def update_page(self, page_id: str, properties: Dict[str, Any]) -> NotionPage:
        """
        Update an existing page.

        Args:
            page_id: Page ID to update
            properties: Updated properties

        Returns:
            Updated NotionPage
        """
        return self.client.update_page(page_id, properties)


class NotionClient:
    """
    Client for interacting with Notion API.

    Handles authentication, requests, and response parsing for
    antenna design parameter management in Notion.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Notion client.

        Args:
            api_key: Notion integration token (reads from NOTION_API_KEY env if not provided)
        """
        self.api_key = api_key or os.getenv('NOTION_API_KEY')

        if not self.api_key:
            raise ValueError("Notion API key not provided. Set NOTION_API_KEY environment variable.")

        try:
            from notion_client import Client
            self.client = Client(auth=self.api_key)
            logger.info("Initialized Notion client")
        except ImportError:
            raise ImportError("notion-client package not installed. Install with: pip install notion-client")

    def get_database(self, database_id: str) -> NotionDatabase:
        """
        Get a Notion database interface.

        Args:
            database_id: Notion database ID

        Returns:
            NotionDatabase instance
        """
        return NotionDatabase(self, database_id)

    def query_database(
        self,
        database_id: str,
        filter_conditions: Optional[Dict[str, Any]] = None,
        sorts: Optional[List[Dict[str, str]]] = None,
        limit: Optional[int] = None
    ) -> List[NotionPage]:
        """
        Query a Notion database.

        Args:
            database_id: Database ID
            filter_conditions: Notion filter object
            sorts: Sort conditions
            limit: Maximum results

        Returns:
            List of NotionPage objects
        """
        try:
            query_params = {}

            if filter_conditions:
                query_params['filter'] = filter_conditions

            if sorts:
                query_params['sorts'] = sorts

            if limit:
                query_params['page_size'] = min(limit, 100)  # Notion max is 100

            response = self.client.databases.query(
                database_id=database_id,
                **query_params
            )

            pages = []
            for result in response.get('results', []):
                page = self._parse_page(result)
                pages.append(page)

            logger.info(f"Retrieved {len(pages)} pages from database {database_id}")
            return pages

        except Exception as e:
            logger.error(f"Failed to query Notion database: {e}")
            return []

    def get_page(self, page_id: str) -> Optional[NotionPage]:
        """
        Get a specific page by ID.

        Args:
            page_id: Page ID

        Returns:
            NotionPage or None
        """
        try:
            response = self.client.pages.retrieve(page_id=page_id)
            return self._parse_page(response)

        except Exception as e:
            logger.error(f"Failed to get Notion page {page_id}: {e}")
            return None

    def create_page(self, database_id: str, properties: Dict[str, Any]) -> NotionPage:
        """
        Create a new page in a database.

        Args:
            database_id: Parent database ID
            properties: Page properties in Notion format

        Returns:
            Created NotionPage
        """
        try:
            response = self.client.pages.create(
                parent={"database_id": database_id},
                properties=properties
            )

            page = self._parse_page(response)
            logger.info(f"Created Notion page: {page.page_id}")
            return page

        except Exception as e:
            logger.error(f"Failed to create Notion page: {e}")
            raise

    def update_page(self, page_id: str, properties: Dict[str, Any]) -> NotionPage:
        """
        Update an existing page.

        Args:
            page_id: Page ID to update
            properties: Updated properties

        Returns:
            Updated NotionPage
        """
        try:
            response = self.client.pages.update(
                page_id=page_id,
                properties=properties
            )

            page = self._parse_page(response)
            logger.info(f"Updated Notion page: {page.page_id}")
            return page

        except Exception as e:
            logger.error(f"Failed to update Notion page: {e}")
            raise

    def _parse_page(self, page_data: Dict[str, Any]) -> NotionPage:
        """
        Parse Notion API response into NotionPage.

        Args:
            page_data: Raw page data from Notion API

        Returns:
            NotionPage object
        """
        page_id = page_data.get('id', '')
        properties = self._parse_properties(page_data.get('properties', {}))

        created_time = None
        if page_data.get('created_time'):
            try:
                created_time = datetime.fromisoformat(page_data['created_time'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass

        last_edited_time = None
        if page_data.get('last_edited_time'):
            try:
                last_edited_time = datetime.fromisoformat(page_data['last_edited_time'].replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass

        return NotionPage(
            page_id=page_id,
            properties=properties,
            created_time=created_time,
            last_edited_time=last_edited_time
        )

    def _parse_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse Notion properties into simple key-value pairs.

        Args:
            properties: Raw properties from Notion API

        Returns:
            Simplified properties dictionary
        """
        parsed = {}

        for key, value in properties.items():
            prop_type = value.get('type')

            if prop_type == 'title':
                parsed[key] = self._extract_text(value.get('title', []))
            elif prop_type == 'rich_text':
                parsed[key] = self._extract_text(value.get('rich_text', []))
            elif prop_type == 'number':
                parsed[key] = value.get('number')
            elif prop_type == 'select':
                select = value.get('select')
                parsed[key] = select.get('name') if select else None
            elif prop_type == 'multi_select':
                parsed[key] = [item['name'] for item in value.get('multi_select', [])]
            elif prop_type == 'date':
                date_obj = value.get('date')
                parsed[key] = date_obj.get('start') if date_obj else None
            elif prop_type == 'checkbox':
                parsed[key] = value.get('checkbox', False)
            elif prop_type == 'url':
                parsed[key] = value.get('url')
            elif prop_type == 'email':
                parsed[key] = value.get('email')
            elif prop_type == 'phone_number':
                parsed[key] = value.get('phone_number')
            elif prop_type == 'formula':
                formula = value.get('formula', {})
                parsed[key] = formula.get('number') or formula.get('string') or formula.get('boolean')
            elif prop_type == 'relation':
                parsed[key] = [rel['id'] for rel in value.get('relation', [])]
            elif prop_type == 'rollup':
                rollup = value.get('rollup', {})
                parsed[key] = rollup.get('number') or rollup.get('array')
            else:
                # Store raw value for unknown types
                parsed[key] = value

        return parsed

    def _extract_text(self, rich_text_array: List[Dict[str, Any]]) -> str:
        """
        Extract plain text from Notion rich text array.

        Args:
            rich_text_array: Notion rich text array

        Returns:
            Plain text string
        """
        return ''.join(item.get('plain_text', '') for item in rich_text_array)

    def create_antenna_requirements_page(
        self,
        database_id: str,
        mission_name: str,
        frequency_ghz: float,
        gain_dbi: float,
        beamwidth_deg: Optional[float] = None,
        polarization: str = "Linear",
        application: str = "",
        **kwargs
    ) -> NotionPage:
        """
        Create a page with antenna requirements in standardized format.

        Args:
            database_id: Notion database ID
            mission_name: Name of the mission
            frequency_ghz: Operating frequency in GHz
            gain_dbi: Required gain in dBi
            beamwidth_deg: Required beamwidth in degrees
            polarization: Polarization type
            application: Application description
            **kwargs: Additional properties

        Returns:
            Created NotionPage
        """
        properties = {
            "Name": {
                "title": [{"text": {"content": mission_name}}]
            },
            "Frequency (GHz)": {
                "number": frequency_ghz
            },
            "Gain (dBi)": {
                "number": gain_dbi
            },
            "Polarization": {
                "select": {"name": polarization}
            },
        }

        if beamwidth_deg:
            properties["Beamwidth (deg)"] = {"number": beamwidth_deg}

        if application:
            properties["Application"] = {
                "rich_text": [{"text": {"content": application}}]
            }

        # Add any additional properties
        for key, value in kwargs.items():
            if isinstance(value, str):
                properties[key] = {"rich_text": [{"text": {"content": value}}]}
            elif isinstance(value, (int, float)):
                properties[key] = {"number": value}
            elif isinstance(value, bool):
                properties[key] = {"checkbox": value}

        return self.create_page(database_id, properties)

    def fetch_antenna_parameters(self, database_id: str) -> List[Dict[str, Any]]:
        """
        Fetch antenna design parameters from Notion database.

        Converts Notion pages to standardized parameter dictionaries
        suitable for antenna design workflow.

        Args:
            database_id: Notion database ID

        Returns:
            List of parameter dictionaries
        """
        pages = self.query_database(database_id)

        parameters = []
        for page in pages:
            params = {
                'notion_page_id': page.page_id,
                'created_time': page.created_time,
                'last_edited_time': page.last_edited_time,
            }

            # Extract standard parameters
            params.update(page.properties)

            parameters.append(params)

        logger.info(f"Fetched {len(parameters)} antenna parameter sets from Notion")
        return parameters


def create_notion_client(api_key: Optional[str] = None) -> NotionClient:
    """
    Factory function to create Notion client.

    Args:
        api_key: Optional API key (uses env variable if not provided)

    Returns:
        NotionClient instance
    """
    return NotionClient(api_key)
