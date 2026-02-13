#!/usr/bin/env python3
"""
Source verification script for 0final.jsonl entries.
Checks if source text content actually exists in the corresponding markdown files.
Uses multi-strategy fuzzy matching:
  1. 4-word sliding window matching
  2. Individual keyword/term matching for table-reformatted content
"""

import json
import os
import re
from collections import defaultdict

MD_DIR = "/home/user/menual/마크다운"
JSONL_FILE = "/home/user/menual/0final.jsonl"
PROBLEMATIC_FILE = "/home/user/menual/problematic_entries.json"
OUTPUT_FILE = "/home/user/menual/source_verification_report.json"


def load_markdown(page_num):
    """Load markdown content for a given page number."""
    md_path = os.path.join(MD_DIR, f"{page_num}쪽.md")
    if not os.path.exists(md_path):
        return None
    with open(md_path, "r", encoding="utf-8") as f:
        return f.read()


def normalize_text(text):
    """Normalize text for comparison."""
    if not text:
        return ""
    # Remove markdown formatting symbols
    text = re.sub(r'[#*_`\[\](){}|>~]', '', text)
    # Normalize all quotes to empty
    text = text.replace('\u201c', '').replace('\u201d', '')
    text = text.replace('\u2018', '').replace('\u2019', '')
    text = text.replace('"', '').replace("'", '')
    text = text.replace('\u300c', '').replace('\u300d', '')
    text = text.replace('\u300e', '').replace('\u300f', '')
    # Remove bullet/numbering markers
    text = re.sub(r'[①②③④⑤⑥⑦⑧⑨⑩]', '', text)
    text = re.sub(r'[∘•·]', ' ', text)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_keywords(source_text, min_len=2):
    """
    Extract meaningful Korean terms/keywords from source text.
    These are multi-character Korean words that are likely to be unique identifiers.
    """
    normalized = normalize_text(source_text)
    # Extract Korean word sequences (2+ chars)
    korean_terms = re.findall(r'[가-힣]{2,}', normalized)
    # Filter to terms of meaningful length (3+ chars for specificity)
    meaningful = [t for t in korean_terms if len(t) >= 3]
    return meaningful


def verify_source(source, md_cache):
    """
    Verify a single source against its corresponding markdown file.
    Uses two strategies:
      Strategy 1: 4-word sliding window (catches verbatim/near-verbatim text)
      Strategy 2: Individual keyword presence (catches reformatted table data)
    Returns (status, reason, match_ratio).
    """
    page = source.get('page')
    source_text = source.get('text', '')
    
    if not source_text:
        return 'mismatched', 'Empty source text', 0.0
    
    if page not in md_cache:
        md_content = load_markdown(page)
        md_cache[page] = md_content
    
    md_content = md_cache[page]
    
    if md_content is None:
        return 'missing_md', f'Markdown file not found for page {page}', 0.0
    
    md_normalized = normalize_text(md_content)
    src_normalized = normalize_text(source_text)
    
    # --- Strategy 1: 4-word sliding window ---
    words = src_normalized.split()
    window_size = 4
    
    if len(words) >= window_size:
        segments = []
        for i in range(0, len(words) - window_size + 1, 2):
            seg = ' '.join(words[i:i + window_size])
            if len(seg) >= 6:
                segments.append(seg)
        
        if segments:
            matched_segs = sum(1 for seg in segments if seg in md_normalized)
            seg_ratio = matched_segs / len(segments)
            if seg_ratio >= 0.30:
                return 'matched', f'Window match: {matched_segs}/{len(segments)} ({seg_ratio:.0%})', seg_ratio
    elif src_normalized and src_normalized in md_normalized:
        return 'matched', 'Direct substring match', 1.0
    elif len(words) > 0 and len(words) < window_size:
        # Short source - check 2-word windows
        if len(words) >= 2:
            for i in range(len(words) - 1):
                bigram = ' '.join(words[i:i+2])
                if bigram in md_normalized:
                    return 'matched', 'Short text bigram match', 0.5
    
    # --- Strategy 2: Korean keyword matching ---
    # This catches cases where source reformats table data
    keywords = extract_keywords(source_text)
    if keywords:
        # Deduplicate while preserving order
        seen = set()
        unique_kw = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_kw.append(kw)
        
        matched_kw = sum(1 for kw in unique_kw if kw in md_normalized)
        kw_ratio = matched_kw / len(unique_kw) if unique_kw else 0
        
        if kw_ratio >= 0.50:
            return 'matched', f'Keyword match: {matched_kw}/{len(unique_kw)} ({kw_ratio:.0%})', kw_ratio
    
    # --- Neither strategy matched ---
    # Collect diagnostics
    seg_info = ""
    if len(words) >= window_size:
        segments = [' '.join(words[i:i+window_size]) for i in range(0, len(words)-window_size+1, 2)]
        matched_segs = sum(1 for seg in segments if seg in md_normalized)
        seg_info = f'Windows: {matched_segs}/{len(segments)}'
    
    kw_info = ""
    if keywords:
        unique_kw_set = list(dict.fromkeys(keywords))
        matched_kw = sum(1 for kw in unique_kw_set if kw in md_normalized)
        unmatched_kw = [kw for kw in unique_kw_set if kw not in md_normalized][:5]
        kw_info = f'Keywords: {matched_kw}/{len(unique_kw_set)}, unmatched: {unmatched_kw}'
    
    reason = f'{seg_info}. {kw_info}'
    
    # Calculate best ratio from either strategy
    best_ratio = 0
    if len(words) >= window_size:
        segments = [' '.join(words[i:i+window_size]) for i in range(0, len(words)-window_size+1, 2)]
        if segments:
            best_ratio = max(best_ratio, sum(1 for seg in segments if seg in md_normalized) / len(segments))
    if keywords:
        unique_kw_set = list(dict.fromkeys(keywords))
        if unique_kw_set:
            best_ratio = max(best_ratio, sum(1 for kw in unique_kw_set if kw in md_normalized) / len(unique_kw_set))
    
    return 'mismatched', reason, best_ratio


