"""Google Docs adapter with direct API access."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from portals.core.adapter import DocumentAdapter
from portals.adapters.gdocs.converter import GoogleDocsConverter


SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.readonly'
]


class GoogleDocsAdapter(DocumentAdapter):
    """Adapter for Google Docs with full formatting support.

    Uses direct Google Docs API access for full control over formatting,
    bypassing MCP tool limitations.
    """

    def __init__(
        self,
        credentials_path: str | None = None,
        token_path: str | None = None
    ):
        """Initialize Google Docs adapter.

        Args:
            credentials_path: Path to OAuth2 credentials file
            token_path: Path to store OAuth2 token
        """
        self.credentials_path = credentials_path or os.path.expanduser(
            "~/.config/docsync/google_credentials.json"
        )
        self.token_path = token_path or os.path.expanduser(
            "~/.config/docsync/google_token.json"
        )

        self.converter = GoogleDocsConverter()
        self._service = None
        self._drive_service = None

    @property
    def service(self):
        """Lazy-load Google Docs service."""
        if self._service is None:
            creds = self._get_credentials()
            self._service = build('docs', 'v1', credentials=creds)
        return self._service

    @property
    def drive_service(self):
        """Lazy-load Google Drive service."""
        if self._drive_service is None:
            creds = self._get_credentials()
            self._drive_service = build('drive', 'v3', credentials=creds)
        return self._drive_service

    def _get_credentials(self) -> Credentials:
        """Get Google API credentials.

        Returns:
            Credentials object
        """
        creds = None

        # Load existing token
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        # Refresh or create new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Google credentials not found at {self.credentials_path}. "
                        "Please download OAuth2 credentials from Google Cloud Console."
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials
            os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())

        return creds

    def read(self, remote_id: str) -> dict[str, Any]:
        """Read document from Google Docs.

        Args:
            remote_id: Google Docs document ID

        Returns:
            Document metadata and content
        """
        try:
            # Get document
            doc = self.service.documents().get(documentId=remote_id).execute()

            # Extract content
            content = self._extract_content(doc)

            # Get metadata from Drive
            drive_file = self.drive_service.files().get(
                fileId=remote_id,
                fields='id,name,modifiedTime,createdTime'
            ).execute()

            return {
                'id': remote_id,
                'title': doc.get('title', ''),
                'content': content,
                'modified_time': drive_file.get('modifiedTime'),
                'created_time': drive_file.get('createdTime'),
            }

        except HttpError as e:
            raise RuntimeError(f"Failed to read Google Doc {remote_id}: {e}")

    def write(self, remote_id: str | None, content: str, title: str | None = None) -> str:
        """Write document to Google Docs with full formatting.

        Args:
            remote_id: Document ID (None to create new)
            content: Markdown content
            title: Document title

        Returns:
            Document ID
        """
        if remote_id is None:
            # Create new document
            return self._create_document(title or "Untitled", content)
        else:
            # Update existing document
            self._update_document(remote_id, content)
            return remote_id

    def delete(self, remote_id: str) -> None:
        """Delete document from Google Docs.

        Args:
            remote_id: Document ID
        """
        try:
            self.drive_service.files().delete(fileId=remote_id).execute()
        except HttpError as e:
            raise RuntimeError(f"Failed to delete Google Doc {remote_id}: {e}")

    def list_documents(self, folder_id: str | None = None) -> list[dict[str, Any]]:
        """List Google Docs.

        Args:
            folder_id: Optional folder ID to filter by

        Returns:
            List of document metadata
        """
        try:
            query = "mimeType='application/vnd.google-apps.document'"
            if folder_id:
                query += f" and '{folder_id}' in parents"

            results = self.drive_service.files().list(
                q=query,
                fields='files(id,name,modifiedTime,createdTime)',
                orderBy='modifiedTime desc'
            ).execute()

            files = results.get('files', [])

            return [
                {
                    'id': f['id'],
                    'title': f['name'],
                    'modified_time': f.get('modifiedTime'),
                    'created_time': f.get('createdTime'),
                }
                for f in files
            ]

        except HttpError as e:
            raise RuntimeError(f"Failed to list Google Docs: {e}")

    def _create_document(self, title: str, content: str) -> str:
        """Create new Google Doc with formatting.

        Args:
            title: Document title
            content: Markdown content

        Returns:
            Document ID
        """
        try:
            # Create empty document
            doc = self.service.documents().create(body={'title': title}).execute()
            doc_id = doc['documentId']

            # Convert markdown
            result = self.converter.markdown_to_gdocs(content)

            # Build requests
            requests = []

            # 1. Insert plain text
            requests.append({
                'insertText': {
                    'location': {'index': 1},
                    'text': result.plain_text
                }
            })

            # 2. Apply formatting
            requests.extend(self.converter.generate_batch_requests(result))

            # Execute batch update
            self.service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()

            return doc_id

        except HttpError as e:
            raise RuntimeError(f"Failed to create Google Doc: {e}")

    def _update_document(self, doc_id: str, content: str) -> None:
        """Update existing Google Doc with formatting.

        Args:
            doc_id: Document ID
            content: Markdown content
        """
        try:
            # Get current document
            doc = self.service.documents().get(documentId=doc_id).execute()
            doc_length = doc['body']['content'][-1]['endIndex'] - 1

            # Convert markdown
            result = self.converter.markdown_to_gdocs(content)

            # Build requests
            requests = []

            # 1. Delete existing content
            if doc_length > 0:
                requests.append({
                    'deleteContentRange': {
                        'range': {
                            'startIndex': 1,
                            'endIndex': doc_length + 1
                        }
                    }
                })

            # 2. Insert new plain text
            requests.append({
                'insertText': {
                    'location': {'index': 1},
                    'text': result.plain_text
                }
            })

            # 3. Apply formatting
            requests.extend(self.converter.generate_batch_requests(result))

            # Execute batch update
            self.service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()

        except HttpError as e:
            raise RuntimeError(f"Failed to update Google Doc {doc_id}: {e}")

    def _extract_content(self, doc: dict[str, Any]) -> str:
        """Extract plain text content from Google Doc.

        Args:
            doc: Document object from API

        Returns:
            Plain text content
        """
        content = []

        for element in doc.get('body', {}).get('content', []):
            if 'paragraph' in element:
                para = element['paragraph']
                for el in para.get('elements', []):
                    if 'textRun' in el:
                        content.append(el['textRun']['content'])

        return ''.join(content)
