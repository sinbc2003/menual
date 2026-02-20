#!/usr/bin/env python3
"""
High-quality QA generator v2 for 교육공무원 인사실무편람.
Reads all markdown files and generates diverse, content-aware Q&A entries.
"""

import json
import os
import re
import random
from collections import defaultdict

random.seed(42)

MD_DIR = "/home/user/menual/마크다운"
OUTPUT_FILE = "/home/user/menual/qa_generated.jsonl"
EXISTING_FILE = "/home/user/menual/qa_dataset.jsonl"

# Category mapping by page range
CATEGORIES = [
    (3, 100, "교원의 임용", "1"),
    (101, 118, "정원 및 순회교사제", "2"),
    (119, 256, "휴직 및 복직", "3"),
    (257, 336, "복무", "4"),
    (337, 434, "계약제교원", "5"),
    (435, 526, "평정 업무", "6"),
    (527, 596, "징계 및 직위해제", "7"),
    (597, 700, "승급 및 호봉획정", "8"),
]

def get_category(page):
    for start, end, name, num in CATEGORIES:
        if start <= page <= end:
            return name, num
    return "교원의 임용", "1"


def has_korean_batchim(char):
    if '\uAC00' <= char <= '\uD7A3':
        return ((ord(char) - 0xAC00) % 28) != 0
    return False


def fix_particles(text, topic):
    if not topic:
        return text
    last_char = topic.rstrip()[-1] if topic.rstrip() else 'a'
    b = has_korean_batchim(last_char)
    text = text.replace("{이가}", "이" if b else "가")
    text = text.replace("{을를}", "을" if b else "를")
    text = text.replace("{은는}", "은" if b else "는")
    text = text.replace("{으로로}", "으로" if b else "로")
    return text


# ──────────────── HTML/FORM DETECTION ────────────────

def is_form_content(text):
    """Check if content is primarily a form/template."""
    html_tags = len(re.findall(r'<(?:br|div|p |span|table|img|input)', text, re.I))
    checkboxes = text.count('[ ]') + text.count('[✓]') + text.count('[v]')
    form_markers = text.count('서식') + text.count('별지') + text.count('귀하')
    blank_lines = text.count('________') + text.count('( )학교')
    total_markers = html_tags + checkboxes + form_markers + blank_lines
    return total_markers > 3 or html_tags > 5


