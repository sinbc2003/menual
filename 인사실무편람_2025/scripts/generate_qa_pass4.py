#!/usr/bin/env python3
"""
QA Generator Pass 4 - Full-page level questions.
Generates overview questions about entire page content.
"""

import json
import os
import re
import random
from collections import defaultdict

random.seed(789)

MD_DIR = "/home/user/menual/마크다운"
OUTPUT_FILE = "/home/user/menual/qa_generated_p4.jsonl"

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

def has_batchim(c):
    if '\uAC00' <= c <= '\uD7A3':
        return ((ord(c) - 0xAC00) % 28) != 0
    return False

def fx(text, topic):
    if not topic: return text
    b = has_batchim(topic.rstrip()[-1]) if topic.rstrip() else False
    return text.replace("{이가}", "이" if b else "가").replace("{을를}", "을" if b else "를").replace("{은는}", "은" if b else "는")

def clean_html(t):
    t = re.sub(r'<br\s*/?>', '\n', t, flags=re.I)
    t = re.sub(r'<[^>]+>', '', t)
    return re.sub(r'\n{3,}', '\n\n', t).strip()

def is_form(t):
    return (len(re.findall(r'<(?:br|div|p |span|table|img)', t, re.I)) > 5 or
            t.count('[ ]') + t.count('서식') + t.count('________') > 3)

def clean_topic(title):
    t = re.sub(r'^[가나다라마바사아자차카타파하][\)\.\s]+', '', title)
    t = re.sub(r'^\d+[\)\.\s]+', '', t)
    t = re.sub(r'^\*\*|\*\*$', '', t)
    t = re.sub(r'\s*\(.*?제\d+조.*?\)', '', t)
    t = re.sub(r'\s*\(계속\)', '', t).strip()
    return t


def load_existing():
    qs = set()
    for fp in ["/home/user/menual/qa_dataset.jsonl",
               "/home/user/menual/qa_hq_p8_12.jsonl",
               "/home/user/menual/qa_hq_direct.jsonl",
               "/home/user/menual/qa_generated.jsonl",
               "/home/user/menual/qa_generated_p2.jsonl",
               "/home/user/menual/qa_generated_p3.jsonl"]:
        if os.path.exists(fp):
            with open(fp) as f:
                for l in f:
                    try:
                        qs.add(json.loads(l.strip()).get('question', '').strip())
                    except: pass
    return qs


# Full-page question templates
PAGE_TEMPLATES = [
    "인사실무편람 {page}쪽에서 다루는 {topic}의 주요 내용은 무엇인가요?",
    "{topic} 관련 규정에서 핵심적으로 알아야 할 사항은 무엇인가요?",
    "{topic}에 대한 전반적인 내용을 요약해주세요.",
    "{topic} 규정의 주요 포인트를 설명해주세요.",
    "{category}에서 {topic}{이가} 중요한 이유는 무엇인가요?",
    "{topic}과 관련된 모든 규정을 정리해주세요.",
    "{topic}에 대해 교원이 꼭 알아야 할 내용은 무엇인가요?",
    "{topic}의 전체 구조와 내용을 설명해주세요.",
]

# Sub-topic combination templates
COMBO_TEMPLATES = [
    "{t1}와 {t2}의 관계는 어떻게 되나요?",
    "{t1}에서 {t2}에 대한 규정은 무엇인가요?",
    "{t1} 과정에서 {t2}{이가} 어떻게 적용되나요?",
    "{t1} 관련하여 {t2}의 기준은 무엇인가요?",
]

# Keyword-focused templates
KW_TEMPLATES = [
    "{kw} 관련 규정의 세부 내용은 어떻게 되나요?",
    "{kw}에 대해 교육공무원 인사실무편람에서는 어떻게 규정하고 있나요?",
    "{kw}{이가} 적용되는 구체적인 사례를 알려주세요.",
    "{kw}와 관련된 법적 근거는 무엇인가요?",
    "{kw}에 대한 세부 절차를 알려주세요.",
]


