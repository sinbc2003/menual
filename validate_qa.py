#!/usr/bin/env python3
"""
Comprehensive QA quality validation - 10 batches x 100 random samples.
Checks each entry against actual markdown source files.
"""

import json
import os
import re
import random
from collections import defaultdict

MD_DIR = "/home/user/menual/마크다운"
QA_FILE = "/home/user/menual/qa_dataset_final.jsonl"
OUTPUT_FILE = "/home/user/menual/qa_validation_results.json"

# Load all entries
with open(QA_FILE) as f:
    ALL_ENTRIES = [json.loads(l) for l in f]

print(f"Loaded {len(ALL_ENTRIES)} entries")

# Cache MD files
MD_CACHE = {}
def get_md(page):
    if page not in MD_CACHE:
        path = os.path.join(MD_DIR, f"{page}쪽.md")
        if os.path.exists(path):
            with open(path) as f:
                MD_CACHE[page] = f.read()
        else:
            MD_CACHE[page] = None
    return MD_CACHE[page]


def check_source_match(entry):
    """Check if source text actually exists in the markdown file."""
    if not entry.get('sources') or not entry['sources']:
        return 'NO_SOURCE', "출처 정보 없음"

    src = entry['sources'][0]
    page = src.get('page')
    src_text = src.get('text', '').strip()

    if not page or not src_text:
        return 'EMPTY_SOURCE', "출처 텍스트 비어있음"

    md = get_md(page)
    if md is None:
        return 'MD_NOT_FOUND', f"마크다운 파일 {page}쪽.md 없음"

    # Clean both for comparison
    def normalize(t):
        t = re.sub(r'\s+', ' ', t)
        t = re.sub(r'[*#>|\-]', '', t)
        return t.strip()

    norm_src = normalize(src_text)
    norm_md = normalize(md)

    # Check exact substring
    if norm_src[:50] in norm_md:
        return 'MATCH', ""

    # Check word overlap
    src_words = set(norm_src.split())
    md_words = set(norm_md.split())
    if not src_words:
        return 'EMPTY_SOURCE', "정규화 후 출처 비어있음"

    overlap = len(src_words & md_words) / len(src_words)
    if overlap >= 0.7:
        return 'PARTIAL_MATCH', f"단어 겹침 {overlap:.0%}"
    elif overlap >= 0.4:
        return 'WEAK_MATCH', f"단어 겹침 {overlap:.0%}"
    else:
        return 'NO_MATCH', f"단어 겹침 {overlap:.0%} - 출처 불일치"


def check_answer_accuracy(entry):
    """Check if answer content is grounded in the source markdown."""
    answer = entry.get('answer', '')
    page = entry['sources'][0]['page'] if entry.get('sources') and entry['sources'] else None
    if not page:
        return 'NO_PAGE', "페이지 정보 없음"

    md = get_md(page)
    if not md:
        return 'MD_NOT_FOUND', ""

    # Extract factual claims from answer (numbers, names, law references)
    answer_claims = set()

    # Numbers (years, periods, amounts)
    for m in re.finditer(r'\d+(?:년|월|일|시간|명|회|%|만원|원|점)', answer):
        answer_claims.add(m.group(0))

    # Law references
    for m in re.finditer(r'[「『](.+?)[」』]', answer):
        answer_claims.add(m.group(1))

    # Article numbers
    for m in re.finditer(r'제\d+조(?:의\d+)?(?:제\d+항)?', answer):
        answer_claims.add(m.group(0))

    if not answer_claims:
        return 'NO_CLAIMS', "검증할 팩트 없음"

    # Check how many claims appear in the markdown
    md_text = md.replace('\n', ' ')
    verified = sum(1 for c in answer_claims if c in md_text)
    ratio = verified / len(answer_claims)

    if ratio >= 0.7:
        return 'ACCURATE', f"팩트 검증 {verified}/{len(answer_claims)} ({ratio:.0%})"
    elif ratio >= 0.4:
        return 'PARTIAL', f"팩트 검증 {verified}/{len(answer_claims)} ({ratio:.0%})"
    else:
        return 'INACCURATE', f"팩트 검증 {verified}/{len(answer_claims)} ({ratio:.0%}) - 답변 부정확"


