# Portals (DocSync)

**Code name**: Portals
**Official name**: DocSync

Multi-platform document synchronization tool for keeping local markdown files in sync with Notion, Google Docs, and Obsidian.

**Status**: Planning phase
**Created**: 2025-11-11
**Notion team space**: Portals

---

## What is this?

DocSync solves the problem of working with documents across multiple platforms. Instead of manually copying content between your local markdown files, Notion pages, Google Docs, and Obsidian vault, DocSync keeps them synchronized automatically.

### Primary use case

Keep your entire `~/Documents/Claude Code/` directory synced with Notion for work and business documentation.

---

## Three operating modes

### 1. Mirror mode (Notion)
**Entire directory ↔ Notion team space**

Perfect for keeping all your Claude Code projects synced with the Portals team space in Notion. Set it up once, let it watch for changes, and work seamlessly in either place.

**Notion structure**:
- Each folder → Notion page in Portals team space
- Each subfolder → Child page
- Each markdown file → Child page
- Preserves full directory hierarchy

```bash
cd ~/Documents/Claude\ Code/
docsync init notion-mirror --teamspace=portals
docsync watch  # Keeps everything in sync
```

### 2. Pair mode (Google Docs)
**Selective document pairing**

Need to collaborate on specific documents? Create manual pairs for individual files.

```bash
docsync pair report.md gdoc://abc123
docsync sync report.md
```

### 3. Import mode (Obsidian)
**One-way import for inspiration**

Pull content from your personal Obsidian vault when needed.

```bash
docsync import obsidian://vault/note.md --to=notion://page-id
```

---

## Features

- ✅ **Bidirectional sync**: Edit locally or remotely, syncs both ways
- ✅ **Semi-automatic**: Prompts before syncing, manual conflict resolution
- ✅ **Hierarchical**: Directory structure maps to Notion page hierarchy
- ✅ **Watch mode**: Continuously monitors for changes
- ✅ **Conflict resolution**: Clear diffs and resolution strategies
- ✅ **Local-first**: Your local files are the source of truth

---

## Project structure

```
docsync/
├── AGENT_CONTEXT.md              # Project navigation (start here!)
├── README.md                     # This file
├── 01-context/                   # Strategic documents
│   └── 2025-11-11_IMPLEMENTATION_PLAN.md  # Complete implementation plan
├── 02-research/                  # Research and analysis
├── 03-implementation/            # Work in progress
├── 04-agents/                    # Agent configurations
├── examples/                     # Usage examples
└── tests/                        # Tests (when built)
```

---

## Getting started

### For understanding the project

1. Read [`AGENT_CONTEXT.md`](./AGENT_CONTEXT.md) for project overview
2. Read [`01-context/2025-11-11_IMPLEMENTATION_PLAN.md`](./01-context/2025-11-11_IMPLEMENTATION_PLAN.md) for complete plan
3. Understand the three operating modes above

### For development

**Current phase**: Planning complete, ready to begin Phase 0

**Next steps**:
1. Review and approve implementation plan
2. Set up Python project with uv
3. Begin Phase 0 (Foundation)

See implementation plan for detailed phase breakdown.

---

## Architecture overview

```
┌─────────────────────────────────────────────┐
│  CLI Layer (Click)                          │
│  Commands: init, pair, sync, watch, resolve │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Mode Controllers                           │
│  - Mirror Mode (Notion directory sync)      │
│  - Pair Mode (Selective documents)          │
│  - Import Mode (One-way from Obsidian)      │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Core Services                              │
│  - SyncService (3-way merge)                │
│  - WatchService (File monitoring)           │
│  - ConflictResolver (Manual resolution)     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Adapters                                   │
│  - Local files                              │
│  - Notion (pages + hierarchy)               │
│  - Google Docs (via MCP)                    │
│  - Obsidian (read-only)                     │
└─────────────────────────────────────────────┘
```

---

## Technology stack

- **Python 3.11+** with asyncio
- **uv** for dependency management
- **Click** for CLI
- **notion-client** for Notion API
- **watchdog** for file monitoring
- **rich** for terminal UI
- **pytest** for testing

---

## Implementation phases

| Phase | Description | Duration | Status |
|-------|-------------|----------|--------|
| 0 | Foundation and setup | 3-5 days | Not started |
| 1 | Local file operations | 3-5 days | Not started |
| 2 | Notion adapter | 5-7 days | Not started |
| 3 | Mirror mode initialization | 3-4 days | Not started |
| 4 | Bidirectional sync | 5-7 days | Not started |
| 5 | Conflict resolution | 4-5 days | Not started |
| 6 | Watch mode | 3-5 days | Not started |
| 7 | Google Docs pairing | 3-5 days | Not started |
| 8 | Obsidian import | 2-3 days | Not started |

**MVP** (Phases 0-6): ~21-33 days
**Full implementation**: ~31-50 days

---

## Philosophy

### Why separate Notion and Obsidian?

**Notion** is naturally suited for work and business:
- Structured content
- Collaboration features
- Database capabilities
- Web-based access

**Obsidian** is naturally suited for personal knowledge:
- Self-reflection
- Book notes
- Personal insights
- Local-first

**No need for bidirectional sync** - they serve different purposes. Import from Obsidian to Notion when a personal insight becomes relevant to work.

### Why semi-automatic?

- **User control**: You decide when to sync
- **Visibility**: Clear prompts show what's happening
- **Safety**: Manual conflict resolution prevents data loss
- **Transparency**: Always know the sync state

---

## Contributing

This is a personal project by Roman Siepelmeyer, built with Claude Code.

---

## License

TBD

---

## Quick links

- **[AGENT_CONTEXT.md](./AGENT_CONTEXT.md)** - Project navigation
- **[Implementation Plan](./01-context/2025-11-11_IMPLEMENTATION_PLAN.md)** - Complete technical plan
- **[Examples](./examples/)** - Usage examples (once built)

---

**Current status**: Planning complete, ready to begin implementation!
