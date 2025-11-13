# Google Docs Formatting Analysis

**Date**: 2025-11-13
**Test Document**: https://docs.google.com/document/d/1EFprGxMNEbBBeSTzMbyozWnNcxxQ3QcL4r3RehcC4so/edit

---

## Current State: MCP `create_doc` Tool

### What It Does
The MCP `create_doc` tool accepts markdown content but treats it as **plain text** - it does NOT parse or format it.

### Test Results

**Input** (markdown):
```markdown
# Q4 Strategy Memo

**Date**: November 2025

## Executive Summary

We expect **30% growth** in Q4, driven by:

- New product launches
- Expanded market reach
```

**Output** (Google Docs):
```
# Q4 Strategy Memo

**Date**: November 2025

## Executive Summary

We expect **30% growth** in Q4, driven by:

- New product launches
- Expanded market reach
```

**Issues Found**:
1. ❌ Headings (`#`, `##`) remain as text symbols, not styled as Heading 1, Heading 2
2. ❌ Bold (`**text**`) remains as asterisks, not actually bold
3. ❌ Lists (`-`) remain as plain text with dashes, not formatted as bullets
4. ❌ Numbered lists stay as plain text
5. ❌ Every paragraph is just "Normal Text" style

**Result**: Document is NOT distribution-ready - looks like raw markdown.

---

## Why This Happens

The MCP `create_doc` tool signature:
```python
mcp__google-workspace__create_doc(
    user_google_email: str,
    title: str,
    content: str  # <-- Just plain text, no formatting
)
```

It simply:
1. Creates an empty Google Doc
2. Inserts the content as plain text
3. Returns the document ID

It does **NOT**:
- Parse markdown syntax
- Apply styles (headings, bold, italic)
- Format lists
- Handle any markdown features

---

## What We Need to Build

A proper **Markdown → Google Docs Converter** that:

### 1. Parses Markdown
Use a proper markdown parser (like `mistletoe` or `markdown-it-py`) to:
- Identify heading levels
- Find bold/italic text ranges
- Detect list items and nesting
- Parse links, code blocks, etc.

### 2. Converts to Google Docs Batch Requests
Google Docs API uses batch update requests with specific operations:

```python
# Example: Convert "# Heading" to Heading 1
{
    "updateParagraphStyle": {
        "range": {"startIndex": 1, "endIndex": 10},
        "paragraphStyle": {"namedStyleType": "HEADING_1"},
        "fields": "namedStyleType"
    }
}

# Example: Convert "**bold**" to bold text
{
    "updateTextStyle": {
        "range": {"startIndex": 20, "endIndex": 24},
        "textStyle": {"bold": True},
        "fields": "bold"
    }
}

# Example: Convert "- item" to bullet list
{
    "createParagraphBullets": {
        "range": {"startIndex": 30, "endIndex": 40},
        "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"
    }
}
```

### 3. Applies Formatting in Correct Order

**Critical**: Google Docs API is index-based, so order matters:

1. Insert plain text first (no markdown symbols)
2. Apply paragraph styles (headings, normal)
3. Apply text styles (bold, italic)
4. Apply list formatting
5. Handle special cases (links, code)

---

## Required MCP Tools

To build proper formatting, we need these MCP tools:

### ✅ Available & Tested
- `mcp__google-workspace__create_doc` - Create empty doc
- `mcp__google-workspace__inspect_doc_structure` - Read doc structure

### 📋 Need to Use
- `mcp__google-workspace__modify_doc_text` - Update text and apply formatting
- `mcp__google-workspace__batch_update_doc` - Apply multiple format operations
- `mcp__google-workspace__insert_doc_elements` - Add tables, lists, page breaks

### 📋 Nice to Have
- `mcp__google-workspace__find_and_replace_doc` - Text operations
- `mcp__google-workspace__insert_doc_image` - Image support (future)

---

## Conversion Strategy

### Step 1: Parse Markdown
```python
import mistletoe
from mistletoe import Document

# Parse markdown
with open('memo.md', 'r') as f:
    doc = Document(f.read())

# Walk the AST
for element in doc.children:
    if isinstance(element, Heading):
        # Track: Heading level, text, position
    elif isinstance(element, Paragraph):
        # Track: Text, inline formatting (bold, italic)
    elif isinstance(element, List):
        # Track: List items, nesting level, ordered/unordered
```

### Step 2: Build Plain Text + Format Map
```python
# Output plain text (no markdown symbols)
plain_text = "Q4 Strategy Memo\n\nDate: November 2025\n\n..."

# Build format map
format_operations = [
    {
        "type": "heading",
        "level": 1,
        "start_index": 1,
        "end_index": 18,
        "text": "Q4 Strategy Memo"
    },
    {
        "type": "bold",
        "start_index": 20,
        "end_index": 25,
        "text": "Date"
    },
    ...
]
```