def check_question_quality(entry):
    """Check question for various quality issues."""
    q = entry.get('question', '')
    issues = []

    # 1. No clear subject (주어 없음)
    # Questions that start with generic templates without a real topic
    if re.match(r'^(의|에서|에 대해|관련|과 관련)\s', q):
        issues.append('NO_SUBJECT')

    # Question topic is too vague/generic
    if q.startswith(('관련 규정', '관련하여', '관련 사항')):
        issues.append('VAGUE_SUBJECT')

    # 2. Placeholder characters
    if '○○' in q or '***' in q or '□□' in q:
        issues.append('PLACEHOLDER')

    # 3. Spaced-out characters (form artifact)
    if re.search(r'[가-힣]\s[가-힣]\s[가-힣]\s[가-힣]\s[가-힣]', q):
        issues.append('SPACED_CHARS')

    # 4. Question is just a section number/reference
    if re.match(r'^[\(\[]\d+[\)\]]', q) or re.match(r'^제\d+조', q):
        issues.append('SECTION_REF_ONLY')

    # 5. Contains raw HTML or markdown artifacts
    if re.search(r'<br|<div|<p |<span|\*\*', q):
        issues.append('RAW_MARKUP')

    # 6. Parenthesized text dominates the question
    paren_content = re.findall(r'\([^)]+\)', q)
    if paren_content and sum(len(p) for p in paren_content) > len(q) * 0.5:
        issues.append('PAREN_HEAVY')

    # 7. Question too short to be meaningful
    if len(q) < 15:
        issues.append('TOO_SHORT')

    # 8. Question topic starts with numbering (가), 1), etc.)
    topic_match = re.match(r'^[가나다라마바사아자차카타파하]\)\s', q)
    if topic_match:
        issues.append('NUMBERED_TOPIC')

    # 9. References specific page of the handbook
    if re.search(r'인사실무편람\s*\d+쪽', q):
        issues.append('PAGE_REF')

    # 10. Contains "계속" suggesting continuation artifact
    if '(계속)' in q or '계속)' in q:
        issues.append('CONTINUATION')

    # 11. Topic is a form/template name
    if re.search(r'서식\s*[ⅠⅡⅢⅣⅤⅥa-zA-Z]+[\-\s]*\d+', q):
        issues.append('FORM_TOPIC')

    # 12. Empty/meaningless topic extracted from section headers
    # e.g., asking about "(경 유)" or "<>" or "[ ]"
    if re.search(r'\([\s가-힣]{1,3}\s[\s가-힣]{1,3}\)', q):
        issues.append('SPACED_PAREN')

    # 13. Angle bracket content
    if '<' in q and '>' in q:
        issues.append('ANGLE_BRACKETS')

    return issues


def check_answer_quality(entry):
    """Check answer for quality issues."""
    a = entry.get('answer', '')
    issues = []

    # 1. Contains form template content
    if '________' in a or '( )학교' in a or '[ ]' in a:
        issues.append('FORM_CONTENT')

    # 2. Contains placeholder
    if a.count('○○') > 2 or a.count('***') > 2:
        issues.append('PLACEHOLDER_HEAVY')

    # 3. HTML contamination
    if re.search(r'<(?:br|div|p |span|table|img|input|align)', a, re.I):
        issues.append('HTML')

    # 4. Too short
    if len(a) < 150:
        issues.append('TOO_SHORT')

    # 5. Mostly formatting/symbols, little actual content
    alpha_chars = len(re.findall(r'[가-힣a-zA-Z]', a))
    if len(a) > 0 and alpha_chars / len(a) < 0.3:
        issues.append('LOW_CONTENT')

    # 6. Answer is just listing table formatting
    if a.count('|') > 10 and a.count('---') > 3:
        issues.append('TABLE_DUMP')

    # 7. Truncated answer (ends mid-word)
    if a and not a.rstrip().endswith(('.', '요', '다', '니다', '음', '임', '됨', '함')):
        last_char = a.rstrip()[-1] if a.rstrip() else ''
        if last_char and not re.match(r'[.!?\)」』\d]', last_char):
            issues.append('TRUNCATED')

    return issues


def check_source_quality(entry):
    """Check source text quality."""
    if not entry.get('sources') or not entry['sources']:
        return ['NO_SOURCE']

    src_text = entry['sources'][0].get('text', '')
    issues = []

    if len(src_text) < 20:
        issues.append('SRC_TOO_SHORT')

    # Mostly symbols/formatting
    alpha = len(re.findall(r'[가-힣a-zA-Z]', src_text))
    if len(src_text) > 0 and alpha / len(src_text) < 0.2:
        issues.append('SRC_LOW_CONTENT')

    # HTML in source
    if re.search(r'<(?:br|div|p |span|table|img)', src_text, re.I):
        issues.append('SRC_HTML')

    return issues


