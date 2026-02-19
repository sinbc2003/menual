#!/usr/bin/env python3
"""
QA Generator Pass 3 - Cross-page combined questions and deeper extraction.
Focuses on pages with rich content that can yield more questions.
"""

import json
import os
import re
import random
from collections import defaultdict

random.seed(456)

MD_DIR = "/home/user/menual/마크다운"
OUTPUT_FILE = "/home/user/menual/qa_generated_p3.jsonl"

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
    for s, e, name, num in CATEGORIES:
        if s <= page <= e:
            return name, num
    return "교원의 임용", "1"

def has_batchim(char):
    if '\uAC00' <= char <= '\uD7A3':
        return ((ord(char) - 0xAC00) % 28) != 0
    return False

def fx(text, topic):
    if not topic: return text
    lc = topic.rstrip()[-1] if topic.rstrip() else 'a'
    b = has_batchim(lc)
    return text.replace("{이가}", "이" if b else "가").replace("{을를}", "을" if b else "를").replace("{은는}", "은" if b else "는")

def clean_html(t):
    t = re.sub(r'<br\s*/?>', '\n', t, flags=re.I)
    t = re.sub(r'<[^>]+>', '', t)
    return re.sub(r'\n{3,}', '\n\n', t).strip()

def is_form(t):
    return (len(re.findall(r'<(?:br|div|p |span|table|img|input)', t, re.I)) > 5 or
            t.count('[ ]') + t.count('서식') + t.count('________') > 3)

def read_md(page):
    path = os.path.join(MD_DIR, f"{page}쪽.md")
    return open(path).read() if os.path.exists(path) else None

def clean_topic(title, parents=None):
    t = re.sub(r'^[가나다라마바사아자차카타파하][\)\.\s]+', '', title)
    t = re.sub(r'^\d+[\)\.\s]+', '', t)
    t = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', t)
    t = re.sub(r'^\([가나다라마바사아자차카타파하\d]+\)\s*', '', t)
    t = re.sub(r'\*\*', '', t)
    t = re.sub(r'\s*\((?:[「『].*?[」』]|.*?제\d+조.*?)\)\s*', '', t)
    t = re.sub(r'\s*\(계속\)\s*', '', t).strip()
    if (not t or len(t) < 2) and parents:
        for p in reversed(parents):
            ct = clean_topic(p)
            if ct and len(ct) >= 2: return ct
    return t


# ──────── PASS 3 STRATEGIES ────────

# Strategy 1: Extract individual numbered items as separate questions
def extract_numbered_items(text):
    """Extract individual numbered/lettered items for dedicated questions."""
    items = []
    # Match (1), (2), (가), (나), ①, ② etc.
    patterns = [
        r'\((\d+)\)\s*(.{20,200}?)(?=\n\(|\n[①②]|\n\*\*|\Z)',
        r'\(([가나다라마바사아자])\)\s*(.{20,200}?)(?=\n\(|\n[①②]|\n\*\*|\Z)',
        r'([①②③④⑤⑥⑦⑧⑨⑩])\s*(.{20,200}?)(?=\n[①②③]|\n\(|\n\*\*|\Z)',
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, re.DOTALL):
            label = m.group(1)
            content = m.group(2).strip().replace('\n', ' ')
            if 20 <= len(content) <= 200 and not is_form(content):
                items.append((label, content))
    return items


# Strategy 2: Extract bold-defined terms
def extract_bold_terms(text):
    """Extract bold-defined terms for definitional questions."""
    terms = []
    for m in re.finditer(r'\*\*(.{3,30}?)\*\*\s*(?::|：|이란|이라\s*함은)\s*(.{10,200})', text):
        term = m.group(1).strip()
        definition = m.group(2).strip()
        if not is_form(definition) and not re.search(r'[가-힣]\s[가-힣]\s[가-힣]\s[가-힣]', term):
            terms.append((term, definition))
    return terms


# Strategy 3: Extract Q&A from blockquote examples/cases
def extract_cases(text):
    """Extract cases/examples from blockquotes."""
    cases = []
    for m in re.finditer(r'【사례\s*\d+】\s*(.{20,300}?)(?=【|$)', text, re.DOTALL):
        case = m.group(1).strip().replace('\n', ' ')
        if len(case) >= 30 and not is_form(case):
            cases.append(case)
    return cases


