#!/usr/bin/env python3
"""
QA Generator Pass 2 - generates additional entries using different question angles.
Reads from existing entries to avoid duplicates, uses different templates.
"""

import json
import os
import re
import random
from collections import defaultdict

random.seed(123)  # Different seed from pass 1

MD_DIR = "/home/user/menual/마크다운"
OUTPUT_FILE = "/home/user/menual/qa_generated_p2.jsonl"

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
    if not topic:
        return text
    lc = topic.rstrip()[-1] if topic.rstrip() else 'a'
    b = has_batchim(lc)
    return text.replace("{이가}", "이" if b else "가").replace("{을를}", "을" if b else "를").replace("{은는}", "은" if b else "는").replace("{으로로}", "으로" if b else "로")

def clean_html(text):
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    return re.sub(r'\n{3,}', '\n\n', text).strip()

def is_form(text):
    html = len(re.findall(r'<(?:br|div|p |span|table|img|input)', text, re.I))
    marks = text.count('[ ]') + text.count('서식') + text.count('별지') + text.count('________')
    return marks > 3 or html > 5

def read_md(page):
    path = os.path.join(MD_DIR, f"{page}쪽.md")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return f.read()

def clean_topic(title, parents=None):
    t = title
    t = re.sub(r'^[가나다라마바사아자차카타파하][\)\.\s]+', '', t)
    t = re.sub(r'^\d+[\)\.\s]+', '', t)
    t = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]\s*', '', t)
    t = re.sub(r'^\([가나다라마바사아자차카타파하\d]+\)\s*', '', t)
    t = re.sub(r'\*\*', '', t)
    t = re.sub(r'\s*\((?:[「『].*?[」』]|.*?제\d+조.*?)\)\s*', '', t)
    t = re.sub(r'\s*\(계속\)\s*', '', t).strip()
    if (not t or len(t) < 2) and parents:
        for p in reversed(parents):
            ct = clean_topic(p)
            if ct and len(ct) >= 2:
                return ct
    return t

# ──────────── PASS 2 QUESTION TEMPLATES (different from pass 1) ────────────

# Conversational / real-world scenario-based questions
CONV_TEMPLATES = [
    "학교에서 {t} 관련 업무를 처리하려면 어떻게 해야 하나요?",
    "{t}에 대해 교사들이 알아야 할 핵심 내용은 무엇인가요?",
    "{t} 업무를 처리할 때 가장 중요한 점은 무엇인가요?",
    "{t}과 관련하여 학교 행정실에서 처리하는 업무는 무엇인가요?",
    "신규 교사가 {t}에 대해 알아야 할 사항은 무엇인가요?",
    "{t}{을를} 잘못 처리하면 어떤 문제가 생기나요?",
    "{t}에 관한 규정이 최근에 어떻게 바뀌었나요?",
    "학교장이 {t} 관련하여 권한이 있나요?",
    "{t}의 법적 근거가 되는 규정은 무엇인가요?",
    "{t}{이가} 교원의 신분에 미치는 영향은 무엇인가요?",
]

# Comparison/relationship questions
COMP_TEMPLATES = [
    "{t}에서 가장 중요한 조건은 무엇인가요?",
    "{t}{은는} 다른 규정과 어떤 관계가 있나요?",
    "{t}의 특이사항이나 예외 규정이 있나요?",
    "{t}에서 자주 혼동되는 부분은 무엇인가요?",
]

# Detail-focused questions
DETAIL_TEMPLATES = [
    "{t}의 구체적인 적용 사례를 알려주세요.",
    "{t}에서 서류 제출 기한은 어떻게 되나요?",
    "{t}의 행정 처리 담당자는 누구인가요?",
    "{t} 관련 민원이 들어오면 어떻게 대응해야 하나요?",
    "{t}의 세부 기준을 설명해주세요.",
    "{t}과 관련된 참고 서식이 있나요?",
]

# Summary / overview questions
OVERVIEW_TEMPLATES = [
    "{t}의 전체적인 내용을 요약해주세요.",
    "{t}에 대한 핵심 포인트를 정리해주세요.",
    "{t}을 한눈에 이해할 수 있도록 설명해주세요.",
]

ALL_P2_TEMPLATES = CONV_TEMPLATES + COMP_TEMPLATES + DETAIL_TEMPLATES + OVERVIEW_TEMPLATES


