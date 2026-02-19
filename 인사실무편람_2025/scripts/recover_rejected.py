#!/usr/bin/env python3
"""
탈락 데이터 복구 스크립트
========================
qa_rejected.jsonl에서 수정 가능한 항목을 자동 수정 후 재검증하여
양질의 데이터만 복구합니다.

수정 대상:
1. QUESTION_RAW_MARKDOWN: 질문에서 마크다운 서식 제거
2. QUESTION_QA_NUMBER: Q3. A2. 등 번호 접두사 제거
3. ANSWER_ESCAPED_MARKDOWN: 답변에서 이스케이프된 마크다운 복원
4. GRAMMAR_ERROR: 한국어 조사 오류 수정
5. SOURCE_TITLE_MEANINGLESS: 의미 없는 소스 제목 -> MD에서 추출
6. QUESTION_NONSENSE_VERB: "~을 하려면" 패턴 자연스럽게 수정
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

MD_DIR = "/home/user/menual/마크다운"
REJECTED_FILE = "/home/user/menual/qa_rejected.jsonl"
CLEAN_FILE = "/home/user/menual/qa_dataset_final.jsonl"
OUTPUT_RECOVERED = "/home/user/menual/qa_recovered.jsonl"
OUTPUT_STILL_REJECTED = "/home/user/menual/qa_still_rejected.jsonl"
OUTPUT_MERGED = "/home/user/menual/qa_dataset_verified.jsonl"
REPORT_FILE = "/home/user/menual/recovery_report.txt"

md_cache = {}


def load_md(page_num):
    if page_num in md_cache:
        return md_cache[page_num]
    filepath = os.path.join(MD_DIR, f"{page_num}쪽.md")
    if not os.path.exists(filepath):
        md_cache[page_num] = None
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    md_cache[page_num] = content
    return content


def extract_page_title(md_content):
    """MD 페이지에서 의미 있는 제목을 추출"""
    if not md_content:
        return None
    lines = md_content.strip().split('\n')
    for line in lines:
        line = line.strip()
        # 헤딩 패턴
        if line.startswith('#'):
            title = re.sub(r'^#+\s*', '', line).strip()
            if len(title) >= 3 and not re.match(r'^\d+$', title):
                return title
        # 볼드 텍스트 패턴
        m = re.search(r'\*\*(.{3,30})\*\*', line)
        if m:
            return m.group(1).strip()
        # 긴 텍스트 라인 (최소 5자)
        if len(line) >= 5 and not line.startswith('|') and not line.startswith('-'):
            clean = re.sub(r'[#*>|`]', '', line).strip()
            if len(clean) >= 3:
                return clean[:50]
    return None


# ─── Fix functions ───

def fix_question_raw_markdown(question):
    """질문에서 마크다운 서식 제거"""
    q = question
    # Remove ** bold markers
    q = re.sub(r'\*\*\s*', '', q)
    q = re.sub(r'\s*\*\*', '', q)
    # Remove leading special bullets
    q = re.sub(r'^[□◎●○■▶☞【\[\(]\s*', '', q)
    # Remove remaining markdown artifacts
    q = re.sub(r'^[>|`#]+\s*', '', q)
    # Clean up whitespace
    q = re.sub(r'\s+', ' ', q).strip()
    return q


def fix_question_qa_number(question):
    """Q3. A2. 등의 번호 접두사 제거"""
    q = re.sub(r'^[QA]\d+[\.\s:]\s*', '', question).strip()
    return q


def fix_answer_escaped_markdown(answer):
    """답변에서 이스케이프된 마크다운 복원"""
    a = answer
    a = a.replace('\\|', '|')
    a = a.replace('\\*', '*')
    a = a.replace('\\#', '#')
    a = a.replace('\\-', '-')
    a = a.replace('\\_', '_')
    return a


def fix_grammar_error(text):
    """한국어 조사 오류 수정 (받침 규칙 기반)"""
    # 받침 있는 글자 + 와 -> 과
    batchim_fixes = {
        '대상와': '대상과', '규정와': '규정과', '기관와': '기관과',
        '기간와': '기간과', '내용와': '내용과', '조건와': '조건과',
        '기준와': '기준과', '요건와': '요건과', '사항와': '사항과',
        '직원와': '직원과', '교원와': '교원과', '공무원와': '공무원과',
        '학생와': '학생과', '학교와': '학교과',  # 학교 ends in vowel, actually correct as 와
        '면직와': '면직과', '면직는': '면직은',
        '공석와': '공석과', '복직와': '복직과', '휴직와': '휴직과',
        '정원와': '정원과', '처분와': '처분과', '결과와': '결과과',  # 결과 ends in vowel
        '자격와': '자격과', '시험와': '시험과',
    }
    # 받침 없는 글자 + 과 -> 와
    no_batchim_fixes = {
        '자료과': '자료와', '교사과': '교사와', '기타과': '기타와',
        '사유과': '사유와', '대리과': '대리와', '배우자과': '배우자와',
        '위원회과': '위원회와', '부서과': '부서와',
    }

    # 실제로 받침 확인 후 수정 (잘못된 매핑 방지)
    def has_batchim(char):
        """한글 문자의 받침 여부 확인"""
        if '가' <= char <= '힣':
            code = ord(char) - 0xAC00
            return (code % 28) != 0
        return False

    # 정확한 매핑만 적용
    safe_fixes = {}
    for wrong, right in batchim_fixes.items():
        # 와 앞의 글자에 받침이 있어야 과로 바꿈
        target_char = wrong[wrong.index('와') - 1] if '와' in wrong else wrong[wrong.index('는') - 1]
        if has_batchim(target_char):
            safe_fixes[wrong] = right

    for wrong, right in no_batchim_fixes.items():
        target_char = wrong[wrong.index('과') - 1]
        if not has_batchim(target_char):
            safe_fixes[wrong] = right

    result = text
    for wrong, right in safe_fixes.items():
        result = result.replace(wrong, right)

    return result


def fix_question_nonsense_verb(question):
    """'~을 하려면 어떻게 해야 하나요?' 패턴을 자연스럽게 수정"""
    # "대상을 하려면" -> "대상에 해당하려면"
    # "서류를 하려면" -> "서류를 제출하려면"
    # "내용을 하려면" -> "내용을 확인하려면"
    replacements = [
        (r'대상을\s*하려면', '대상에 해당하려면'),
        (r'내용을\s*하려면', '내용을 확인하려면'),
        (r'사항을\s*하려면', '사항을 확인하려면'),
        (r'서류를\s*하려면', '서류를 제출하려면'),
        (r'기준을\s*하려면', '기준을 충족하려면'),
        (r'규정을\s*하려면', '규정을 적용하려면'),
    ]
    q = question
    for pat, repl in replacements:
        q = re.sub(pat, repl, q)
    return q


def fix_source_title(entry):
    """의미 없는 소스 제목을 MD 페이지에서 추출한 제목으로 교체"""
    sources = entry.get('sources', [])
    if not sources:
        return entry

    for src in sources:
        title = src.get('title', '')
        if title and (len(title) <= 2 or re.match(r'^[A-Z]?\d+$', title) or title.endswith(':')):
            page = src.get('page', 0)
            md_content = load_md(page)
            new_title = extract_page_title(md_content)
            if new_title:
                src['title'] = new_title
    return entry


# ─── Re-inspection (imported from inspect_qa.py logic) ───

def strip_particles(word):
    if len(word) <= 2:
        return word
    particles = [
        '으로서의', '으로써의', '으로부터', '에서부터',
        '에서는', '에서의', '으로는', '에게서', '으로서', '으로써',
        '에서도', '까지는', '부터는', '만으로', '에게는', '과의', '와의',
        '으로', '에서', '에게', '부터', '까지', '에는', '에도',
        '이란', '이라', '에의', '란', '라면', '이면',
        '인가요', '되나요', '하나요', '인지요', '습니까', '입니까',
        '은', '는', '이', '가', '을', '를', '에', '의', '도',
        '로', '과', '와', '나', '며', '야', '요', '고',
    ]
    for p in particles:
        if word.endswith(p) and len(word) > len(p) + 1:
            return word[:-len(p)]
    return word


def extract_stems(text):
    words = re.findall(r'[가-힣]{2,}', text)
    stems = set()
    for w in words:
        stem = strip_particles(w)
        if len(stem) >= 2:
            stems.add(stem)
        if len(w) >= 3:
            stems.add(w)
    return stems


def normalize_text(text):
    if not text:
        return ""
    t = re.sub(r'\*\*', '', text)
    t = re.sub(r'[#>|`]', '', t)
    t = t.replace('\u201c', '"').replace('\u201d', '"')
    t = t.replace('\u2018', "'").replace('\u2019', "'")
    t = t.replace('「', '"').replace('」', '"')
    t = t.replace('『', '"').replace('』', '"')
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def normalize_for_source_match(text):
    if not text:
        return ""
    t = normalize_text(text)
    t = re.sub(r'[^\w\s가-힣]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def check_source_text_in_md(source_text, md_content):
    if not source_text or not md_content:
        return False, 0.0
    if source_text.strip() in md_content:
        return True, 1.0
    norm_source = normalize_text(source_text)
    norm_md = normalize_text(md_content)
    if len(norm_source) > 10 and norm_source in norm_md:
        return True, 1.0
    agg_source = normalize_for_source_match(source_text)
    agg_md = normalize_for_source_match(md_content)
    if len(agg_source) > 10 and agg_source in agg_md:
        return True, 0.95
    source_lines = [l.strip() for l in source_text.split('\n') if l.strip() and len(l.strip()) > 5]
    if not source_lines:
        if len(agg_source) >= 5:
            src_words = set(agg_source.split())
            md_words = set(agg_md.split())
            if src_words and len(src_words & md_words) / len(src_words) > 0.5:
                return True, 0.7
        return False, 0.0
    matched_lines = 0
    for line in source_lines:
        norm_line = normalize_for_source_match(line)
        if len(norm_line) < 5:
            matched_lines += 1
            continue
        if norm_line in agg_md:
            matched_lines += 1
        else:
            words = norm_line.split()
            if len(words) >= 3:
                chunk = ' '.join(words[:min(5, len(words))])
                if chunk in agg_md:
                    matched_lines += 0.7
                else:
                    chunk2 = ' '.join(words[:min(3, len(words))])
                    if chunk2 in agg_md:
                        matched_lines += 0.4
    ratio = matched_lines / len(source_lines) if source_lines else 0
    return ratio >= 0.5, ratio


def is_form_page(md_content):
    if not md_content:
        return False
    indicators = [
        r'서식\s*[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩivx\d]',
        r'□\s+[가-힣]',
        r'<center>',
        r'\(인\)',
        r'성\s*명\s*:.*\(인\)',
    ]
    count = sum(1 for pat in indicators if re.search(pat, md_content))
    first_lines = md_content.split('\n')[:5]
    first_text = ' '.join(first_lines)
    if re.search(r'서식\s*[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩivx\d]', first_text):
        count += 3
    if md_content.strip().endswith('귀하') or re.search(r'[가-힣]+장?\s*귀\s*하', md_content):
        count += 1
    return count >= 3


def is_reference_table(md_content, entry):
    if not md_content:
        return False
    country_indicators = ['아포스티유', '가입국', '리스트', '뉴질랜드', '마샬군도']
    return sum(1 for ind in country_indicators if ind in md_content) >= 2


def reinspect_entry(entry, existing_answer_keys):
    """수정된 엔트리를 재검증"""
    issues = []
    entry_id = entry.get('id', 'unknown')
    question = entry.get('question', '')
    answer = entry.get('answer', '')
    sources = entry.get('sources', [])

    # Basic checks
    if not question or len(question) < 10:
        issues.append("QUESTION_TOO_SHORT")
    if not answer or len(answer) < 100:
        issues.append("ANSWER_TOO_SHORT")
    if not sources:
        issues.append("NO_SOURCES")

    # HTML check
    if re.search(r'<(?:br|div|center|table|tr|td|th|p|h[1-6])\b', answer, re.I):
        issues.append("HTML_IN_ANSWER")
    if re.search(r'<(?:br|div|center|table|tr|td|th|p|h[1-6])\b', question, re.I):
        issues.append("HTML_IN_QUESTION")

    # Duplicate check against existing clean entries
    norm_ans = normalize_for_source_match(answer)
    if len(norm_ans) >= 50:
        key = norm_ans[:200]
        if key in existing_answer_keys:
            issues.append("DUPLICATE_ANSWER")

    # Source-level checks
    all_md_content = ""
    for src in sources:
        page = src.get('page', 0)
        source_text = src.get('text', '')
        md_content = load_md(page)
        if md_content is None:
            issues.append(f"SOURCE_MISSING:page={page}")
            continue
        all_md_content += "\n" + md_content

        if source_text and len(source_text.strip()) > 10:
            matched, ratio = check_source_text_in_md(source_text, md_content)
            if not matched:
                issues.append(f"SOURCE_TEXT_MISMATCH:page={page},ratio={ratio:.2f}")
        elif not source_text or len(source_text.strip()) < 10:
            issues.append(f"SOURCE_TEXT_EMPTY:page={page}")

        if is_form_page(md_content):
            issues.append(f"FORM_CONTENT:page={page}")

        if is_reference_table(md_content, entry):
            issues.append(f"REFERENCE_TABLE:page={page}")

    # Question quality checks
    if re.search(r'\*\*\s*[가-힣]', question) or re.search(r'[가-힣]\s*\*\*', question):
        issues.append("QUESTION_RAW_MARKDOWN")
    if re.search(r'^[□◎●○■▶☞【\[\(]\s', question):
        issues.append("QUESTION_RAW_MARKDOWN")

    if len(question) > 120:
        q_endings = ['요?', '까?', '나요?', '는지?', '가요?', '세요?', '인지?', '습니까?']
        if not any(question.rstrip().endswith(e) for e in q_endings):
            issues.append("QUESTION_PASTED_CONTENT")
        if len(question) > 150:
            issues.append("QUESTION_PASTED_CONTENT")

    if re.match(r'^[QA]\d+[\.\s]', question):
        issues.append("QUESTION_QA_NUMBER")

    if re.match(r'^(다음|아래|위)(의|에|은|는)', question):
        issues.append("QUESTION_VAGUE_REFERENCE")

    nonsense_patterns = [
        r'대상을\s*하려면', r'내용을\s*하려면', r'사항을\s*하려면',
        r'서류를\s*하려면', r'기준을\s*하려면', r'규정을\s*하려면',
    ]
    for pat in nonsense_patterns:
        if re.search(pat, question):
            issues.append("QUESTION_NONSENSE_VERB")
            break

    if re.search(r'(과의?\s*관계|와의?\s*관계|의\s*관계)', question):
        answer_first = answer[:300]
        rel_phrases = ['관계가', '관련이', '연관', '연계', '영향을 미',
                       '상호', '함께', '밀접', '연결']
        if not any(p in answer_first for p in rel_phrases):
            issues.append("QUESTION_FAKE_RELATION")

    if re.search(r'(최근\s*변경|변경\s*사항|개정\s*내용|변경된\s*점)', question):
        if all_md_content and not re.search(r'(변경|개정|신설|삭제|수정|개편|종전|현행)', all_md_content):
            issues.append("QUESTION_TEMPLATE_MISMATCH")

    # Grammar error check
    batchim_wa_errors = ['대상와', '규정와', '기관와', '기간와', '내용와',
                         '조건와', '기준와', '요건와', '사항와', '직원와',
                         '교원와', '공무원와', '학생와', '면직와',
                         '면직는', '공석와', '복직와', '휴직와', '정원와',
                         '처분와', '자격와', '시험와']
    no_batchim_gwa_errors = ['자료과', '교사과', '기타과', '사유과',
                              '대리과', '배우자과', '위원회과', '부서과']
    for err in batchim_wa_errors:
        if err in question or err in answer:
            issues.append("GRAMMAR_ERROR")
            break
    for err in no_batchim_gwa_errors:
        if err in question or err in answer:
            issues.append("GRAMMAR_ERROR")
            break

    # Answer-question relevance
    q_stems = extract_stems(question)
    generic = {'무엇', '어떤', '어떻게', '대해', '설명', '알려', '있나', '인가',
               '관련', '규정', '내용', '경우', '사항', '해당', '따른', '대한',
               '주요', '구체', '자세', '어떠', '가능', '필요', '어떤것',
               '정리', '알고', '싶은', '궁금', '차이', '비교', '각각', '모든',
               '어떻', '하는', '되는', '있는', '없는', '것이', '점이',
               '처리', '절차', '방법', '기준', '조건', '요건'}
    q_topic_stems = {s for s in q_stems if s not in generic and len(s) >= 2}

    if q_topic_stems:
        a_stems = extract_stems(answer)
        matched = sum(1 for s in q_topic_stems if s in a_stems or any(s in a for a in a_stems))
        ratio = matched / len(q_topic_stems) if q_topic_stems else 0
        substring_matched = sum(1 for s in q_topic_stems if len(s) >= 2 and s in answer)
        substring_ratio = substring_matched / len(q_topic_stems)
        best_ratio = max(ratio, substring_ratio)
        if best_ratio < 0.15 and len(q_topic_stems) >= 3:
            issues.append(f"ANSWER_QUESTION_DISCONNECT:ratio={best_ratio:.2f}")

        # Topic mismatch check
        a_first_stems = extract_stems(answer[:300])
        a_first_topics = {s for s in a_first_stems if s not in generic and len(s) >= 2}
        if a_first_topics:
            overlap = q_topic_stems & a_first_topics
            sub_overlap = sum(1 for qs in q_topic_stems if any(qs in at or at in qs for at in a_first_topics))
            text_overlap = sum(1 for qs in q_topic_stems if qs in answer[:300])
            total_matches = len(overlap) + sub_overlap + text_overlap
            if total_matches == 0 and len(q_topic_stems) >= 2 and len(a_first_topics) >= 2:
                issues.append("ANSWER_TOPIC_MISMATCH")

    # Page content match
    if all_md_content:
        q_stems2 = extract_stems(question)
        generic2 = {'무엇', '어떤', '어떻게', '대해', '설명', '알려', '있나', '인가',
                    '관련', '규정', '내용', '경우', '사항', '해당', '따른', '대한',
                    '주요', '구체', '자세', '어떠', '가능', '필요',
                    '처리', '절차', '방법', '기준', '조건', '요건', '정의',
                    '종류', '범위', '특징', '목적', '대상', '기간', '시기'}
        q_topic2 = {s for s in q_stems2 if s not in generic2 and len(s) >= 3}
        if q_topic2 and len(q_topic2) >= 2:
            found = sum(1 for s in q_topic2 if s in all_md_content)
            if found == 0:
                issues.append("QUESTION_TOPIC_NOT_ON_PAGE")

    # Source title check
    if sources:
        title = sources[0].get('title', '')
        if title and (len(title) <= 2 or re.match(r'^[A-Z]?\d+$', title) or title.endswith(':')):
            issues.append("SOURCE_TITLE_MEANINGLESS")

    # Escaped markdown
    if '\\|' in answer or '\\*' in answer:
        issues.append("ANSWER_ESCAPED_MARKDOWN")

    # Form template data
    form_samples = ['이순신', '홍길동', '○○', '△△', '□□', '☆☆',
                    '20**', '19**', '20  .  .', '(인)', '귀하']
    form_hit = sum(1 for s in form_samples if s in answer)
    if form_hit >= 2:
        issues.append("ANSWER_FORM_TEMPLATE_DATA")

    # Classify severity
    critical_patterns = [
        'SOURCE_MISSING', 'SOURCE_TEXT_MISMATCH', 'FORM_CONTENT',
        'REFERENCE_TABLE', 'ANSWER_QUESTION_DISCONNECT', 'ANSWER_TOPIC_MISMATCH',
        'QUESTION_TOPIC_NOT_ON_PAGE', 'HTML_IN_ANSWER', 'HTML_IN_QUESTION',
        'QUESTION_EMPTY', 'ANSWER_EMPTY', 'NO_SOURCES', 'SOURCE_TEXT_EMPTY',
        'QUESTION_FAKE_RELATION', 'GRAMMAR_ERROR', 'DUPLICATE_ANSWER',
        'QUESTION_RAW_MARKDOWN', 'QUESTION_PASTED_CONTENT',
        'QUESTION_CONTINUATION', 'ANSWER_STARTS_WITH_CONTINUATION',
        'SOURCE_TITLE_MEANINGLESS', 'ANSWER_ESCAPED_MARKDOWN',
        'ANSWER_FORM_TEMPLATE_DATA', 'QUESTION_QA_NUMBER',
        'QUESTION_VAGUE_REFERENCE', 'QUESTION_NONSENSE_VERB'
    ]

    critical = [i for i in issues if any(p in i for p in critical_patterns)]
    return critical, issues


def apply_fixes(entry):
    """엔트리에 수정 적용. 수정된 항목 목록 반환."""
    fixes_applied = []
    reasons = set(r.split(':')[0] for r in entry.get('_rejection_reasons', []))

    # 1. QUESTION_RAW_MARKDOWN
    old_q = entry['question']
    new_q = fix_question_raw_markdown(old_q)
    if new_q != old_q:
        entry['question'] = new_q
        fixes_applied.append('QUESTION_RAW_MARKDOWN')

    # 2. QUESTION_QA_NUMBER
    old_q = entry['question']
    new_q = fix_question_qa_number(old_q)
    if new_q != old_q:
        entry['question'] = new_q
        fixes_applied.append('QUESTION_QA_NUMBER')

    # 3. ANSWER_ESCAPED_MARKDOWN
    old_a = entry['answer']
    new_a = fix_answer_escaped_markdown(old_a)
    if new_a != old_a:
        entry['answer'] = new_a
        fixes_applied.append('ANSWER_ESCAPED_MARKDOWN')

    # 4. GRAMMAR_ERROR - fix in both question and answer
    old_q = entry['question']
    new_q = fix_grammar_error(old_q)
    old_a = entry['answer']
    new_a = fix_grammar_error(old_a)
    if new_q != old_q or new_a != old_a:
        entry['question'] = new_q
        entry['answer'] = new_a
        fixes_applied.append('GRAMMAR_ERROR')

    # 5. SOURCE_TITLE_MEANINGLESS
    if 'SOURCE_TITLE_MEANINGLESS' in reasons:
        old_titles = [s.get('title', '') for s in entry.get('sources', [])]
        entry = fix_source_title(entry)
        new_titles = [s.get('title', '') for s in entry.get('sources', [])]
        if old_titles != new_titles:
            fixes_applied.append('SOURCE_TITLE_MEANINGLESS')

    # 6. QUESTION_NONSENSE_VERB
    old_q = entry['question']
    new_q = fix_question_nonsense_verb(old_q)
    if new_q != old_q:
        entry['question'] = new_q
        fixes_applied.append('QUESTION_NONSENSE_VERB')

    return entry, fixes_applied


def main():
    print("=" * 70)
    print("탈락 데이터 복구 스크립트")
    print("=" * 70)

    # Load existing clean entries for duplicate checking
    print("\n기존 통과 데이터 로드 중...")
    clean_entries = []
    existing_answer_keys = set()
    with open(CLEAN_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                e = json.loads(line)
                clean_entries.append(e)
                norm_ans = normalize_for_source_match(e.get('answer', ''))
                if len(norm_ans) >= 50:
                    existing_answer_keys.add(norm_ans[:200])
    print(f"  기존 통과: {len(clean_entries)}개")

    # Load rejected entries
    print("탈락 데이터 로드 중...")
    rejected = []
    with open(REJECTED_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rejected.append(json.loads(line))
    print(f"  탈락 데이터: {len(rejected)}개")

    # Apply fixes and re-inspect
    recovered = []
    still_rejected = []
    fix_counter = Counter()
    recovery_reason = Counter()
    original_reasons = Counter()

    print("\n수정 및 재검증 진행 중...")
    for i, entry in enumerate(rejected):
        if (i + 1) % 500 == 0:
            print(f"  {i+1}/{len(rejected)} 완료... (복구: {len(recovered)}, 재탈락: {len(still_rejected)})")

        orig_reasons = entry.get('_rejection_reasons', [])
        for r in orig_reasons:
            original_reasons[r.split(':')[0]] += 1

        # Apply fixes
        fixed_entry, fixes = apply_fixes(entry)
        for f in fixes:
            fix_counter[f] += 1

        # Remove internal fields before re-inspection
        clean_entry = {k: v for k, v in fixed_entry.items() if not k.startswith('_')}

        # Re-inspect
        critical, all_issues = reinspect_entry(clean_entry, existing_answer_keys)

        if not critical:
            # Recovered! Add to clean set and update answer keys
            recovered.append(clean_entry)
            norm_ans = normalize_for_source_match(clean_entry.get('answer', ''))
            if len(norm_ans) >= 50:
                existing_answer_keys.add(norm_ans[:200])
            for r in orig_reasons:
                recovery_reason[r.split(':')[0]] += 1
        else:
            clean_entry['_rejection_reasons'] = critical
            still_rejected.append(clean_entry)

    print(f"\n{'='*60}")
    print("복구 결과")
    print(f"{'='*60}")
    print(f"  원본 탈락: {len(rejected)}개")
    print(f"  복구 성공: {len(recovered)}개 ({len(recovered)/len(rejected)*100:.1f}%)")
    print(f"  여전히 탈락: {len(still_rejected)}개")
    print(f"  기존 통과: {len(clean_entries)}개")
    print(f"  최종 합계: {len(clean_entries) + len(recovered)}개")

    # Write outputs
    print("\n파일 출력 중...")
    with open(OUTPUT_RECOVERED, 'w', encoding='utf-8') as f:
        for entry in recovered:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    with open(OUTPUT_STILL_REJECTED, 'w', encoding='utf-8') as f:
        for entry in still_rejected:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    # Merge: clean + recovered
    merged = clean_entries + recovered
    with open(OUTPUT_MERGED, 'w', encoding='utf-8') as f:
        for entry in merged:
            out = {k: v for k, v in entry.items() if not k.startswith('_')}
            f.write(json.dumps(out, ensure_ascii=False) + '\n')

    # Report
    report = []
    report.append("=" * 70)
    report.append("탈락 데이터 복구 보고서")
    report.append("=" * 70)
    report.append(f"\n원본 탈락: {len(rejected)}개")
    report.append(f"복구 성공: {len(recovered)}개 ({len(recovered)/len(rejected)*100:.1f}%)")
    report.append(f"여전히 탈락: {len(still_rejected)}개")
    report.append(f"기존 통과: {len(clean_entries)}개")
    report.append(f"최종 합계: {len(clean_entries) + len(recovered)}개")

    report.append(f"\n{'='*50}")
    report.append("수정 적용 통계")
    report.append(f"{'='*50}")
    for fix, cnt in fix_counter.most_common():
        report.append(f"  {fix}: {cnt}건 수정")

    report.append(f"\n{'='*50}")
    report.append("원래 사유별 복구 성공 수")
    report.append(f"{'='*50}")
    for reason in sorted(original_reasons.keys()):
        orig = original_reasons[reason]
        recov = recovery_reason.get(reason, 0)
        rate = recov / orig * 100 if orig > 0 else 0
        report.append(f"  {reason}: {recov}/{orig} 복구 ({rate:.1f}%)")

    report.append(f"\n{'='*50}")
    report.append("여전히 탈락 사유 통계")
    report.append(f"{'='*50}")
    still_counter = Counter()
    for e in still_rejected:
        for r in e.get('_rejection_reasons', []):
            still_counter[r.split(':')[0]] += 1
    for reason, cnt in still_counter.most_common():
        report.append(f"  {reason}: {cnt}개")

    # Recovered samples
    report.append(f"\n{'='*50}")
    report.append("복구 샘플 (15개)")
    report.append(f"{'='*50}")
    import random
    random.seed(42)
    sample = random.sample(recovered, min(15, len(recovered)))
    for entry in sample:
        report.append(f"\nID: {entry['id']}")
        report.append(f"  Q: {entry['question'][:100]}")
        report.append(f"  A길이: {len(entry.get('answer', ''))}자")
        page = entry['sources'][0]['page'] if entry.get('sources') else 'N/A'
        report.append(f"  출처: page {page}")

    report_text = '\n'.join(report)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"\n{report_text}")
    print(f"\n출력 파일:")
    print(f"  복구 데이터: {OUTPUT_RECOVERED}")
    print(f"  여전히 탈락: {OUTPUT_STILL_REJECTED}")
    print(f"  최종 병합: {OUTPUT_MERGED}")
    print(f"  보고서: {REPORT_FILE}")


if __name__ == '__main__':
    main()
