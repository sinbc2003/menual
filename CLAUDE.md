# CLAUDE.md - AI Assistant Guide for menual Repository

## Repository Overview

This repository (`menual`) is a document archive containing the **2025 Korean Education Public Official Personnel Handbook for Secondary Education** (2025년 교육공무원 인사실무편람 - 중등). It serves as a reference resource for personnel administration in the Korean secondary education system.

## Repository Structure

```
menual/
├── 2025년 교육공무원 인사실무편람(중등)_표준용량.pdf  # Main handbook (~15MB)
├── 분리된페이지/                                      # Split individual PDF pages (685 files)
│   ├── 표지 및 머릿말1쪽.pdf ~ 표지 및 머릿말8쪽.pdf  # Cover & preface (8 pages)
│   └── 3쪽.pdf ~ 679쪽.pdf                            # Main content pages
├── 마크다운/                                          # Markdown extractions (602 files)
│   ├── 표지 및 머릿말1쪽.md ~ 표지 및 머릿말8쪽.md    # Cover & preface (8 pages)
│   └── 3쪽.md ~ 608쪽.md                              # Main content pages
└── CLAUDE.md                                          # This file
```

### File Naming Convention

- **Main content pages**: `{페이지번호}쪽.pdf` or `{페이지번호}쪽.md` (e.g., `10쪽.pdf` = page 10)
- **Cover/Preface pages**: `표지 및 머릿말{번호}쪽.pdf/.md` (e.g., `표지 및 머릿말1쪽.pdf`)
- `쪽` means "page" in Korean

### Document Statistics

| Category | Count | Size |
|----------|-------|------|
| Main PDF | 1 | ~15MB |
| Split PDF files | 685 | ~405MB |
| Markdown files | 602 | ~1.5MB |
| Cover & preface pages | 8 (each format) | - |
| Main PDF pages | 3-679 | - |
| Markdown pages | 3-608 | - |
| **Total repository size** | - | **~422MB** |

## Content Formats

### PDF Files (`분리된페이지/`)

- Individual PDF pages extracted from the main handbook
- Contains pages 3-679 plus 8 cover/preface pages
- Suitable for viewing original formatting, tables, and diagrams
- Use when visual layout is important

### Markdown Files (`마크다운/`)

- Text extractions of PDF pages converted to markdown format
- Contains pages 3-608 plus 8 cover/preface pages
- **Recommended for AI assistants**: Faster to read and search
- Preserves document structure with headers, lists, and basic formatting
- Use for text-based searches and content analysis

## Purpose & Use Cases

This repository is designed for:

1. **Reference lookup**: Finding specific personnel administration guidelines
2. **Page-level access**: Individual pages can be referenced or shared
3. **Document preservation**: Version-controlled storage of official handbook
4. **Text search**: Markdown files enable full-text search capabilities

## Working with This Repository

### For AI Assistants

When working with this repository:

1. **Prefer markdown files**: Use `마크다운/{페이지}쪽.md` for faster reading and searching
2. **Use PDFs when needed**: Use `분리된페이지/{페이지}쪽.pdf` for visual content or pages 609-679
3. **Finding pages**: Page numbers in filenames correspond to the handbook's internal pagination
4. **Korean language**: All content is in Korean; provide translations when helpful

### Recommended Workflow

1. **For content searches**: Read markdown files in `마크다운/` directory
2. **For specific page requests**: Check if markdown exists (pages 3-608), otherwise use PDF
3. **For visual/table verification**: Reference the PDF version

### Common Tasks

- **Locating specific topics**: Search markdown files for keywords
- **Page extraction**: Individual pages are already extracted in both formats
- **Content search**: Use Grep on `마크다운/` directory for text searches
- **Viewing tables/diagrams**: Read PDF files when formatting matters

## Document Context

The **교육공무원 인사실무편람** (Education Public Official Personnel Handbook) covers:

- Personnel appointment and transfer procedures (임용)
- Qualification requirements for education officials
- Performance evaluation guidelines
- Leave and benefits administration
- Disciplinary procedures
- And other HR-related regulations for secondary education

## Git Workflow

### Branch Strategy

- Development branches follow pattern: `claude/claude-md-{session-id}`
- Pull requests are used for content updates

### Commit Guidelines

- Use descriptive commit messages
- Reference page numbers or content changes specifically
- Examples:
  - `Add split PDF pages from 인사실무편람`
  - `Add markdown extractions for pages 27-608`

## Important Notes

1. **File sizes**: The main PDF is ~15MB; individual pages vary in size
2. **Binary files**: PDF files are binary; markdown files are text
3. **Language**: All document content is in Korean
4. **Official document**: This is a government publication; treat content as authoritative reference material
5. **Incomplete markdown**: Markdown extractions currently cover pages 3-608; pages 609-679 are PDF-only

## Version Information

- **Document year**: 2025
- **Target audience**: Secondary education (중등) administrators
- **Publisher**: Korean government education authority
- **Last CLAUDE.md update**: 2026-01-24