def parse_sections(content, page):
    if is_form(content):
        content = clean_html(content)
    lines = content.split('\n')
    sections = []
    cur = {'title': '', 'level': 0, 'lines': [], 'parents': [], 'page': page}
    stack = []

    for line in lines:
        s = line.strip()
        if not s or re.match(r'^#\s+\d+쪽\s*$', s):
            continue
        if len(re.findall(r'<[^>]+>', s)) > 2:
            continue
        if re.match(r'^[\-=_]{3,}$', s):
            continue

        hm = re.match(r'^(#{1,6})\s+(.+)$', s)
        if hm:
            if cur['lines']:
                sections.append(finalize(cur))
            level = len(hm.group(1))
            title = hm.group(2).strip()
            while stack and stack[-1][0] >= level:
                stack.pop()
            parents = [t[1] for t in stack]
            stack.append((level, title))
            cur = {'title': title, 'level': level, 'lines': [], 'parents': parents[:], 'page': page}
            continue

        bm = re.match(r'^\*\*(.+?)\*\*\s*$', s)
        if bm and len(s) < 100:
            if cur['lines']:
                sections.append(finalize(cur))
            sub = bm.group(1).strip()
            parents = cur['parents'][:]
            if cur['title']:
                parents.append(cur['title'])
            cur = {'title': sub, 'level': cur['level']+1, 'lines': [], 'parents': parents, 'page': page}
            continue

        if not re.match(r'^\|[\-\s:|]+\|$', s):
            cur['lines'].append(s)

    if cur['lines']:
        sections.append(finalize(cur))
    return sections


def finalize(sec):
    raw = '\n'.join(sec['lines'])
    text = clean_html(raw)
    sec['text'] = text
    sec['raw'] = raw
    sec['length'] = len(text)
    sec['is_form'] = is_form(raw)
    sec['has_law'] = bool(re.search(r'[「『].*?[」』]|제\d+조', text))
    sec['has_table'] = bool(re.search(r'\|.*\|.*\|', raw))
    return sec


def build_answer_p2(section, question):
    """Build answer with different structure than pass 1."""
    topic = clean_topic(section['title'], section['parents'])
    text = section['text']

    # Different intro style for pass 2
    intros = [
        f"{topic} 관련 내용을 안내해 드리겠습니다.",
        f"{topic}에 대해 상세히 설명드립니다.",
        f"질문하신 {topic}에 대해 답변드립니다.",
        f"{topic}의 주요 내용을 정리해 드리겠습니다.",
    ]
    intro = random.choice(intros)

    # Build body with content
    body_lines = []
    content_lines = text.split('\n')
    meaningful_lines = [l.strip() for l in content_lines
                       if l.strip() and len(l.strip()) > 5
                       and not l.strip().startswith('|')
                       and not re.match(r'^[\-\s:|]+$', l.strip())]

    if meaningful_lines:
        # Group into paragraphs
        if len(meaningful_lines) >= 4:
            body_lines.append(f"**주요 내용:**")
            for line in meaningful_lines[:3]:
                clean_line = re.sub(r'^\*\*(.+?)\*\*\s*', r'**\1:** ', line)
                body_lines.append(f"- {clean_line}" if not clean_line.startswith(('-', '※', '·')) else clean_line)

            body_lines.append(f"\n**세부 사항:**")
            for line in meaningful_lines[3:8]:
                clean_line = re.sub(r'^\*\*(.+?)\*\*\s*', r'**\1:** ', line)
                body_lines.append(f"- {clean_line}" if not clean_line.startswith(('-', '※', '·')) else clean_line)
        else:
            for line in meaningful_lines[:6]:
                clean_line = re.sub(r'^\*\*(.+?)\*\*\s*', r'**\1:** ', line)
                body_lines.append(clean_line)

    if not body_lines:
        return ""

    # Add law references
    law_refs = []
    for m in re.finditer(r'[「『](.+?)[」』]\s*(제\d+조(?:의\d+)?)?', text):
        ref = f"「{m.group(1)}」"
        if m.group(2):
            ref += f" {m.group(2)}"
        if ref not in law_refs:
            law_refs.append(ref)

    body = "\n".join(body_lines)

    # Add context from hierarchy
    if section['parents']:
        clean_parents = [clean_topic(p) for p in section['parents'] if clean_topic(p)]
        if clean_parents:
            context = " > ".join(clean_parents[-3:])
            body = f"**관련 분야:** {context}\n\n{body}"

    ref_section = ""
    if law_refs:
        ref_section = f"\n\n**관련 법령:** {', '.join(law_refs[:4])}"

    answer = f"{intro}\n\n{body}{ref_section}"
    return answer


def extract_source(section):
    text = section['text']
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE).strip()
    if len(text) < 80 and section.get('parents'):
        prefix = clean_topic(section['parents'][-1])
        if prefix:
            text = f"{prefix}: {text}"
    if len(text) > 500:
        cut = text[:500]
        for em in ['다.', '함.', '음.', '임.', '됨.']:
            pos = cut.rfind(em)
            if pos > 200:
                return text[:pos + len(em)]
        return text[:500]
    return text