def clean_html(text):
    """Remove HTML tags from text."""
    text = re.sub(r'<br\s*/?>',  '\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ──────────────── CONTENT PARSING ────────────────

def read_md_file(page):
    path = os.path.join(MD_DIR, f"{page}쪽.md")
    if not os.path.exists(path):
        return None
    with open(path, encoding='utf-8') as f:
        return f.read()


def parse_sections(content, page):
    """Parse markdown content into structured sections."""
    # Skip form/template pages
    if is_form_content(content):
        # Still try to extract meaningful text sections
        content = clean_html(content)

    lines = content.split('\n')
    sections = []
    current_section = {
        'title': '', 'level': 0, 'content_lines': [],
        'parent_titles': [], 'page': page
    }
    title_stack = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip page header
        if re.match(r'^#\s+\d+쪽\s*$', stripped):
            continue

        # Skip HTML-heavy lines
        if len(re.findall(r'<[^>]+>', stripped)) > 2:
            continue

        # Skip pure separator lines
        if re.match(r'^[\-=_]{3,}$', stripped):
            continue

        # Header detection
        header_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if header_match:
            if current_section['content_lines']:
                sections.append(finalize_section(current_section))
            level = len(header_match.group(1))
            title = header_match.group(2).strip()
            while title_stack and title_stack[-1][0] >= level:
                title_stack.pop()
            parent_titles = [t[1] for t in title_stack]
            title_stack.append((level, title))
            current_section = {
                'title': title, 'level': level, 'content_lines': [],
                'parent_titles': parent_titles[:], 'page': page
            }
            continue

        # Bold-prefixed sub-sections
        bold_match = re.match(r'^\*\*(.+?)\*\*\s*$', stripped)
        if bold_match and len(stripped) < 100:
            if current_section['content_lines']:
                sections.append(finalize_section(current_section))
            sub_title = bold_match.group(1).strip()
            parent_titles = current_section['parent_titles'][:]
            if current_section['title']:
                parent_titles.append(current_section['title'])
            current_section = {
                'title': sub_title, 'level': current_section['level'] + 1,
                'content_lines': [], 'parent_titles': parent_titles, 'page': page
            }
            continue

        # Regular content line (skip table separators)
        if not re.match(r'^\|[\-\s:|]+\|$', stripped):
            current_section['content_lines'].append(stripped)

    if current_section['content_lines']:
        sections.append(finalize_section(current_section))

    return sections


def finalize_section(section):
    """Finalize a section with analysis."""
    raw_text = '\n'.join(section['content_lines'])
    # Clean HTML
    text = clean_html(raw_text)
    section['text'] = text
    section['raw_text'] = raw_text
    section['text_length'] = len(text)
    section['content_type'] = detect_content_type(text, section['title'])
    section['key_terms'] = extract_key_terms(text, section['title'])
    section['has_table'] = bool(re.search(r'\|.*\|.*\|', raw_text))
    section['has_law_ref'] = bool(re.search(r'[「『].*?[」』]|제\d+조', text))
    section['numbers'] = extract_numbers(text)
    section['is_form'] = is_form_content(raw_text)
    return section


def detect_content_type(text, title):
    types = []
    combined = (title + ' ' + text)[:500]
    checks = [
        ('definition', r'이란|이라\s*함은|을\s*말한다|의미한다|뜻한다|정의'),
        ('condition', r'조건|요건|자격|해당하는\s*경우|대상[^자]|기준|충족'),
        ('procedure', r'절차|방법|신청|제출|신고|보고|처리|과정|순서|접수'),
        ('number', r'기간|일수|년|개월|시간|횟수|회\b|만원|퍼센트|%|평정점'),
        ('list', r'[①②③④⑤⑥⑦⑧⑨⑩]|\([가나다라마바]\)|종류|구분|유형'),
        ('restriction', r'금지|못한다|안\s*된다|위반|처벌|제한|불가'),
        ('effect', r'효력|효과|인정|산입|반영|적용'),
        ('exception', r'다만|단,|예외|제외|특례|불구하고'),
        ('discipline', r'감경|가중|징계|처분|면직|파면|해임|정직|감봉|견책'),
        ('compensation', r'보수|수당|급여|호봉|봉급|승급'),
        ('evaluation', r'평정|평가|성적|근무성적|경력평정|가산점'),
        ('appointment', r'전보|전직|승진|임용|채용|발령|배치'),
        ('leave', r'휴직|복직|휴가|연가|병가|공가|특별휴가'),
    ]
    for ctype, pattern in checks:
        if re.search(pattern, combined):
            types.append(ctype)
    return types or ['general']


def extract_key_terms(text, title):
    terms = set()
    for m in re.finditer(r'\*\*(.+?)\*\*', text):
        t = m.group(1).strip()
        if 2 <= len(t) <= 30 and not t.startswith('가)') and not re.match(r'^\d+\)', t):
            terms.add(t)
    clean_title = re.sub(r'[*#\d\)\(\.]', '', title).strip()
    if clean_title and len(clean_title) >= 2:
        terms.add(clean_title)
    for m in re.finditer(r'[「『](.+?)[」』]', text):
        terms.add(m.group(1))
    return list(terms)[:8]


def extract_numbers(text):
    nums = []
    for m in re.finditer(r'\d+(?:년|월|일|시간|명|회|%|퍼센트|만원|원)\b', text):
        nums.append(m.group(0))
    return nums


# ──────────────── TOPIC NAME CLEANING ────────────────

def clean_topic(title, parent_titles=None):
    """Clean a title into a natural topic name."""
    t = title
    # Remove numbering prefixes
    t = re.sub(r'^[가나다라마바사아자차카타파하]\)\s*', '', t)
    t = re.sub(r'^[가나다라마바사아자차카타파하]\.\s*', '', t)
    t = re.sub(r'^\d+[\)\.\s]+', '', t)
    t = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', t)
    t = re.sub(r'^\([가나다라마바사아자차카타파하\d]+\)\s*', '', t)
    # Remove markdown
    t = re.sub(r'\*\*', '', t)
    # Remove law references in parentheses
    t = re.sub(r'\s*\((?:[「『].*?[」』]|.*?제\d+조.*?)\)\s*', '', t)
    t = re.sub(r'\s*\(계속\)\s*', '', t)
    t = t.strip()

    if (not t or len(t) < 2) and parent_titles:
        for pt in reversed(parent_titles):
            ct = clean_topic(pt)
            if ct and len(ct) >= 2:
                return ct
    return t


# ──────────────── QUESTION GENERATION ────────────────

# Extended question templates with more variety
TEMPLATES = {
    'definition': [
        "{t}{은는} 무엇인가요?",
        "{t}의 정의가 어떻게 되나요?",
        "{t}에 대해 구체적으로 설명해주세요.",
        "{t}{이가} 정확히 어떤 것을 의미하나요?",
        "{t}의 개념이 궁금합니다.",
        "{t}{이가} 무엇을 뜻하는 건가요?",
    ],
    'condition': [
        "{t}의 조건은 무엇인가요?",
        "{t}{을를} 하려면 어떤 요건이 필요한가요?",
        "{t}의 자격 요건이 어떻게 되나요?",
        "어떤 경우에 {t}{이가} 가능한가요?",
        "{t}의 대상자는 누구인가요?",
        "{t}에 해당하려면 어떤 조건을 충족해야 하나요?",
        "{t} 신청 자격이 있는 사람은 누구인가요?",
        "{t}{을를} 받을 수 있는 자격이 궁금합니다.",
    ],
    'procedure': [
        "{t}의 절차는 어떻게 되나요?",
        "{t}{을를} 하려면 어떻게 해야 하나요?",
        "{t} 신청 방법을 알려주세요.",
        "{t}{을를} 위해 필요한 서류는 무엇인가요?",
        "{t}{은는} 어떤 과정을 거치나요?",
        "{t}의 처리 절차가 궁금합니다.",
        "{t}{을를} 신청할 때 유의사항이 있나요?",
        "{t}의 처리 기한이 어떻게 되나요?",
    ],
    'number': [
        "{t}의 기간은 얼마나 되나요?",
        "{t}{은는} 몇 년까지 가능한가요?",
        "{t}의 횟수 제한이 있나요?",
        "{t}{은는} 얼마나 인정되나요?",
        "{t} 기간은 어떻게 계산하나요?",
        "{t}의 일수는 어떻게 되나요?",
        "{t}에 관한 기간과 횟수를 알려주세요.",
    ],
    'list': [
        "{t}에는 어떤 종류가 있나요?",
        "{t}에 해당하는 것들은 무엇인가요?",
        "{t}의 유형을 알려주세요.",
        "{t}에는 어떤 것들이 포함되나요?",
        "{t}의 구분이 어떻게 되나요?",
        "{t}{을를} 분류하면 어떻게 되나요?",
    ],
    'restriction': [
        "{t}에서 금지되는 행위는 무엇인가요?",
        "{t} 관련 제한사항이 있나요?",
        "{t}{을를} 위반하면 어떻게 되나요?",
        "{t}에서 주의해야 할 점은 무엇인가요?",
        "{t}과 관련하여 금지되는 사항을 알려주세요.",
        "{t}{이가} 제한되는 경우는 언제인가요?",
    ],
    'effect': [
        "{t}의 효력은 어떻게 되나요?",
        "{t}하면 어떤 효과가 있나요?",
        "{t}{이가} 경력평정에 어떻게 반영되나요?",
        "{t}{이가} 승진에 미치는 영향은 무엇인가요?",
        "{t}의 승급 인정은 어떻게 되나요?",
        "{t}의 결과는 어떻게 처리되나요?",
    ],
    'exception': [
        "{t}의 예외 사항이 있나요?",
        "{t}에서 제외되는 경우는 어떤 경우인가요?",
        "{t}에 특례가 적용되는 경우가 있나요?",
        "{t}{이가} 적용되지 않는 경우는 언제인가요?",
        "{t}의 단서 조항이 있나요?",
    ],
    'discipline': [
        "{t}의 종류와 내용은 무엇인가요?",
        "{t}에 해당하는 사유는 무엇인가요?",
        "{t} 시 절차는 어떻게 되나요?",
        "{t}{을를} 감경받을 수 있는 경우가 있나요?",
        "{t}의 기준은 어떻게 되나요?",
        "{t}의 양정 기준이 궁금합니다.",
    ],
    'compensation': [
        "{t}{은는} 어떻게 결정되나요?",
        "{t}의 산정 기준은 무엇인가요?",
        "{t}{은는} 얼마나 지급되나요?",
        "{t}{을를} 받을 수 있는 조건은 무엇인가요?",
        "{t}의 지급 방법이 어떻게 되나요?",
    ],
    'evaluation': [
        "{t}{은는} 어떻게 이루어지나요?",
        "{t}의 기준은 무엇인가요?",
        "{t}의 방법을 알려주세요.",
        "{t} 시 고려사항은 무엇인가요?",
        "{t}의 점수는 어떻게 계산하나요?",
        "{t}{은는} 누가 하나요?",
    ],
    'appointment': [
        "{t}의 요건은 무엇인가요?",
        "{t}{은는} 어떻게 진행되나요?",
        "{t}의 기준이 어떻게 되나요?",
        "{t} 대상자는 어떻게 선발하나요?",
        "{t}{은는} 누가 하나요?",
        "{t}의 원칙은 무엇인가요?",
    ],
    'leave': [
        "{t}{은는} 얼마나 사용할 수 있나요?",
        "{t}의 신청 절차는 어떻게 되나요?",
        "{t} 중 보수는 어떻게 되나요?",
        "{t} 기간에 승급이 되나요?",
        "{t}의 사유는 어떤 것이 있나요?",
        "{t}{을를} 사용하려면 어떻게 해야 하나요?",
        "{t} 기간 중 신분은 어떻게 되나요?",
    ],
    'general': [
        "{t}에 대해 알려주세요.",
        "{t}의 내용은 무엇인가요?",
        "{t}{은는} 어떻게 되나요?",
        "{t}에 대한 규정은 어떻게 되어 있나요?",
        "{t}{이가} 궁금합니다.",
        "{t}에 관한 주요 내용을 설명해주세요.",
    ],
}

# Natural situation-based templates
SITUATION_TEMPLATES = [
    "교사가 {sit} 어떻게 해야 하나요?",
    "{sit} 어떤 절차를 밟아야 하나요?",
    "{sit} 주의해야 할 점이 있나요?",
    "{sit} 어떻게 처리하나요?",
    "만약 {sit} 어떻게 되나요?",
    "{sit} 필요한 서류가 있나요?",
    "{sit} 관련 규정이 어떻게 되나요?",
]

# Practical/specific question templates
PRACTICAL_TEMPLATES = [
    "{t} 관련하여 자주 묻는 질문이 있나요?",
    "{t}에서 실무적으로 주의할 점은 무엇인가요?",
    "{t}의 법적 근거는 무엇인가요?",
    "{t} 관련 최근 변경사항이 있나요?",
    "{t}에 관한 판례나 사례가 있나요?",
]


def generate_questions(section):
    """Generate diverse questions for a section."""
    topic = clean_topic(section['title'], section['parent_titles'])
    if not topic or len(topic) < 2 or section['text_length'] < 50:
        return []
    if section['is_form']:
        return []

    questions = []
    used_templates = set()

    # Primary questions from content types
    for ctype in section['content_type'][:3]:
        templates = TEMPLATES.get(ctype, TEMPLATES['general'])
        available = [t for t in templates if t not in used_templates]
        selected = random.sample(available, min(2, len(available)))
        for tmpl in selected:
            used_templates.add(tmpl)
            q = tmpl.replace("{t}", topic)
            q = fix_particles(q, topic)
            questions.append((q, ctype))

    # Add general/practical questions if content is rich
    if section['text_length'] > 200:
        tmpl = random.choice(PRACTICAL_TEMPLATES)
        q = tmpl.replace("{t}", topic)
        q = fix_particles(q, topic)
        questions.append((q, 'practical'))

    # Situation-based questions from text
    if section['text_length'] > 100:
        situations = extract_situations(section['text'])
        for sit in situations[:2]:
            tmpl = random.choice(SITUATION_TEMPLATES)
            q = tmpl.replace("{sit}", sit)
            questions.append((q, 'situation'))

    # Questions from key terms (different from main topic)
    for term in section['key_terms'][:2]:
        ct = clean_topic(term)
        if ct and ct != topic and len(ct) >= 3:
            ctype = section['content_type'][0] if section['content_type'] else 'general'
            templates = TEMPLATES.get(ctype, TEMPLATES['general'])
            tmpl = random.choice(templates)
            q = tmpl.replace("{t}", ct)
            q = fix_particles(q, ct)
            questions.append((q, ctype))

    # Numbered-item specific questions
    if section['numbers']:
        for num in section['numbers'][:2]:
            q = f"{topic}에서 {num}이라는 기준은 어떤 의미인가요?"
            questions.append((q, 'number'))

    # Deduplicate
    seen = set()
    unique = []
    for q, ct in questions:
        q_norm = q.strip()
        if q_norm not in seen and len(q_norm) >= 15:
            seen.add(q_norm)
            unique.append((q_norm, ct))

    return unique[:8]


def extract_situations(text):
    situations = []
    patterns = [
        r'([가-힣\s·,]{8,50}(?:하는|한|된|하게\s*된|되는|받은|받는))\s*경우',
        r'([가-힣\s·,]{8,50}(?:하였을|하였더라도|하더라도))\s*때',
        r'([가-힣\s·,]{8,50}(?:으로|로)\s+인한)',
    ]
    for pat in patterns:
        for m in re.finditer(pat, text):
            sit = m.group(1).strip()
            sit = re.sub(r'^[·\-\s\*>]+', '', sit)
            if 8 <= len(sit) <= 60:
                # Make it end naturally
                if not sit.endswith(('경우', '때', '경우에는')):
                    sit += " 경우"
                situations.append(sit)
    return situations[:3]


# ──────────────── ANSWER GENERATION ────────────────

INTROS = [
    "{t}에 대해 안내드립니다.",
    "{t}에 대해 설명드리겠습니다.",
    "{t}{을를} 안내드립니다.",
    "{t} 관련 사항을 설명드리겠습니다.",
    "{t}에 관해 안내드립니다.",
    "{t}의 내용을 설명드리겠습니다.",
]


def build_answer(section, question, qtype):
    """Build a detailed, structured answer."""
    topic = clean_topic(section['title'], section['parent_titles'])
    text = section['text']

    # Intro
    intro_tmpl = random.choice(INTROS)
    intro = intro_tmpl.replace("{t}", topic)
    intro = fix_particles(intro, topic)

    # Build body from content
    body = build_body(section, qtype)

    # Add context from parent titles
    context_parts = []
    if section['parent_titles']:
        clean_parents = [clean_topic(p) for p in section['parent_titles'] if clean_topic(p)]
        if clean_parents:
            context_line = " > ".join(clean_parents[-3:])

    # Law references
    law_refs = extract_law_references(text)
    ref_section = ""
    if law_refs:
        ref_str = ", ".join(law_refs[:4])
        ref_section = f"\n\n**관련 근거:** {ref_str}"

    # Assemble
    answer = f"{intro}\n\n{body}{ref_section}"

    # If still too short, add more detail
    if len(answer) < 350:
        # Add parent context
        if section['parent_titles']:
            clean_parents = [clean_topic(p) for p in section['parent_titles'] if clean_topic(p)]
            if clean_parents:
                answer = f"{intro}\n\n**분류:** {' > '.join(clean_parents[-3:])}\n\n{body}{ref_section}"

        # Add numbers context
        if section['numbers'] and len(answer) < 350:
            nums_str = ", ".join(section['numbers'][:5])
            answer += f"\n\n**주요 수치:** {nums_str}"

    return answer


def build_body(section, qtype):
    """Build the main body of an answer from section content."""
    text = section['text']
    lines = text.split('\n')
    body_parts = []

    if section['has_table'] and not section['is_form']:
        # Parse table into structured text
        table_body = parse_table_to_text(section['raw_text'])
        if table_body and len(table_body) > 50:
            body_parts.append(table_body)

    if not body_parts:
        # Parse content elements
        elements = []
        for line in lines:
            stripped = line.strip()
            if not stripped or len(stripped) < 3:
                continue

            # Skip table markup
            if stripped.startswith('|') or re.match(r'^[\-\s:|]+$', stripped):
                continue

            # Bold header with content
            bm = re.match(r'^\*\*(.+?)\*\*\s*:?\s*(.*)', stripped)
            if bm:
                header = bm.group(1).strip()
                content = bm.group(2).strip()
                if content:
                    elements.append(f"**{header}:** {content}")
                elif len(header) > 3:
                    elements.append(f"**{header}**")
                continue

            # Bullet / numbered items
            im = re.match(r'^[\-•]\s*\*\*([가나다라마바사아자])\)\*\*\s*(.*)', stripped)
            if im:
                elements.append(f"- **{im.group(1)})** {im.group(2)}")
                continue

            pm = re.match(r'^\((\d+|[가나다라마바사아자])\)\s*(.*)', stripped)
            if pm:
                elements.append(f"- ({pm.group(1)}) {pm.group(2)}")
                continue

            cm = re.match(r'^([①②③④⑤⑥⑦⑧⑨⑩])\s*(.*)', stripped)
            if cm:
                elements.append(f"- {cm.group(1)} {cm.group(2)}")
                continue

            bul = re.match(r'^[\-•]\s*(.*)', stripped)
            if bul:
                elements.append(f"- {bul.group(1)}")
                continue

            # Blockquote (note)
            qm = re.match(r'^>\s*(.*)', stripped)
            if qm:
                note = qm.group(1).strip()
                if note and not note.startswith('■') and len(note) > 5:
                    elements.append(f"※ {note}")
                continue

            # Regular paragraph
            if len(stripped) > 10:
                elements.append(stripped)

        # Assemble elements
        if elements:
            # Group into logical sections
            if len(elements) <= 3:
                body_parts.append("\n".join(elements))
            else:
                # First element as summary
                body_parts.append(f"**핵심 내용:**\n{elements[0]}")
                # Rest as detailed items
                body_parts.append("\n".join(elements[1:]))
        else:
            # Fallback: use cleaned text
            clean = re.sub(r'\*\*', '', text)
            clean = re.sub(r'^>\s*', '', clean, flags=re.MULTILINE)
            if len(clean) > 20:
                body_parts.append(clean[:600])

    return "\n\n".join(body_parts)


def parse_table_to_text(raw_text):
    """Convert table content to readable structured text."""
    lines = raw_text.split('\n')
    table_lines = [l.strip() for l in lines if l.strip().startswith('|')]

    if len(table_lines) < 2:
        return ""

    # Parse header
    headers = [h.strip() for h in table_lines[0].split('|') if h.strip()]
    if not headers:
        return ""

    # Parse rows (skip separator)
    rows = []
    for line in table_lines[1:]:
        if re.match(r'^\|[\s\-:|]+\|$', line):
            continue
        cells = [c.strip() for c in line.split('|') if c.strip() != '']
        if cells:
            rows.append(cells)

    if not rows:
        return ""

    # Format as readable text
    parts = []
    for row in rows[:12]:
        if len(row) >= 2 and len(headers) >= 2:
            label = row[0].replace('<br>', ' / ').replace('<br/>', ' / ')
            if not label or label == '-':
                continue
            row_text = f"**{label}:**"
            for i, cell in enumerate(row[1:], 1):
                cell_clean = cell.replace('<br>', ', ').strip()
                if cell_clean and cell_clean != '-' and i < len(headers):
                    row_text += f"\n  - {headers[i]}: {cell_clean}"
                elif cell_clean and cell_clean != '-':
                    row_text += f"\n  - {cell_clean}"
            parts.append(row_text)

    return "\n\n".join(parts)


def extract_law_references(text):
    refs = []
    for m in re.finditer(r'[「『](.+?)[」』]\s*(제\d+조(?:의\d+)?(?:제\d+항)?)?', text):
        ref = f"「{m.group(1)}」"
        if m.group(2):
            ref += f" {m.group(2)}"
        if ref not in refs:
            refs.append(ref)
    return refs


# ──────────────── SOURCE TEXT ────────────────

def extract_source(section, min_len=80):
    """Extract source text ensuring minimum length."""
    text = section['text']
    # Remove blockquote markers
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    text = text.strip()

    if len(text) < min_len and section.get('parent_titles'):
        prefix = clean_topic(section['parent_titles'][-1])
        if prefix:
            text = f"{prefix}: {text}"

    # Truncate long sources at sentence boundary
    if len(text) > 500:
        cut = text[:500]
        for end_marker in ['다.', '다\n', '함.', '음.', '임.', '됨.']:
            pos = cut.rfind(end_marker)
            if pos > 200:
                text = text[:pos + len(end_marker)]
                break
        else:
            text = text[:500]

    return text.strip()


# ──────────────── KEYWORDS ────────────────

def extract_keywords(section, topic):
    kws = set()
    if topic and 2 <= len(topic) <= 15:
        kws.add(topic)
    for t in section['key_terms'][:3]:
        c = re.sub(r'[「」『』]', '', t).strip()
        if 2 <= len(c) <= 15:
            kws.add(c)
    for pt in section['parent_titles'][-2:]:
        c = clean_topic(pt)
        if c and 2 <= len(c) <= 15:
            kws.add(c)
    # Important domain terms
    for pat in [r'교장|교감|교사|교원|교육감',
                r'임용|채용|전보|승진|휴직|복직|면직',
                r'징계|파면|해임|정직|감봉|견책',
                r'호봉|승급|보수|수당',
                r'연가|병가|공가|육아휴직',
                r'평정|평가|경력평정|가산점']:
        for m in re.finditer(pat, section['text'][:300]):
            kws.add(m.group(0))
    return list(kws)[:7]


def get_subcategory(section, category):
    titles = section['parent_titles'] + [section['title']]
    for t in reversed(titles):
        c = clean_topic(t)
        if c and 2 <= len(c) <= 20 and c != category:
            return c
    return category


# ──────────────── MULTI-PAGE CONTEXT ────────────────

def get_continuation_context(page):
    """Get context from adjacent pages for continuation sections."""
    # Some pages start with "(계속)" indicating continuation
    prev_content = read_md_file(page - 1)
    if prev_content:
        # Extract last header from previous page
        headers = re.findall(r'^#{1,6}\s+(.+)$', prev_content, re.MULTILINE)
        if headers:
            return headers[-1]
    return None


# ──────────────── MAIN GENERATION ────────────────

def load_existing():
    questions = set()
    for fp in [EXISTING_FILE,
               "/home/user/menual/qa_hq_p8_12.jsonl",
               "/home/user/menual/qa_hq_direct.jsonl"]:
        if os.path.exists(fp):
            with open(fp) as f:
                for line in f:
                    try:
                        d = json.loads(line.strip())
                        questions.add(d.get('question', '').strip())
                    except:
                        pass
    return questions


def quality_check(entry):
    """Final quality gate for an entry."""
    a = entry['answer']
    q = entry['question']
    s = entry['sources'][0]['text']

    # Minimum lengths
    if len(a) < 250:
        return False
    if len(q) < 12:
        return False
    if len(s) < 30:
        return False

    # No HTML in answer
    if re.search(r'<(?:br|div|p |span|table|img|input|align)', a, re.I):
        return False

    # No HTML in source
    if re.search(r'<(?:br|div|p |span|table|img|input|align)', s, re.I):
        return False

    # No form-like content
    if '[ ]' in a or '________' in a:
        return False

    # Question shouldn't start with numbering
    if re.match(r'^[가나다라마바사아자차카타파하]\)\s', q) or re.match(r'^\d+\)\s', q):
        return False

    # Answer shouldn't be mostly dashes/separators
    if a.count('---') > 2:
        return False

    # Source shouldn't be mostly empty
    if s.count('◦') > 3:
        return False

    return True


def generate_all():
    existing_q = load_existing()
    print(f"Loaded {len(existing_q)} existing questions")

    pages = sorted(int(m.group(1)) for fn in os.listdir(MD_DIR)
                   if (m := re.match(r'(\d+)쪽\.md$', fn)))
    print(f"Found {len(pages)} MD pages")

    all_entries = []
    stats = defaultdict(int)
    cat_counts = defaultdict(int)

    for page in pages:
        content = read_md_file(page)
        if not content or len(content.strip()) < 50:
            stats['skip_empty'] += 1
            continue

        sections = parse_sections(content, page)
        cat_name, cat_num = get_category(page)

        for section in sections:
            if section['text_length'] < 40:
                stats['skip_short_section'] += 1
                continue
            if section['is_form'] and section['text_length'] < 100:
                stats['skip_form'] += 1
                continue

            questions = generate_questions(section)

            for q_text, qtype in questions:
                if q_text in existing_q:
                    stats['skip_dup'] += 1
                    continue

                answer = build_answer(section, q_text, qtype)
                source_text = extract_source(section)
                topic = clean_topic(section['title'], section['parent_titles'])
                keywords = extract_keywords(section, topic)
                subcategory = get_subcategory(section, cat_name)

                entry = {
                    "id": f"q_{cat_num}_{len(all_entries) + 5001:04d}",
                    "question": q_text,
                    "answer": answer,
                    "sources": [{
                        "page": page,
                        "title": topic or subcategory,
                        "text": source_text
                    }],
                    "category": cat_name,
                    "subcategory": subcategory,
                    "keywords": keywords
                }

                if quality_check(entry):
                    all_entries.append(entry)
                    existing_q.add(q_text)
                    cat_counts[cat_name] += 1
                else:
                    stats['skip_quality'] += 1

    # Print results
    print(f"\n=== Generation Results ===")
    print(f"Total entries: {len(all_entries)}")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    print(f"\nCategory distribution:")
    for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {cnt}")

    if all_entries:
        al = [len(e['answer']) for e in all_entries]
        sl = [len(e['sources'][0]['text']) for e in all_entries]
        ql = [len(e['question']) for e in all_entries]
        print(f"\nQuality metrics:")
        print(f"  Answer: avg={sum(al)//len(al)}, min={min(al)}, max={max(al)}")
        print(f"  Source: avg={sum(sl)//len(sl)}, min={min(sl)}, max={max(sl)}")
        print(f"  Question: avg={sum(ql)//len(ql)}, min={min(ql)}, max={max(ql)}")
        pages_covered = len(set(e['sources'][0]['page'] for e in all_entries))
        print(f"  Pages covered: {pages_covered}")

    # Write
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for e in all_entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
    print(f"\nWritten to {OUTPUT_FILE}")

    return all_entries


if __name__ == '__main__':
    generate_all()