# Strategy 4: Table row questions (one Q per row)
def extract_table_rows(raw_text):
    """Extract individual table rows as Q&A pairs."""
    lines = raw_text.split('\n')
    table_lines = [l.strip() for l in lines if l.strip().startswith('|')]
    if len(table_lines) < 3:
        return []

    headers = [h.strip() for h in table_lines[0].split('|') if h.strip()]
    rows = []
    for line in table_lines[1:]:
        if re.match(r'^\|[\s\-:|]+\|$', line):
            continue
        cells = [c.strip() for c in line.split('|') if c.strip() != '']
        if cells and len(cells) >= 2:
            # Skip rows with HTML
            if any(re.search(r'<(?:br|div|p )', c, re.I) for c in cells):
                continue
            rows.append((headers, cells))
    return rows


# Question templates for pass 3
ITEM_Q = [
    "{parent}에서 {item_desc}{은는} 어떤 내용인가요?",
    "{parent}의 {item_label}번째 항목은 무엇인가요?",
    "{item_desc}에 대해 자세히 설명해주세요.",
]

TERM_Q = [
    "{term}{이가} 의미하는 바는 무엇인가요?",
    "{term}의 정확한 뜻을 알려주세요.",
    "법령에서 말하는 {term}{은는} 무엇인가요?",
]

CASE_Q = [
    "관련 사례에서 {case_summary} 경우는 어떻게 판단하나요?",
    "{case_summary}에 대한 판례나 해석이 어떻게 되나요?",
]

TABLE_Q = [
    "{row_label}의 {header}는 어떻게 되나요?",
    "{row_label}에 대한 세부 내용을 알려주세요.",
]


def make_item_question(parent_topic, label, content):
    """Generate a question from a numbered item."""
    # Extract key phrase from content
    desc = content[:30].strip()
    if '하는 경우' in content:
        idx = content.index('하는 경우') + 4
        desc = content[:idx].strip()
    elif '한 경우' in content:
        idx = content.index('한 경우') + 3
        desc = content[:idx].strip()

    tmpl = random.choice(ITEM_Q)
    q = tmpl.replace("{parent}", parent_topic).replace("{item_desc}", desc).replace("{item_label}", str(label))
    q = fx(q, desc)
    return q


def make_term_question(term):
    tmpl = random.choice(TERM_Q)
    q = tmpl.replace("{term}", term)
    return fx(q, term)


def make_case_question(case_text):
    summary = case_text[:40].strip()
    if len(summary) > 35:
        summary = summary[:35] + "..."
    tmpl = random.choice(CASE_Q)
    q = tmpl.replace("{case_summary}", summary)
    return q


def make_table_question(headers, row, parent_topic):
    label = row[0].replace('<br>', '/').strip()
    if not label or label == '-' or len(label) < 2:
        return None
    if len(headers) >= 2:
        header = headers[1]
    else:
        header = "내용"
    tmpl = random.choice(TABLE_Q)
    q = tmpl.replace("{row_label}", label).replace("{header}", header)
    return q


def build_answer_from_content(intro, content, law_text=""):
    """Build a structured answer from content."""
    clean_content = clean_html(content)
    # Remove markdown bold for readability
    formatted = re.sub(r'\*\*(.+?)\*\*', r'\1', clean_content)

    answer = f"{intro}\n\n{formatted}"
    if law_text:
        answer += f"\n\n**관련 근거:** {law_text}"
    return answer


def quality_ok(entry):
    a, q, s = entry['answer'], entry['question'], entry['sources'][0]['text']
    if len(a) < 200 or len(q) < 12 or len(s) < 25:
        return False
    if re.search(r'<(?:br|div|p |span|table|img|input|align)', a + s, re.I):
        return False
    if '[ ]' in a or '________' in a or a.count('---') > 2:
        return False
    if re.search(r'[가-힣]\s[가-힣]\s[가-힣]\s[가-힣]', q):
        return False
    return True