### Step 3: Create Doc & Apply Formatting
```python
# Create empty doc
doc_id = create_doc(title="Q4 Strategy Memo", content=plain_text)

# Build batch update requests
batch_requests = []
for op in format_operations:
    if op["type"] == "heading":
        batch_requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": op["start_index"], "endIndex": op["end_index"]},
                "paragraphStyle": {"namedStyleType": f"HEADING_{op['level']}"},
                "fields": "namedStyleType"
            }
        })
    elif op["type"] == "bold":
        batch_requests.append({
            "updateTextStyle": {
                "range": {"startIndex": op["start_index"], "endIndex": op["end_index"]},
                "textStyle": {"bold": True},
                "fields": "bold"
            }
        })
    # ... etc

# Apply all formatting
batch_update_doc(doc_id, batch_requests)
```

---

## Example: Perfect Output

**Input Markdown**:
```markdown
# Q4 Strategy Memo

**Date**: November 2025

## Financial Projections

We expect **30% growth** in Q4, driven by:

- New product launches
- Expanded market reach
- Improved conversion rates
```

**Expected Google Docs Output**:

```
Q4 Strategy Memo                    [Heading 1, large font]

Date: November 2025                 [Date bold, rest normal]

Financial Projections               [Heading 2, medium font]

We expect 30% growth in Q4,         [30% growth bold, rest normal]
driven by:

• New product launches              [Bullet list, proper indent]
• Expanded market reach             [Bullet list, proper indent]
• Improved conversion rates         [Bullet list, proper indent]
```

**Key Features**:
- ✅ Headings use Google Docs heading styles (not just large text)
- ✅ Bold text is actually bold (not asterisks)
- ✅ Lists use native Google Docs bullets (not dashes)
- ✅ Proper spacing between elements
- ✅ Distribution-ready without manual edits

---

## Implementation Plan

### Phase 1: Basic Converter (Day 1-2)
**Goal**: Support headings, bold, italic, lists

**Files**:
- `portals/adapters/gdocs/converter.py`
- `portals/adapters/gdocs/markdown_parser.py`

**Test**: Sample memo → Google Docs → Should be distribution-ready

### Phase 2: Google Docs Adapter (Day 2-3)
**Goal**: Full DocumentAdapter implementation

**Files**:
- `portals/adapters/gdocs/adapter.py`
- `portals/adapters/gdocs/mcp_client.py`

**Test**: Read/write operations with proper formatting

### Phase 3: Advanced Features (Day 3-4)
**Goal**: Tables, code blocks, links

**Optional Enhancements**:
- Images (if needed)
- Comments/suggestions
- Custom styles

---

## Success Criteria

A conversion is **successful** when:

1. ✅ All headings styled correctly (H1, H2, H3)
2. ✅ Bold/italic text formatted (no asterisks visible)
3. ✅ Bullet lists use native bullets (not dashes)
4. ✅ Numbered lists use native numbering (not "1.", "2.")
5. ✅ Proper spacing (not random line skips)
6. ✅ Links are clickable (not [text](url))
7. ✅ Code blocks formatted correctly
8. ✅ Document is distribution-ready (no manual edits needed)

**Quality Bar**: Roman can push to Google Docs and immediately share with Christof without any formatting fixes.

---

## Next Steps

1. ✅ **Tested current state** - Confirmed no formatting applied
2. 📋 **Choose markdown parser** - Evaluate options
3. 📋 **Build converter prototype** - Basic headings + bold
4. 📋 **Test with sample memo** - Verify formatting quality
5. 📋 **Iterate** - Add lists, links, etc.
6. 📋 **Full adapter** - Complete DocumentAdapter implementation

---

## Technical Notes

### Index Management
Google Docs is index-based (like a giant string):
- Index 0: Section break
- Index 1: First character
- Formatting ranges are `[startIndex, endIndex)`
- Insertions shift all subsequent indices

**Key Challenge**: Must track indices carefully when building batch requests.

### Batch Update Benefits
- Single API call for all formatting
- Atomic operation (all or nothing)
- More efficient than individual updates

### MCP Tool Limitations
- `create_doc` doesn't support initial formatting (we'll add it after)
- `modify_doc_text` might have limits on batch size
- May need multiple batch updates for large documents

---

## Related Documents

- `/01-context/2025-11-13_PHASE_7_PLAN.md` - Overall Phase 7 plan
- Test document: https://docs.google.com/document/d/1EFprGxMNEbBBeSTzMbyozWnNcxxQ3QcL4r3RehcC4so/edit

---

**Status**: Analysis complete, ready to build converter
**Next**: Choose markdown parser and start implementation