def get_page_topics(content):
    """Extract main topics from page content."""
    topics = []
    for m in re.finditer(r'^#{2,4}\s+(.+)$', content, re.MULTILINE):
        t = clean_topic(m.group(1))
        if t and len(t) >= 3 and not re.search(r'^\d+쪽$', t) and not re.search(r'[가-힣]\s[가-힣]\s[가-힣]', t):
            topics.append(t)
    # Also from bold headers
    for m in re.finditer(r'^\*\*(.{3,40}?)\*\*\s*$', content, re.MULTILINE):
        t = clean_topic(m.group(1))
        if t and len(t) >= 3 and t not in topics:
            topics.append(t)
    return topics[:6]


def get_page_keywords(content):
    """Extract important keywords from page."""
    kws = set()
    for pat in [r'교장|교감|교사|교원|교육감|교육부장관',
                r'임용|채용|전보|전직|승진|강임',
                r'휴직|복직|육아휴직|병가휴직|연수휴직',
                r'연가|병가|공가|특별휴가',
                r'징계|파면|해임|강등|정직|감봉|견책',
                r'호봉|승급|봉급|보수|수당',
                r'평정|근무성적|경력평정|가산점',
                r'기간제교원|산학겸임교사|명예교사']:
        for m in re.finditer(pat, content):
            kws.add(m.group(0))
    return list(kws)


def build_page_answer(content, topic, page, category):
    """Build an answer from full page content."""
    text = clean_html(content)
    text = re.sub(r'^#\s+\d+쪽\s*\n', '', text)

    # Get meaningful lines (skip empty, table seps, etc.)
    lines = []
    for l in text.split('\n'):
        s = l.strip()
        if not s or len(s) < 5:
            continue
        if s.startswith('|') and ('---' in s):
            continue
        if re.match(r'^[\-=_]{3,}$', s):
            continue
        lines.append(s)

    if not lines:
        return ""

    intro = f"{topic}에 대한 주요 내용을 안내드립니다."

    # Build structured answer
    body_parts = []

    # Take first ~10 meaningful lines
    for i, line in enumerate(lines[:12]):
        # Format headers
        hm = re.match(r'^#{1,4}\s+(.+)$', line)
        if hm:
            body_parts.append(f"\n**{clean_topic(hm.group(1))}**")
            continue

        # Format bold lines
        bm = re.match(r'^\*\*(.+?)\*\*(.*)$', line)
        if bm:
            body_parts.append(f"**{bm.group(1)}** {bm.group(2)}")
            continue

        # Blockquote
        if line.startswith('>'):
            note = line.lstrip('> ').strip()
            if note and len(note) > 5:
                body_parts.append(f"※ {note}")
            continue

        # Table rows - convert to text
        if line.startswith('|'):
            cells = [c.strip() for c in line.split('|') if c.strip()]
            if cells:
                body_parts.append(f"- {' / '.join(cells[:4])}")
            continue

        # Regular lines
        if line.startswith(('-', '•', '·')):
            body_parts.append(line)
        elif re.match(r'^\(?\d+[\)\.]', line) or re.match(r'^\([가나다]', line):
            body_parts.append(f"- {line}")
        else:
            body_parts.append(line)

    body = "\n".join(body_parts)

    # Law references
    laws = []
    for m in re.finditer(r'[「『](.+?)[」』]\s*(제\d+조)?', text):
        ref = f"「{m.group(1)}」"
        if m.group(2): ref += f" {m.group(2)}"
        if ref not in laws: laws.append(ref)

    ref = ""
    if laws:
        ref = f"\n\n**관련 근거:** {', '.join(laws[:4])}"

    answer = f"{intro}\n\n{body}{ref}"
    return answer


def quality_ok(entry):
    a, q, s = entry['answer'], entry['question'], entry['sources'][0]['text']
    if len(a) < 250 or len(q) < 15 or len(s) < 30:
        return False
    if re.search(r'<(?:br|div|p |span|table|img|input|align)', a + s, re.I):
        return False
    if '[ ]' in a or '________' in a or a.count('---') > 2:
        return False
    if re.search(r'[가-힣]\s[가-힣]\s[가-힣]\s[가-힣]', q):
        return False
    return True