def validate_batch(batch_num, entries, indices):
    """Validate a batch of entries."""
    results = {
        'batch': batch_num,
        'size': len(indices),
        'flagged_ids': [],
        'issues_by_type': defaultdict(int),
        'critical_ids': [],  # entries that should be DELETED
        'details': []
    }

    for idx in indices:
        entry = entries[idx]
        entry_issues = []
        is_critical = False

        # 1. Source match check
        src_status, src_detail = check_source_match(entry)
        if src_status in ('NO_MATCH', 'NO_SOURCE', 'EMPTY_SOURCE', 'MD_NOT_FOUND'):
            entry_issues.append(f"SOURCE:{src_status}")
            if src_status == 'NO_MATCH':
                is_critical = True

        # 2. Answer accuracy check
        acc_status, acc_detail = check_answer_accuracy(entry)
        if acc_status == 'INACCURATE':
            entry_issues.append(f"ACCURACY:{acc_status}")
            is_critical = True

        # 3. Question quality
        q_issues = check_question_quality(entry)
        for qi in q_issues:
            entry_issues.append(f"Q:{qi}")
        # Critical question issues
        if any(qi in ('PLACEHOLDER', 'SPACED_CHARS', 'SPACED_PAREN', 'FORM_TOPIC', 'PAGE_REF') for qi in q_issues):
            is_critical = True

        # 4. Answer quality
        a_issues = check_answer_quality(entry)
        for ai in a_issues:
            entry_issues.append(f"A:{ai}")
        if any(ai in ('FORM_CONTENT', 'HTML', 'TABLE_DUMP', 'LOW_CONTENT') for ai in a_issues):
            is_critical = True

        # 5. Source quality
        s_issues = check_source_quality(entry)
        for si in s_issues:
            entry_issues.append(f"S:{si}")
        if 'SRC_HTML' in s_issues or 'SRC_LOW_CONTENT' in s_issues:
            is_critical = True

        # Record
        if entry_issues:
            results['flagged_ids'].append(entry['id'])
            for issue in entry_issues:
                results['issues_by_type'][issue] += 1

            if is_critical:
                results['critical_ids'].append(entry['id'])

            results['details'].append({
                'id': entry['id'],
                'page': entry['sources'][0]['page'] if entry.get('sources') and entry['sources'] else None,
                'question': entry['question'][:80],
                'answer_len': len(entry.get('answer', '')),
                'issues': entry_issues,
                'critical': is_critical
            })

    return results