def extract_keywords(section, topic):
    kws = set()
    if topic and 2 <= len(topic) <= 15:
        kws.add(topic)
    for m in re.finditer(r'\*\*(.+?)\*\*', section['text'][:300]):
        t = m.group(1).strip()
        if 2 <= len(t) <= 15:
            kws.add(t)
    for m in re.finditer(r'[「『](.+?)[」』]', section['text'][:300]):
        kws.add(re.sub(r'[「」『』]', '', m.group(0)).strip())
    for pat in [r'교장|교감|교사|교원', r'임용|전보|승진|휴직|복직', r'징계|파면|해임', r'호봉|승급|보수']:
        for m in re.finditer(pat, section['text'][:200]):
            kws.add(m.group(0))
    return list(kws)[:7]


def quality_ok(entry):
    a, q, s = entry['answer'], entry['question'], entry['sources'][0]['text']
    if len(a) < 280 or len(q) < 12 or len(s) < 30:
        return False
    if re.search(r'<(?:br|div|p |span|table|img|input|align)', a + s, re.I):
        return False
    if '[ ]' in a or '________' in a or a.count('---') > 2 or s.count('◦') > 3:
        return False
    return True


def load_existing():
    qs = set()
    for fp in ["/home/user/menual/qa_dataset.jsonl",
               "/home/user/menual/qa_hq_p8_12.jsonl",
               "/home/user/menual/qa_hq_direct.jsonl",
               "/home/user/menual/qa_generated.jsonl"]:
        if os.path.exists(fp):
            with open(fp) as f:
                for line in f:
                    try:
                        d = json.loads(line.strip())
                        qs.add(d.get('question', '').strip())
                    except:
                        pass
    return qs


def generate_pass2():
    existing = load_existing()
    print(f"Loaded {len(existing)} existing questions for dedup")

    pages = sorted(int(m.group(1)) for fn in os.listdir(MD_DIR)
                   if (m := re.match(r'(\d+)쪽\.md$', fn)))
    print(f"Found {len(pages)} pages")

    entries = []
    stats = defaultdict(int)
    cat_counts = defaultdict(int)

    for page in pages:
        content = read_md(page)
        if not content or len(content.strip()) < 50:
            continue
        sections = parse_sections(content, page)
        cat_name, cat_num = get_category(page)

        for sec in sections:
            if sec['length'] < 60 or sec['is_form']:
                stats['skip'] += 1
                continue

            topic = clean_topic(sec['title'], sec['parents'])
            if not topic or len(topic) < 2:
                continue

            # Check for spaced-out characters (form artifacts)
            if re.search(r'[가-힣]\s[가-힣]\s[가-힣]\s[가-힣]', topic):
                stats['skip_spaced'] += 1
                continue

            # Generate 2-3 questions per section using pass 2 templates
            templates = random.sample(ALL_P2_TEMPLATES, min(3, len(ALL_P2_TEMPLATES)))
            for tmpl in templates:
                q = tmpl.replace("{t}", topic)
                q = fx(q, topic)

                if q in existing:
                    stats['dup'] += 1
                    continue

                answer = build_answer_p2(sec, q)
                if not answer or len(answer) < 250:
                    stats['short_answer'] += 1
                    continue

                source = extract_source(sec)
                keywords = extract_keywords(sec, topic)
                subcategory = topic if len(topic) <= 20 else cat_name

                entry = {
                    "id": f"q_{cat_num}_{len(entries) + 10001:05d}",
                    "question": q,
                    "answer": answer,
                    "sources": [{"page": page, "title": topic, "text": source}],
                    "category": cat_name,
                    "subcategory": subcategory,
                    "keywords": keywords
                }

                if quality_ok(entry):
                    entries.append(entry)
                    existing.add(q)
                    cat_counts[cat_name] += 1
                else:
                    stats['quality_fail'] += 1

    print(f"\n=== Pass 2 Results ===")
    print(f"Total: {len(entries)}")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    print(f"\nCategories:")
    for c, n in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")

    if entries:
        al = [len(e['answer']) for e in entries]
        sl = [len(e['sources'][0]['text']) for e in entries]
        ql = [len(e['question']) for e in entries]
        print(f"\nQuality:")
        print(f"  Answer: avg={sum(al)//len(al)}, min={min(al)}, max={max(al)}")
        print(f"  Source: avg={sum(sl)//len(sl)}, min={min(sl)}, max={max(sl)}")
        print(f"  Question: avg={sum(ql)//len(ql)}, min={min(ql)}, max={max(ql)}")
        print(f"  Pages: {len(set(e['sources'][0]['page'] for e in entries))}")

    with open(OUTPUT_FILE, 'w') as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
    print(f"\nWritten to {OUTPUT_FILE}")


if __name__ == '__main__':
    generate_pass2()