def verify_entry(entry, md_cache):
    """
    Verify all sources for an entry.
    Matched if any source matches, or average across sources is reasonable.
    """
    sources = entry.get('sources', [])
    if not sources:
        return 'mismatched', 'No sources listed', []
    
    source_results = []
    any_missing = False
    any_matched = False
    all_mismatched = True
    
    for source in sources:
        status, reason, ratio = verify_source(source, md_cache)
        source_results.append((status, reason, source.get('page'), ratio))
        if status == 'missing_md':
            any_missing = True
        if status == 'matched':
            any_matched = True
            all_mismatched = False
        elif status == 'missing_md':
            all_mismatched = False
    
    if any_missing and not any_matched:
        missing_pages = [r[2] for r in source_results if r[0] == 'missing_md']
        return 'missing_md', f'Missing markdown for pages: {missing_pages}', source_results
    
    if any_matched:
        return 'matched', 'At least one source verified', source_results
    
    # All sources mismatched
    mismatch_details = [(r[2], r[1]) for r in source_results if r[0] == 'mismatched']
    return 'mismatched', f'All sources mismatched: {mismatch_details}', source_results


def main():
    print("=" * 70)
    print("Source Verification Report")
    print("=" * 70)
    
    # Load all entries
    all_entries = []
    with open(JSONL_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                all_entries.append(json.loads(line))
    
    print(f"Total entries in 0final.jsonl: {len(all_entries)}")
    
    # Load problematic entries
    with open(PROBLEMATIC_FILE, 'r', encoding='utf-8') as f:
        problematic = json.load(f)
    
    problematic_ids = {e['id'] for e in problematic}
    print(f"Total problematic entries: {len(problematic_ids)}")
    
    # Verify ALL entries
    md_cache = {}
    
    results = {
        'total_checked': 0,
        'matched': 0,
        'mismatched': 0,
        'missing_md': 0,
        'mismatched_entries': [],
        'missing_md_entries': [],
        'problematic_results': {
            'total': len(problematic_ids),
            'matched': 0,
            'mismatched': 0,
            'missing_md': 0
        },
        'non_problematic_results': {
            'total': 0,
            'matched': 0,
            'mismatched': 0,
            'missing_md': 0
        },
        'by_category': {}
    }
    
    for idx, entry in enumerate(all_entries):
        if (idx + 1) % 500 == 0:
            print(f"  Verified {idx + 1}/{len(all_entries)} entries...")
        
        status, reason, source_results = verify_entry(entry, md_cache)
        results['total_checked'] += 1
        
        entry_id = entry['id']
        is_problematic = entry_id in problematic_ids
        cat = entry.get('category', 'unknown')
        
        if cat not in results['by_category']:
            results['by_category'][cat] = {'matched': 0, 'mismatched': 0, 'missing_md': 0}
        
        sub_key = 'problematic_results' if is_problematic else 'non_problematic_results'
        
        if status == 'matched':
            results['matched'] += 1
            results['by_category'][cat]['matched'] += 1
            results[sub_key]['matched'] += 1
        elif status == 'missing_md':
            results['missing_md'] += 1
            results['by_category'][cat]['missing_md'] += 1
            results[sub_key]['missing_md'] += 1
            results['missing_md_entries'].append({
                'id': entry_id,
                'page': entry['sources'][0]['page'] if entry.get('sources') else None,
                'reason': reason,
                'is_problematic': is_problematic,
                'category': cat
            })
        else:
            results['mismatched'] += 1
            results['by_category'][cat]['mismatched'] += 1
            results[sub_key]['mismatched'] += 1
            source_pages = [s['page'] for s in entry.get('sources', [])]
            results['mismatched_entries'].append({
                'id': entry_id,
                'page': source_pages[0] if source_pages else None,
                'all_pages': source_pages,
                'reason': reason[:500],
                'is_problematic': is_problematic,
                'category': cat,
                'question': entry.get('question', '')[:200],
                'source_text_preview': entry['sources'][0]['text'][:200] if entry.get('sources') else ''
            })
    
    results['non_problematic_results']['total'] = (
        results['non_problematic_results']['matched'] +
        results['non_problematic_results']['mismatched'] +
        results['non_problematic_results']['missing_md']
    )
    
    # Print summary
    print()
    print("=" * 70)
    print("OVERALL RESULTS")
    print("=" * 70)
    tc = results['total_checked']
    print(f"Total checked:  {tc}")
    print(f"Matched:        {results['matched']} ({results['matched']/tc*100:.1f}%)")
    print(f"Mismatched:     {results['mismatched']} ({results['mismatched']/tc*100:.1f}%)")
    print(f"Missing MD:     {results['missing_md']} ({results['missing_md']/tc*100:.1f}%)")
    
    print()
    print("PROBLEMATIC ENTRIES")
    pr = results['problematic_results']
    print(f"  Total: {pr['total']}")
    print(f"  Matched: {pr['matched']}")
    print(f"  Mismatched: {pr['mismatched']}")
    print(f"  Missing MD: {pr['missing_md']}")
    
    print()
    print("NON-PROBLEMATIC ENTRIES")
    npr = results['non_problematic_results']
    print(f"  Total: {npr['total']}")
    print(f"  Matched: {npr['matched']}")
    print(f"  Mismatched: {npr['mismatched']}")
    print(f"  Missing MD: {npr['missing_md']}")
    
    print()
    print("BY CATEGORY:")
    for cat, stats in sorted(results['by_category'].items()):
        total_cat = stats['matched'] + stats['mismatched'] + stats['missing_md']
        match_pct = stats['matched'] / total_cat * 100 if total_cat > 0 else 0
        print(f"  {cat}: {stats['matched']}/{total_cat} matched ({match_pct:.1f}%), "
              f"{stats['mismatched']} mismatched, {stats['missing_md']} missing")
    
    if results['mismatched_entries']:
        print()
        print(f"ALL MISMATCHED ENTRIES ({len(results['mismatched_entries'])}):")
        for entry in results['mismatched_entries']:
            prob_flag = " [PROBLEMATIC]" if entry['is_problematic'] else ""
            print(f"  {entry['id']} | Pages: {entry.get('all_pages', entry.get('page'))} | "
                  f"Cat: {entry['category']}{prob_flag}")
            print(f"    Q: {entry.get('question', '')[:100]}")
            reason = entry['reason']
            if len(reason) > 200:
                reason = reason[:200] + "..."
            print(f"    Reason: {reason}")
    
    # Save results
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print()
    print(f"Full report saved to: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