def run_full_validation():
    """Run 10 batches of 100 random samples."""
    all_indices = list(range(len(ALL_ENTRIES)))

    # Use 10 different seeds for 10 batches
    all_results = []
    all_flagged = set()
    all_critical = set()

    for batch in range(10):
        seed = batch * 111 + 7
        random.seed(seed)
        indices = random.sample(all_indices, 100)

        result = validate_batch(batch + 1, ALL_ENTRIES, indices)
        all_results.append(result)
        all_flagged.update(result['flagged_ids'])
        all_critical.update(result['critical_ids'])

        flagged_pct = len(result['flagged_ids'])
        critical_pct = len(result['critical_ids'])
        print(f"Batch {batch+1}: {flagged_pct}/100 flagged, {critical_pct}/100 critical")

    # Aggregate statistics
    total_issues = defaultdict(int)
    for r in all_results:
        for issue, count in r['issues_by_type'].items():
            total_issues[issue] += count

    print(f"\n{'='*60}")
    print(f"VALIDATION SUMMARY (1,000 random samples from 10,044)")
    print(f"{'='*60}")
    print(f"Total flagged: {len(all_flagged)} ({len(all_flagged)/10:.1f}%)")
    print(f"Total CRITICAL (삭제 대상): {len(all_critical)} ({len(all_critical)/10:.1f}%)")

    print(f"\nIssue breakdown (across 1,000 samples):")
    for issue, count in sorted(total_issues.items(), key=lambda x: -x[1]):
        print(f"  {issue}: {count} ({count/10:.1f}%)")

    # Now scan FULL dataset for critical issues
    print(f"\n{'='*60}")
    print(f"FULL DATASET SCAN for critical issues...")
    print(f"{'='*60}")

    full_critical = set()
    full_issue_counts = defaultdict(int)

    for entry in ALL_ENTRIES:
        entry_critical = False

        # Quick critical checks on ALL entries
        q = entry.get('question', '')
        a = entry.get('answer', '')
        src_text = entry['sources'][0].get('text', '') if entry.get('sources') and entry['sources'] else ''

        reasons = []

        # Q: Placeholder
        if '○○' in q or '***' in q:
            reasons.append('Q:PLACEHOLDER')
            entry_critical = True

        # Q: Spaced characters
        if re.search(r'[가-힣]\s[가-힣]\s[가-힣]\s[가-힣]\s[가-힣]', q):
            reasons.append('Q:SPACED_CHARS')
            entry_critical = True

        # Q: Spaced parens (form fields)
        if re.search(r'\([\s가-힣]{1,3}\s[\s가-힣]{1,3}\)', q):
            reasons.append('Q:SPACED_PAREN')
            entry_critical = True

        # Q: Form/서식 topic
        if re.search(r'서식\s*[ⅠⅡⅢⅣⅤⅥa-zA-Z]+[\-\s]*\d+', q):
            reasons.append('Q:FORM_TOPIC')
            entry_critical = True

        # Q: Page reference
        if re.search(r'인사실무편람\s*\d+쪽', q):
            reasons.append('Q:PAGE_REF')
            entry_critical = True

        # Q: Too short
        if len(q) < 12:
            reasons.append('Q:TOO_SHORT')
            entry_critical = True

        # Q: Angle brackets
        if '<' in q and '>' in q and not '→' in q:
            reasons.append('Q:ANGLE_BRACKETS')
            entry_critical = True

        # Q: (계속) artifact
        if '(계속)' in q:
            reasons.append('Q:CONTINUATION')
            entry_critical = True

        # A: HTML
        if re.search(r'<(?:br|div|p |span|table|img|input|align)', a, re.I):
            reasons.append('A:HTML')
            entry_critical = True

        # A: Form content
        if '________' in a or ('[ ]' in a and a.count('[ ]') > 1):
            reasons.append('A:FORM_CONTENT')
            entry_critical = True

        # A: Very short
        if len(a) < 120:
            reasons.append('A:VERY_SHORT')
            entry_critical = True

        # A: Low content ratio
        alpha = len(re.findall(r'[가-힣a-zA-Z]', a))
        if len(a) > 50 and alpha / len(a) < 0.25:
            reasons.append('A:LOW_CONTENT')
            entry_critical = True

        # S: HTML in source
        if re.search(r'<(?:br|div|p |span|table|img|input|align)', src_text, re.I):
            reasons.append('S:HTML')
            entry_critical = True

        # S: Very short source
        if len(src_text) < 15:
            reasons.append('S:VERY_SHORT')
            entry_critical = True

        # S: Low content ratio in source
        if src_text:
            s_alpha = len(re.findall(r'[가-힣a-zA-Z]', src_text))
            if len(src_text) > 20 and s_alpha / len(src_text) < 0.15:
                reasons.append('S:LOW_CONTENT')
                entry_critical = True

        # Source text not in markdown (spot check - only for sampled entries)
        # (Full source check is too slow for 10k entries, done in sampling)

        if entry_critical:
            full_critical.add(entry['id'])
            for r in reasons:
                full_issue_counts[r] += 1

    print(f"\nFull dataset critical entries: {len(full_critical)} ({len(full_critical)*100/len(ALL_ENTRIES):.1f}%)")
    print(f"\nIssue breakdown (full dataset):")
    for issue, count in sorted(full_issue_counts.items(), key=lambda x: -x[1]):
        print(f"  {issue}: {count}")

    # Save results
    results = {
        'total_entries': len(ALL_ENTRIES),
        'sampled': 1000,
        'sample_flagged': len(all_flagged),
        'sample_critical': len(all_critical),
        'full_critical_count': len(full_critical),
        'full_critical_ids': sorted(full_critical),
        'issue_counts': dict(full_issue_counts),
        'batch_details': [
            {
                'batch': r['batch'],
                'flagged': len(r['flagged_ids']),
                'critical': len(r['critical_ids']),
                'details': r['details'][:20]  # Top 20 per batch
            }
            for r in all_results
        ]
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nDetailed results saved to {OUTPUT_FILE}")
    print(f"\n삭제 대상 ID 목록: {len(full_critical)}개")

    return full_critical


if __name__ == '__main__':
    critical_ids = run_full_validation()