def load_existing():
    qs = set()
    for fp in ["/home/user/menual/qa_dataset.jsonl",
               "/home/user/menual/qa_hq_p8_12.jsonl",
               "/home/user/menual/qa_hq_direct.jsonl",
               "/home/user/menual/qa_generated.jsonl",
               "/home/user/menual/qa_generated_p2.jsonl"]:
        if os.path.exists(fp):
            with open(fp) as f:
                for line in f:
                    try:
                        d = json.loads(line.strip())
                        qs.add(d.get('question', '').strip())
                    except:
                        pass
    return qs


def parse_page_full(content, page):
    """Parse full page content into one big section."""
    text = clean_html(content)
    # Remove page header
    text = re.sub(r'^#\s+\d+쪽\s*\n', '', text)
    # Extract headers as parent titles
    headers = re.findall(r'^#{1,4}\s+(.+)$', text, re.MULTILINE)
    return {
        'text': text,
        'raw': content,
        'headers': headers,
        'page': page,
        'length': len(text),
        'is_form': is_form(content)
    }


def generate_pass3():
    existing = load_existing()
    print(f"Loaded {len(existing)} existing questions")

    pages = sorted(int(m.group(1)) for fn in os.listdir(MD_DIR)
                   if (m := re.match(r'(\d+)쪽\.md$', fn)))

    entries = []
    stats = defaultdict(int)
    cat_counts = defaultdict(int)

    for page in pages:
        content = read_md(page)
        if not content or len(content.strip()) < 80:
            continue
        if is_form(content):
            stats['skip_form'] += 1
            continue

        text = clean_html(content)
        text_no_header = re.sub(r'^#\s+\d+쪽\s*\n', '', text)
        cat_name, cat_num = get_category(page)

        # Get parent topic from headers
        headers = re.findall(r'^#{1,4}\s+(.+)$', text, re.MULTILINE)
        parent_topic = ""
        for h in headers:
            ct = clean_topic(h)
            if ct and len(ct) >= 3 and not re.search(r'\d+쪽', ct):
                parent_topic = ct
                break
        if not parent_topic:
            parent_topic = cat_name

        # Strategy 1: Individual numbered items
        items = extract_numbered_items(text_no_header)
        for label, item_content in items[:5]:
            q = make_item_question(parent_topic, label, item_content)
            if q in existing or len(q) < 15:
                stats['dup'] += 1
                continue

            intro = f"{parent_topic}의 세부 내용을 안내드립니다."
            answer = build_answer_from_content(intro, item_content)

            # Add context
            if len(answer) < 200:
                answer = f"{intro}\n\n**관련 분류:** {parent_topic}\n\n{item_content}"

            # Extract law refs from item
            laws = re.findall(r'[「『](.+?)[」』]\s*(제\d+조)?', item_content)
            if laws:
                law_str = ", ".join(f"「{l[0]}」{' ' + l[1] if l[1] else ''}" for l in laws[:3])
                answer += f"\n\n**관련 근거:** {law_str}"

            source = item_content if len(item_content) >= 30 else f"{parent_topic}: {item_content}"

            entry = {
                "id": f"q_{cat_num}_{len(entries)+20001:05d}",
                "question": q,
                "answer": answer,
                "sources": [{"page": page, "title": parent_topic, "text": source[:500]}],
                "category": cat_name,
                "subcategory": parent_topic[:20] if len(parent_topic) <= 20 else cat_name,
                "keywords": list(set([parent_topic] + re.findall(r'교[원감사장]|임용|전보|승진|휴직|복직|징계|호봉|승급|평정', item_content)))[:6]
            }
            if quality_ok(entry):
                entries.append(entry)
                existing.add(q)
                cat_counts[cat_name] += 1
            else:
                stats['quality_fail'] += 1

        # Strategy 2: Bold-defined terms
        terms = extract_bold_terms(text_no_header)
        for term, definition in terms[:3]:
            q = make_term_question(term)
            if q in existing or len(q) < 12:
                stats['dup'] += 1
                continue

            intro = f"{term}의 의미를 안내드립니다."
            answer = f"{intro}\n\n**{term}:** {definition}"
            if parent_topic and parent_topic != term:
                answer = f"{intro}\n\n**관련 분야:** {parent_topic}\n\n**{term}:** {definition}"

            laws = re.findall(r'[「『](.+?)[」』]', definition)
            if laws:
                answer += f"\n\n**관련 법령:** 「{'」, 「'.join(laws[:3])}」"

            source = f"{term}: {definition}"[:500]

            entry = {
                "id": f"q_{cat_num}_{len(entries)+20001:05d}",
                "question": q,
                "answer": answer,
                "sources": [{"page": page, "title": term, "text": source}],
                "category": cat_name,
                "subcategory": parent_topic[:20] if len(parent_topic) <= 20 else cat_name,
                "keywords": list(set([term, parent_topic]))[:6]
            }
            if quality_ok(entry):
                entries.append(entry)
                existing.add(q)
                cat_counts[cat_name] += 1

        # Strategy 3: Case/example questions
        cases = extract_cases(text_no_header)
        for case in cases[:2]:
            q = make_case_question(case)
            if q in existing or len(q) < 15:
                continue

            intro = f"{parent_topic} 관련 사례에 대해 설명드리겠습니다."
            answer = f"{intro}\n\n**사례 내용:**\n{case}"
            laws = re.findall(r'[「『](.+?)[」』]', case)
            if laws:
                answer += f"\n\n**관련 법령:** 「{'」, 「'.join(laws[:3])}」"

            entry = {
                "id": f"q_{cat_num}_{len(entries)+20001:05d}",
                "question": q,
                "answer": answer,
                "sources": [{"page": page, "title": parent_topic, "text": case[:500]}],
                "category": cat_name,
                "subcategory": parent_topic[:20],
                "keywords": list(set([parent_topic] + re.findall(r'징계|처분|감경|위반|의무', case)))[:6]
            }
            if quality_ok(entry):
                entries.append(entry)
                existing.add(q)
                cat_counts[cat_name] += 1

        # Strategy 4: Table row questions
        if '|' in content:
            rows = extract_table_rows(content)
            for headers_list, row in rows[:4]:
                q = make_table_question(headers_list, row, parent_topic)
                if not q or q in existing or len(q) < 12:
                    continue

                # Build answer from row data
                row_label = row[0].replace('<br>', '/').strip()
                intro = f"{row_label}에 대해 안내드립니다."
                answer_parts = [intro, ""]
                for i, cell in enumerate(row):
                    cell_clean = cell.replace('<br>', ', ').strip()
                    if cell_clean and cell_clean != '-':
                        if i < len(headers_list):
                            answer_parts.append(f"**{headers_list[i]}:** {cell_clean}")
                        else:
                            answer_parts.append(f"- {cell_clean}")

                answer = "\n".join(answer_parts)
                if parent_topic:
                    answer = f"{intro}\n\n**관련 분야:** {parent_topic}\n\n" + "\n".join(answer_parts[2:])

                source = " | ".join(row)[:500]

                entry = {
                    "id": f"q_{cat_num}_{len(entries)+20001:05d}",
                    "question": q,
                    "answer": answer,
                    "sources": [{"page": page, "title": row_label, "text": source}],
                    "category": cat_name,
                    "subcategory": parent_topic[:20],
                    "keywords": list(set([parent_topic, row_label]))[:6]
                }
                if quality_ok(entry):
                    entries.append(entry)
                    existing.add(q)
                    cat_counts[cat_name] += 1

    print(f"\n=== Pass 3 Results ===")
    print(f"Total: {len(entries)}")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    print(f"\nCategories:")
    for c, n in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")

    if entries:
        al = [len(e['answer']) for e in entries]
        sl = [len(e['sources'][0]['text']) for e in entries]
        print(f"\nQuality:")
        print(f"  Answer: avg={sum(al)//len(al)}, min={min(al)}, max={max(al)}")
        print(f"  Source: avg={sum(sl)//len(sl)}, min={min(sl)}, max={max(sl)}")
        print(f"  Pages: {len(set(e['sources'][0]['page'] for e in entries))}")

    with open(OUTPUT_FILE, 'w') as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
    print(f"\nWritten to {OUTPUT_FILE}")


if __name__ == '__main__':
    generate_pass3()