def generate_pass4():
    existing = load_existing()
    print(f"Loaded {len(existing)} existing questions")

    pages = sorted(int(m.group(1)) for fn in os.listdir(MD_DIR)
                   if (m := re.match(r'(\d+)쪽\.md$', fn)))

    entries = []
    stats = defaultdict(int)
    cat_counts = defaultdict(int)

    for page in pages:
        path = os.path.join(MD_DIR, f"{page}쪽.md")
        with open(path) as f:
            content = f.read()

        if len(content.strip()) < 100 or is_form(content):
            stats['skip'] += 1
            continue

        cat_name, cat_num = get_category(page)
        topics = get_page_topics(content)
        keywords = get_page_keywords(content)

        if not topics:
            topics = [cat_name]

        main_topic = topics[0] if topics else cat_name

        # Strategy 1: Full-page overview questions
        for tmpl in random.sample(PAGE_TEMPLATES, min(2, len(PAGE_TEMPLATES))):
            q = tmpl.replace("{topic}", main_topic).replace("{page}", str(page)).replace("{category}", cat_name)
            q = fx(q, main_topic)

            if q in existing:
                stats['dup'] += 1
                continue

            answer = build_page_answer(content, main_topic, page, cat_name)
            if not answer or len(answer) < 250:
                stats['short'] += 1
                continue

            source_text = clean_html(content)[:500]
            source_text = re.sub(r'^#\s+\d+쪽\s*\n', '', source_text)

            entry = {
                "id": f"q_{cat_num}_{len(entries)+30001:05d}",
                "question": q,
                "answer": answer,
                "sources": [{"page": page, "title": main_topic, "text": source_text}],
                "category": cat_name,
                "subcategory": main_topic[:20],
                "keywords": list(set([main_topic] + keywords))[:7]
            }
            if quality_ok(entry):
                entries.append(entry)
                existing.add(q)
                cat_counts[cat_name] += 1
            else:
                stats['quality'] += 1

        # Strategy 2: Sub-topic combination questions
        if len(topics) >= 2:
            for i in range(min(2, len(topics)-1)):
                t1, t2 = topics[i], topics[i+1]
                if t1 == t2: continue
                tmpl = random.choice(COMBO_TEMPLATES)
                q = tmpl.replace("{t1}", t1).replace("{t2}", t2)
                q = fx(q, t2)

                if q in existing or len(q) < 15:
                    continue

                answer = build_page_answer(content, f"{t1}과 {t2}", page, cat_name)
                if not answer or len(answer) < 250:
                    continue

                source_text = clean_html(content)[:500]
                source_text = re.sub(r'^#\s+\d+쪽\s*\n', '', source_text)

                entry = {
                    "id": f"q_{cat_num}_{len(entries)+30001:05d}",
                    "question": q,
                    "answer": answer,
                    "sources": [{"page": page, "title": f"{t1}/{t2}", "text": source_text}],
                    "category": cat_name,
                    "subcategory": t1[:20],
                    "keywords": list(set([t1, t2] + keywords))[:7]
                }
                if quality_ok(entry):
                    entries.append(entry)
                    existing.add(q)
                    cat_counts[cat_name] += 1

        # Strategy 3: Keyword-based questions
        for kw in random.sample(keywords, min(2, len(keywords))):
            tmpl = random.choice(KW_TEMPLATES)
            q = tmpl.replace("{kw}", kw)
            q = fx(q, kw)

            if q in existing or len(q) < 15:
                continue

            answer = build_page_answer(content, kw, page, cat_name)
            if not answer or len(answer) < 250:
                continue

            source_text = clean_html(content)[:500]
            source_text = re.sub(r'^#\s+\d+쪽\s*\n', '', source_text)

            entry = {
                "id": f"q_{cat_num}_{len(entries)+30001:05d}",
                "question": q,
                "answer": answer,
                "sources": [{"page": page, "title": kw, "text": source_text}],
                "category": cat_name,
                "subcategory": main_topic[:20],
                "keywords": list(set([kw, main_topic] + keywords))[:7]
            }
            if quality_ok(entry):
                entries.append(entry)
                existing.add(q)
                cat_counts[cat_name] += 1

    print(f"\n=== Pass 4 Results ===")
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
        print(f"  Source: avg={sum(sl)//len(sl)}")
        print(f"  Pages: {len(set(e['sources'][0]['page'] for e in entries))}")

    with open(OUTPUT_FILE, 'w') as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
    print(f"\nWritten to {OUTPUT_FILE}")


if __name__ == '__main__':
    generate_pass4()
