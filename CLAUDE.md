# CLAUDE.md - AI Assistant Guide for menual Repository

## Repository Overview

This repository (`menual`) is a document archive containing the **2025 Korean Education Public Official Personnel Handbook for Secondary Education** (2025년 교육공무원 인사실무편람 - 중등). It serves as a reference resource for personnel administration in the Korean secondary education system.

## Repository Structure

```
menual/
├── 2025년 교육공무원 인사실무편람(중등)_표준용량.pdf  # Main handbook (~15MB)
├── 분리된페이지/                                      # Split individual pages (687 files)
│   ├── 표지 및 머릿말1쪽.pdf ~ 표지 및 머릿말8쪽.pdf  # Cover & preface (8 pages)
│   └── 8쪽.pdf ~ 679쪽.pdf                           # Main content pages
└── CLAUDE.md                                          # This file
```

### File Naming Convention

- **Main content pages**: `{페이지번호}쪽.pdf` (e.g., `10쪽.pdf` = page 10)
- **Cover/Preface pages**: `표지 및 머릿말{번호}쪽.pdf` (e.g., `표지 및 머릿말1쪽.pdf`)
- `쪽` means "page" in Korean

### Document Statistics

| Category | Count |
|----------|-------|
| Total split PDF files | 687 |
| Cover & preface pages | 8 |
| Main content pages | 679 |
| Repository size | ~420MB |

## Purpose & Use Cases

This repository is designed for:

1. **Reference lookup**: Finding specific personnel administration guidelines
2. **Page-level access**: Individual pages can be referenced or shared
3. **Document preservation**: Version-controlled storage of official handbook

## Working with This Repository

### For AI Assistants

When working with this repository:

1. **Reading PDFs**: Use the Read tool to view PDF content when users ask about specific pages
2. **Finding pages**: Page numbers in filenames correspond to the handbook's internal pagination
3. **Korean language**: All content is in Korean; provide translations when helpful

### Common Tasks

- **Locating specific topics**: Users may ask about personnel regulations by topic
- **Page extraction**: Individual pages are already extracted in `분리된페이지/`
- **Content search**: May require reading PDF files to find relevant sections

## Git Workflow

### Branch Strategy

- Development branches follow pattern: `claude/claude-md-{session-id}`
- Pull requests are used for content updates

### Commit Guidelines

- Use descriptive commit messages
- Reference page numbers or content changes specifically
- Example: `Add split PDF pages from 인사실무편람`

## Important Notes

1. **File sizes**: The main PDF is ~15MB; individual pages vary in size
2. **Binary files**: This repo primarily contains PDFs (binary), not code
3. **Language**: All document content is in Korean
4. **Official document**: This is a government publication; treat content as authoritative reference material

## Document Context

The **교육공무원 인사실무편람** (Education Public Official Personnel Handbook) covers:

- Personnel appointment and transfer procedures
- Qualification requirements for education officials
- Performance evaluation guidelines
- Leave and benefits administration
- Disciplinary procedures
- And other HR-related regulations for secondary education

## Version Information

- **Document year**: 2025
- **Target audience**: Secondary education (중등) administrators
- **Publisher**: Korean government education authority
