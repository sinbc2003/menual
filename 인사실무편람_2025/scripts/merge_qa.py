#!/usr/bin/env python3
"""
Merge all QA JSONL files, deduplicate, reassign IDs, and validate.
"""

import json
import os
import re
from collections import defaultdict

OUTPUT = "/home/user/menual/qa_dataset_final.jsonl"

FILES = [
    "/home/user/menual/qa_dataset.jsonl",
    "/home/user/menual/qa_hq_p8_12.jsonl",
    "/home/user/menual/qa_hq_direct.jsonl",
    "/home/user/menual/qa_generated.jsonl",
    "/home/user/menual/qa_generated_p2.jsonl",
    "/home/user/menual/qa_generated_p3.jsonl",
    "/home/user/menual/qa_generated_p4.jsonl",
    "/home/user/menual/qa_generated_p5.jsonl",
]

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

CAT_NUM = {name: num for _, _, name, num in CATEGORIES}

def get_cat_num(cat_name):
    return CAT_NUM.get(cat_name, "1")


def main():
    # Load all entries
    all_entries = []
    file_counts = {}
    for fp in FILES:
        if not os.path.exists(fp):
            print(f"SKIP (not found): {fp}")
            continue
        count = 0
        with open(fp) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    all_entries.append(entry)
                    count += 1
                except json.JSONDecodeError as e:
                    print(f"JSON error in {fp}: {e}")
        file_counts[os.path.basename(fp)] = count
        print(f"Loaded {count} from {os.path.basename(fp)}")

    print(f"\nTotal loaded: {len(all_entries)}")

    # Deduplicate by question text
    seen_questions = set()
    deduped = []
    dup_count = 0
    for entry in all_entries:
        q = entry.get('question', '').strip()
        if q in seen_questions:
            dup_count += 1
            continue
        seen_questions.add(q)
        deduped.append(entry)

    print(f"After dedup: {len(deduped)} (removed {dup_count} duplicates)")

    # Quality validation
    valid = []
    invalid_count = 0
    for entry in deduped:
        issues = []
        if not entry.get('question') or len(entry['question']) < 10:
            issues.append('short_question')
        if not entry.get('answer') or len(entry['answer']) < 100:
            issues.append('short_answer')
        if not entry.get('sources') or not entry['sources']:
            issues.append('no_sources')
        elif not entry['sources'][0].get('text') or len(entry['sources'][0]['text']) < 10:
            issues.append('short_source')
        if not entry.get('category'):
            issues.append('no_category')

        # HTML check
        if entry.get('answer') and re.search(r'<(?:br|div|p |span|table|img|input|align)', entry['answer'], re.I):
            issues.append('html_in_answer')
        if entry.get('sources') and entry['sources'] and re.search(r'<(?:br|div|p |span|table|img|input|align)', entry['sources'][0].get('text', ''), re.I):
            issues.append('html_in_source')

        if issues:
            invalid_count += 1
        else:
            valid.append(entry)

    print(f"After validation: {len(valid)} (removed {invalid_count} invalid)")

    # Sort by category page order, then by source page
    def sort_key(e):
        cat = e.get('category', '')
        cat_order = {'교원의 임용': 1, '정원 및 순회교사제': 2, '휴직 및 복직': 3,
                     '복무': 4, '계약제교원': 5, '평정 업무': 6,
                     '징계 및 직위해제': 7, '승급 및 호봉획정': 8}
        page = e['sources'][0]['page'] if e.get('sources') and e['sources'] else 0
        return (cat_order.get(cat, 9), page)

    valid.sort(key=sort_key)

    # Reassign IDs
    cat_counters = defaultdict(int)
    for entry in valid:
        cat_name = entry['category']
        cat_num = get_cat_num(cat_name)
        cat_counters[cat_name] += 1
        entry['id'] = f"q_{cat_num}_{cat_counters[cat_name]:04d}"

    # Statistics
    print(f"\n=== Final Dataset Statistics ===")
    print(f"Total entries: {len(valid)}")

    cat_counts = defaultdict(int)
    for e in valid:
        cat_counts[e['category']] += 1
    print(f"\nCategory distribution:")
    for cat in ['교원의 임용', '정원 및 순회교사제', '휴직 및 복직', '복무',
                '계약제교원', '평정 업무', '징계 및 직위해제', '승급 및 호봉획정']:
        print(f"  {cat}: {cat_counts.get(cat, 0)}")

    # Quality metrics
    ans_lens = [len(e['answer']) for e in valid]
    src_lens = [len(e['sources'][0]['text']) for e in valid if e.get('sources')]
    q_lens = [len(e['question']) for e in valid]
    print(f"\nQuality metrics:")
    print(f"  Answer length: avg={sum(ans_lens)//len(ans_lens)}, min={min(ans_lens)}, max={max(ans_lens)}")
    print(f"  Source length: avg={sum(src_lens)//len(src_lens)}, min={min(src_lens)}, max={max(src_lens)}")
    print(f"  Question length: avg={sum(q_lens)//len(q_lens)}, min={min(q_lens)}, max={max(q_lens)}")

    # Page coverage
    pages = set()
    for e in valid:
        if e.get('sources'):
            for s in e['sources']:
                pages.add(s['page'])
    print(f"  Pages covered: {len(pages)}")

    # Subcategory diversity
    subcats = set(e.get('subcategory', '') for e in valid)
    print(f"  Unique subcategories: {len(subcats)}")

    # Keyword count
    kw_count = sum(len(e.get('keywords', [])) for e in valid)
    print(f"  Total keywords: {kw_count} (avg {kw_count//len(valid)} per entry)")

    # Write output
    with open(OUTPUT, 'w', encoding='utf-8') as f:
        for entry in valid:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    print(f"\nWritten to {OUTPUT}")

    # JSON validation
    print("\nValidating JSON...")
    with open(OUTPUT) as f:
        for i, line in enumerate(f, 1):
            try:
                json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  ERROR on line {i}: {e}")
    print("  JSON validation passed!")

    return valid


if __name__ == '__main__':
    main()
