#!/usr/bin/env python3
"""
전수조사 (Full Entry-by-Entry Inspection) Script v2
====================================================
qa_dataset_final.jsonl의 모든 엔트리를 하나씩 검증합니다.

v2 개선사항:
- 한국어 조사(particles) 제거 후 어간 기반 비교
- 출처 텍스트 매칭 시 따옴표/특수문자 정규화 강화
- 오탐(false positive) 감소를 위한 임계값 조정
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

MD_DIR = "/home/user/menual/마크다운"
INPUT_FILE = "/home/user/menual/qa_dataset_final.jsonl"
OUTPUT_CLEAN = "/home/user/menual/qa_dataset_inspected.jsonl"
OUTPUT_REJECTED = "/home/user/menual/qa_rejected.jsonl"
REPORT_FILE = "/home/user/menual/inspection_report.txt"

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


def strip_particles(word):
    """Strip Korean particles from end of a word to get the stem."""
    if len(word) <= 2:
        return word
    # Order matters: longest particles first
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
    """Extract Korean word stems from text, stripping particles."""
    words = re.findall(r'[가-힣]{2,}', text)
    stems = set()
    for w in words:
        stem = strip_particles(w)
        if len(stem) >= 2:
            stems.add(stem)
        # Also add the original if long enough (compound words)
        if len(w) >= 3:
            stems.add(w)
    return stems


def normalize_text(text):
    """Normalize text for comparison."""
    if not text:
        return ""
    t = re.sub(r'\*\*', '', text)
    t = re.sub(r'[#>|`]', '', t)
    # Normalize quotes
    t = t.replace('\u201c', '"').replace('\u201d', '"')  # ""
    t = t.replace('\u2018', "'").replace('\u2019', "'")  # ''
    t = t.replace('「', '"').replace('」', '"')
    t = t.replace('『', '"').replace('』', '"')
    # Normalize whitespace
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def normalize_for_source_match(text):
    """Aggressive normalization specifically for source text matching."""
    if not text:
        return ""
    t = normalize_text(text)
    # Remove all punctuation and formatting
    t = re.sub(r'[^\w\s가-힣]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def check_source_text_in_md(source_text, md_content):
    """Check if source text exists in MD file."""
    if not source_text or not md_content:
        return False, 0.0

    # Strategy 1: Direct substring match
    if source_text.strip() in md_content:
        return True, 1.0

    # Strategy 2: Normalized match
    norm_source = normalize_text(source_text)
    norm_md = normalize_text(md_content)
    if len(norm_source) > 10 and norm_source in norm_md:
        return True, 1.0

    # Strategy 3: Aggressive normalization
    agg_source = normalize_for_source_match(source_text)
    agg_md = normalize_for_source_match(md_content)
    if len(agg_source) > 10 and agg_source in agg_md:
        return True, 0.95

    # Strategy 4: Line-by-line match
    source_lines = [l.strip() for l in source_text.split('\n') if l.strip() and len(l.strip()) > 5]
    if not source_lines:
        # Very short source text - try whole chunk
        if len(agg_source) >= 5:
            # Check if at least some words match
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
            # Try chunk matching
            words = norm_line.split()
            if len(words) >= 3:
                chunk = ' '.join(words[:min(5, len(words))])
                if chunk in agg_md:
                    matched_lines += 0.7
                else:
                    # Try even smaller chunk
                    chunk2 = ' '.join(words[:min(3, len(words))])
                    if chunk2 in agg_md:
                        matched_lines += 0.4

    ratio = matched_lines / len(source_lines) if source_lines else 0
    return ratio >= 0.5, ratio


def is_form_page(md_content):
    """Detect if page is a form/서식 page."""
    if not md_content:
        return False

    indicators = [
        r'서식\s*[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩivx\d]',
        r'□\s+[가-힣]',  # Checkbox items with Korean text
        r'<center>',
        r'\(인\)',
        r'성\s*명\s*:.*\(인\)',
    ]

    count = sum(1 for pat in indicators if re.search(pat, md_content))

    # Check title area for 서식
    first_lines = md_content.split('\n')[:5]
    first_text = ' '.join(first_lines)
    if re.search(r'서식\s*[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩivx\d]', first_text):
        count += 3

    # Strong indicator: form header pattern (귀하 at end)
    if md_content.strip().endswith('귀하') or re.search(r'[가-힣]+장?\s*귀\s*하', md_content):
        count += 1

    return count >= 3


def is_reference_table(md_content, entry):
    """Detect if entry is from a meaningless reference table."""
    if not md_content:
        return False

    # Country list detection
    country_indicators = ['아포스티유', '가입국', '리스트', '뉴질랜드', '마샬군도']
    if sum(1 for ind in country_indicators if ind in md_content) >= 2:
        return True

    return False


def check_question_quality(question, answer, md_content):
    """Check question quality."""
    issues = []
    if not question:
        issues.append("QUESTION_EMPTY")
        return issues

    # Raw markdown or special formatting in question
    if re.search(r'\*\*\s*[가-힣]', question) or re.search(r'[가-힣]\s*\*\*', question):
        issues.append("QUESTION_RAW_MARKDOWN")
    if re.search(r'^[□◎●○■▶☞【\[\(]\s', question):
        issues.append("QUESTION_RAW_MARKDOWN")

    # Very long questions (likely pasted from source)
    if len(question) > 120:
        # Check if it's a natural question or pasted content
        q_endings = ['요?', '까?', '나요?', '는지?', '가요?', '세요?', '인지?', '습니까?']
        if not any(question.rstrip().endswith(e) for e in q_endings):
            issues.append("QUESTION_PASTED_CONTENT")
        # Even if it ends with a question mark, very long = suspicious
        if len(question) > 150:
            issues.append("QUESTION_PASTED_CONTENT")

    # Question with "(계속)" indicating continuation page
    if '(계속)' in question or '계속)' in question:
        issues.append("QUESTION_CONTINUATION")

    # Source text starting with "(계속)" - may lack context
    if answer and answer.strip().startswith('(계속)'):
        issues.append("ANSWER_STARTS_WITH_CONTINUATION")

    # Questions starting with Q&A numbering from handbook
    if re.match(r'^[QA]\d+[\.\s]', question):
        issues.append("QUESTION_QA_NUMBER")

    # Questions with vague references ("다음의", "위의", "아래의")
    if re.match(r'^(다음|아래|위)(의|에|은|는)', question):
        issues.append("QUESTION_VAGUE_REFERENCE")

    # Questions with nonsensical verb pairing "~을 하려면" with non-actionable nouns
    # e.g., "지급제외대상을 하려면" - 대상 can't be "done"
    nonsense_patterns = [
        r'대상을\s*하려면', r'내용을\s*하려면', r'사항을\s*하려면',
        r'서류를\s*하려면', r'기준을\s*하려면', r'규정을\s*하려면',
    ]
    for pat in nonsense_patterns:
        if re.search(pat, question):
            issues.append("QUESTION_NONSENSE_VERB")
            break

    # Fake "관계" questions between unrelated topics
    if re.search(r'(과의?\s*관계|와의?\s*관계|의\s*관계)', question):
        # If answer doesn't actually explain HOW two things relate
        # but just lists content from both topics
        answer_first = answer[:300]
        rel_phrases = ['관계가', '관련이', '연관', '연계', '영향을 미',
                       '상호', '함께', '밀접', '연결']
        has_relation_explanation = any(p in answer_first for p in rel_phrases)
        if not has_relation_explanation:
            issues.append("QUESTION_FAKE_RELATION")

    # Template mismatch - asking about changes when content doesn't discuss changes
    if re.search(r'(최근\s*변경|변경\s*사항|개정\s*내용|변경된\s*점)', question):
        if md_content and not re.search(r'(변경|개정|신설|삭제|수정|개편|종전|현행)', md_content):
            issues.append("QUESTION_TEMPLATE_MISMATCH")

    # Grammar errors - batchim + wrong particle
    # Words ending in consonant (받침) should use 과/은/이/을 not 와/는/가/를
    batchim_wa_errors = ['대상와', '규정와', '기관와', '기간와', '내용와',
                         '조건와', '기준와', '요건와', '사항와', '직원와',
                         '교원와', '공무원와', '학생와', '학교와', '면직와',
                         '면직는', '공석와', '복직와', '휴직와', '정원와',
                         '처분와', '결과와', '자격와', '시험와']
    # Also check: words NOT ending in 받침 should use 와 not 과
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

    return issues


def check_answer_question_relevance(question, answer, sources):
    """Check if answer addresses the question using stem-based matching."""
    issues = []
    if not question or not answer:
        if not answer:
            issues.append("ANSWER_EMPTY")
        return issues

    # Extract stems from question
    q_stems = extract_stems(question)

    # Remove very common/generic words that appear in any QA
    generic = {'무엇', '어떤', '어떻게', '대해', '설명', '알려', '있나', '인가',
               '관련', '규정', '내용', '경우', '사항', '해당', '따른', '대한',
               '주요', '구체', '자세', '어떠', '가능', '필요', '어떤것',
               '정리', '알고', '싶은', '궁금', '차이', '비교', '각각', '모든',
               '어떻', '하는', '되는', '있는', '없는', '것이', '점이',
               '처리', '절차', '방법', '기준', '조건', '요건'}
    q_topic_stems = {s for s in q_stems if s not in generic and len(s) >= 2}

    if not q_topic_stems:
        return issues

    # Extract stems from answer
    a_stems = extract_stems(answer)

    # Check overlap
    matched = sum(1 for s in q_topic_stems if s in a_stems or any(s in a for a in a_stems))
    ratio = matched / len(q_topic_stems) if q_topic_stems else 0

    # Also check if question stems appear as substrings in answer text
    substring_matched = sum(1 for s in q_topic_stems if len(s) >= 2 and s in answer)
    substring_ratio = substring_matched / len(q_topic_stems)

    # Use the better of two ratios
    best_ratio = max(ratio, substring_ratio)

    if best_ratio < 0.15 and len(q_topic_stems) >= 3:
        issues.append(f"ANSWER_QUESTION_DISCONNECT:ratio={best_ratio:.2f}")

    # Topic mismatch: first part of answer should mention the question topic
    a_first_stems = extract_stems(answer[:300])
    a_first_topics = {s for s in a_first_stems if s not in generic and len(s) >= 2}
    if q_topic_stems and a_first_topics:
        overlap = q_topic_stems & a_first_topics
        # Also check substring overlap (e.g., 교육공무원 contains 공무원)
        sub_overlap = sum(1 for qs in q_topic_stems if any(qs in at or at in qs for at in a_first_topics))
        # Also check if any question topic word appears in the first 300 chars of answer
        text_overlap = sum(1 for qs in q_topic_stems if qs in answer[:300])
        total_matches = len(overlap) + sub_overlap + text_overlap
        if total_matches == 0 and len(q_topic_stems) >= 2 and len(a_first_topics) >= 2:
            issues.append("ANSWER_TOPIC_MISMATCH")

    return issues


def check_page_content_match(question, answer, sources, md_content):
    """Check if question actually relates to the page content."""
    issues = []
    if not md_content or not sources:
        return issues

    # Check if source title exists in page
    source_title = sources[0].get('title', '') if sources else ''
    if source_title and len(source_title) > 5:
        title_stems = extract_stems(source_title)
        md_stems = extract_stems(md_content)
        title_match = sum(1 for s in title_stems if s in md_stems or s in md_content)
        if title_match == 0 and len(title_stems) >= 2:
            issues.append("SOURCE_TITLE_NOT_IN_PAGE")

    # Check if question's topic appears on the page
    q_stems = extract_stems(question)
    generic = {'무엇', '어떤', '어떻게', '대해', '설명', '알려', '있나', '인가',
               '관련', '규정', '내용', '경우', '사항', '해당', '따른', '대한',
               '주요', '구체', '자세', '어떠', '가능', '필요',
               '처리', '절차', '방법', '기준', '조건', '요건', '정의',
               '종류', '범위', '특징', '목적', '대상', '기간', '시기'}
    q_topic_stems = {s for s in q_stems if s not in generic and len(s) >= 3}

    if q_topic_stems and len(q_topic_stems) >= 2:
        # Check how many topic stems appear in the MD page content
        found = sum(1 for s in q_topic_stems if s in md_content)
        if found == 0:
            issues.append("QUESTION_TOPIC_NOT_ON_PAGE")

    return issues


def detect_duplicate_answers(entries):
    """Find entries with duplicate or near-duplicate answers."""
    answer_map = defaultdict(list)
    for entry in entries:
        ans = normalize_for_source_match(entry.get('answer', ''))
        if len(ans) < 50:
            continue
        key = ans[:200]
        answer_map[key].append(entry['id'])

    duplicate_ids = set()
    for key, ids in answer_map.items():
        if len(ids) > 1:
            for dup_id in ids[1:]:
                duplicate_ids.add(dup_id)
    return duplicate_ids


def check_answer_is_source_copy(answer, source_text):
    """Check if answer is just a copy of source text."""
    if not answer or not source_text:
        return False
    norm_ans = normalize_for_source_match(answer)
    norm_src = normalize_for_source_match(source_text)
    if not norm_ans or not norm_src:
        return False
    ratio = SequenceMatcher(None, norm_ans[:500], norm_src[:500]).ratio()
    return ratio > 0.85


def inspect_entry(entry, duplicate_ids):
    """Inspect a single QA entry."""
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

    # Duplicate
    if entry_id in duplicate_ids:
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

        # Source text match
        if source_text and len(source_text.strip()) > 10:
            matched, ratio = check_source_text_in_md(source_text, md_content)
            if not matched:
                issues.append(f"SOURCE_TEXT_MISMATCH:page={page},ratio={ratio:.2f}")
        elif not source_text or len(source_text.strip()) < 10:
            issues.append(f"SOURCE_TEXT_EMPTY:page={page}")

        # Form content
        if is_form_page(md_content):
            issues.append(f"FORM_CONTENT:page={page}")

        # Reference table
        if is_reference_table(md_content, entry):
            issues.append(f"REFERENCE_TABLE:page={page}")

    # Question quality
    q_issues = check_question_quality(question, answer, all_md_content)
    issues.extend(q_issues)

    # Answer-question relevance
    aq_issues = check_answer_question_relevance(question, answer, sources)
    issues.extend(aq_issues)

    # Page content match
    if all_md_content:
        pc_issues = check_page_content_match(question, answer, sources, all_md_content)
        issues.extend(pc_issues)

    # Source copy check
    if sources and sources[0].get('text'):
        all_source_text = ' '.join(s.get('text', '') for s in sources)
        if check_answer_is_source_copy(answer, all_source_text):
            issues.append("ANSWER_IS_JUST_SOURCE_COPY")

    # Very short or meaningless source titles
    if sources:
        title = sources[0].get('title', '')
        # Titles that are just numbers, single chars, or form labels
        if title and (len(title) <= 2 or re.match(r'^[A-Z]?\d+$', title) or title.endswith(':')):
            issues.append("SOURCE_TITLE_MEANINGLESS")

    # Escaped markdown in answer (poorly converted tables)
    if '\\|' in answer or '\\*' in answer:
        issues.append("ANSWER_ESCAPED_MARKDOWN")

    # Form template sample data in answer
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
    warning_patterns = [
        'QUESTION_TEMPLATE_MISMATCH', 'ANSWER_TOO_SHORT',
        'QUESTION_TOO_SHORT', 'QUESTION_NO_SUBJECT', 'SOURCE_TITLE_NOT_IN_PAGE',
        'ANSWER_IS_JUST_SOURCE_COPY', 'QUESTION_REFERENCE_STYLE'
    ]

    critical = [i for i in issues if any(p in i for p in critical_patterns)]
    warnings = [i for i in issues if any(p in i for p in warning_patterns)]
    return critical, warnings, issues


def main():
    print("=" * 80)
    print("전수조사 v2 (Full Entry-by-Entry Inspection)")
    print("=" * 80)

    entries = []
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    print(f"\n총 {len(entries)}개 엔트리 로드 완료")

    print("중복 답변 검출 중...")
    duplicate_ids = detect_duplicate_answers(entries)
    print(f"  중복 답변: {len(duplicate_ids)}개")

    clean_entries = []
    rejected_entries = []
    issue_counter = Counter()
    critical_counter = Counter()
    category_stats = defaultdict(lambda: {'total': 0, 'clean': 0, 'rejected': 0})

    print("\n검증 진행 중...")
    for i, entry in enumerate(entries):
        if (i + 1) % 500 == 0:
            print(f"  {i+1}/{len(entries)} 완료... (통과: {len(clean_entries)}, 탈락: {len(rejected_entries)})")

        critical, warnings, all_issues = inspect_entry(entry, duplicate_ids)

        for issue in all_issues:
            base = issue.split(':')[0]
            issue_counter[base] += 1
        for c in critical:
            base = c.split(':')[0]
            critical_counter[base] += 1

        cat = entry.get('category', 'unknown')
        category_stats[cat]['total'] += 1

        if critical:
            entry['_rejection_reasons'] = critical
            entry['_warnings'] = warnings
            rejected_entries.append(entry)
            category_stats[cat]['rejected'] += 1
        else:
            if warnings:
                entry['_warnings'] = warnings
            clean_entries.append(entry)
            category_stats[cat]['clean'] += 1

    print(f"\n검증 완료!")
    print(f"  통과: {len(clean_entries)}개")
    print(f"  탈락: {len(rejected_entries)}개")
    print(f"  탈락률: {len(rejected_entries)/len(entries)*100:.1f}%")

    # Write outputs
    with open(OUTPUT_CLEAN, 'w', encoding='utf-8') as f:
        for entry in clean_entries:
            out = {k: v for k, v in entry.items() if not k.startswith('_')}
            f.write(json.dumps(out, ensure_ascii=False) + '\n')

    with open(OUTPUT_REJECTED, 'w', encoding='utf-8') as f:
        for entry in rejected_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    # Report
    report = []
    report.append("=" * 80)
    report.append("전수조사 검증 보고서 v2")
    report.append("=" * 80)
    report.append(f"\n입력: {len(entries)}개")
    report.append(f"통과: {len(clean_entries)}개")
    report.append(f"탈락: {len(rejected_entries)}개 ({len(rejected_entries)/len(entries)*100:.1f}%)")

    report.append(f"\n{'='*60}")
    report.append("탈락 사유별 통계 (Critical)")
    report.append(f"{'='*60}")
    for issue, count in critical_counter.most_common():
        report.append(f"  {issue}: {count}개")

    report.append(f"\n{'='*60}")
    report.append("전체 이슈 통계")
    report.append(f"{'='*60}")
    for issue, count in issue_counter.most_common():
        report.append(f"  {issue}: {count}개")

    report.append(f"\n{'='*60}")
    report.append("카테고리별 통계")
    report.append(f"{'='*60}")
    for cat in sorted(category_stats.keys()):
        s = category_stats[cat]
        r = s['rejected']/s['total']*100 if s['total'] > 0 else 0
        report.append(f"  {cat}: 총 {s['total']}개, 통과 {s['clean']}개, 탈락 {s['rejected']}개 ({r:.1f}%)")

    w_count = sum(1 for e in clean_entries if '_warnings' in e)
    report.append(f"\n통과 엔트리 중 경고: {w_count}개")
    wc = Counter()
    for e in clean_entries:
        if '_warnings' in e:
            for w in e['_warnings']:
                wc[w.split(':')[0]] += 1
    for w, c in wc.most_common():
        report.append(f"  {w}: {c}개")

    # Sample rejected
    report.append(f"\n{'='*60}")
    report.append("탈락 샘플 (20개)")
    report.append(f"{'='*60}")
    import random
    random.seed(42)
    sample = random.sample(rejected_entries, min(20, len(rejected_entries)))
    for entry in sample:
        report.append(f"\nID: {entry['id']}")
        report.append(f"  Q: {entry['question'][:100]}")
        report.append(f"  A길이: {len(entry.get('answer',''))}자")
        report.append(f"  출처: page {entry['sources'][0]['page'] if entry.get('sources') else 'N/A'}")
        report.append(f"  사유: {entry.get('_rejection_reasons', [])}")

    report_text = '\n'.join(report)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report_text)

    print(f"\n{report_text}")


if __name__ == '__main__':
    main()
