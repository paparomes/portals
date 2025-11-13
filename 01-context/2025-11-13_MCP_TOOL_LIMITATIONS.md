# MCP Google Docs Tool Limitations

**Date**: 2025-11-13
**Issue**: MCP batch_update_doc doesn't support paragraph styling

---

## Problem

The MCP `batch_update_doc` tool has limited operation support. It does NOT support:
- `updateParagraphStyle` - Cannot apply heading styles (H1, H2, H3)
- `createParagraphBullets` - Cannot create bullet/numbered lists
- Full Google Docs API operations

## Test Results

**Error when trying to apply heading style**:
```
Error: Batch operation failed: Operation 1: Unsupported operation type: updateParagraphStyle
```

**Supported operations** (from tool description):
- `insert_text`
- `delete_text`
- `replace_text`
- `format_text` (bold, italic, font, etc.)
- `insert_table`
- `insert_page_break`

**NOT supported**:
- `updateParagraphStyle` - Heading styles, alignment, spacing
- `createParagraphBullets` - List formatting
- Other advanced paragraph operations

## Impact

This means the MCP tools cannot create distribution-ready documents with:
- Proper heading styles (H1, H2, H3)
- Native bullet lists
- Native numbered lists
- Advanced paragraph formatting

## Solution

We need to implement direct Google Docs API access in the GoogleDocsAdapter instead of relying solely on MCP tools.

### Approach

1. **Use MCP for document discovery/listing**
   - `search_docs`, `list_docs`, `get_doc_content` work fine

2. **Use direct Google Docs API for write operations**
   - Create docs
   - Apply full formatting (headings, lists, etc.)
   - Full batch update support

3. **GoogleDocsAdapter implementation**
```python
class GoogleDocsAdapter(DocumentAdapter):
    def __init__(self):
        # Use google-api-python-client directly
        self.service = build('docs', 'v1', credentials=creds)
        self.converter = GoogleDocsConverter()

    def create_document(self, title: str, content: str) -> str:
        # Create doc
        doc = self.service.documents().create(body={'title': title}).execute()
        doc_id = doc['documentId']

        # Convert markdown
        result = self.converter.markdown_to_gdocs(content)

        # Insert plain text
        requests = [{
            'insertText': {
                'location': {'index': 1},
                'text': result.plain_text
            }
        }]

        # Apply all formatting (headings, bold, lists, etc.)
        requests.extend(self.converter.generate_batch_requests(result))

        # Execute batch update
        self.service.documents().batchUpdate(
            documentId=doc_id,
            body={'requests': requests}
        ).execute()

        return doc_id
```

## Next Steps

1. ✅ Documented MCP limitation
2. 📋 Implement GoogleDocsAdapter with direct API access
3. 📋 Use Google Workspace MCP auth (already set up)
4. 📋 Test full formatting pipeline
5. 📋 Integrate with docsync CLI

---

**Key Takeaway**: MCP tools are great for reading/discovery, but we need direct API access for full write/formatting capabilities.
