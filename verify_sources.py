#!/usr/bin/env python3
"""
Source verification script for 0final.jsonl entries.
Checks if source text content actually exists in the corresponding markdown files.
Uses fuzzy matching: extracts key phrases from source text and checks presence in markdown.
"""

import json
import os
import re
import random
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
    """Normalize text for comparison: remove markdown formatting, extra whitespace, etc."""
    if not text:
        return ""
    # Remove markdown formatting symbols
    text = re.sub(r'[#*_`\[\](){}|>~]', '', text)
    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"').replace("'", "'").replace("'", "'")
    text = text.replace('「', '').replace('」', '').replace('『', '').replace('』', '')
    # Remove numbering artifacts like (1), (가), ①, etc. but keep the content
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_key_phrases(source_text, min_length=8):
    """
    Extract key phrases from source text for matching.
    Returns a list of normalized phrases that should appear in the markdown.
    """
    normalized = normalize_text(source_text)
    if not normalized:
        return []
    
    # Split into sentences/clauses
    # Split on common delimiters
    parts = re.split(r'[.。\n]', normalized)
    
    phrases = []
    for part in parts:
        part = part.strip()
        if len(part) >= min_length:
            # Take meaningful substrings - use chunks of the sentence
            # For longer parts, extract the core content
            phrases.append(part)
    
    # If no phrases found from splitting, use the whole text
    if not phrases and len(normalized) >= min_length:
        phrases.append(normalized)
    
    return phrases


def check_phrase_in_markdown(phrase, md_content_normalized, threshold=0.6):
    """
    Check if a phrase (or significant portion of it) exists in the markdown content.
    Uses substring matching with some flexibility.
    """
    if not phrase or not md_content_normalized:
        return False
    
    # Direct substring match
    if phrase in md_content_normalized:
        return True
    
    # Try matching significant substrings (sliding window)
    # Take windows of varying sizes from the phrase
    words = phrase.split()
    if len(words) <= 3:
        # For short phrases, require exact match of at least part
        # Try consecutive word sequences
        for i in range(len(words)):
            for j in range(i + 2, len(words) + 1):
                sub = ' '.join(words[i:j])
                if len(sub) >= 6 and sub in md_content_normalized:
                    return True
        return False
    
    # For longer phrases, check if enough consecutive words match
    # Try windows of 4+ consecutive words
    match_count = 0
    total_windows = 0
    window_size = min(4, len(words))
    
    for i in range(len(words) - window_size + 1):
        window = ' '.join(words[i:i + window_size])
        total_windows += 1
        if window in md_content_normalized:
            match_count += 1
    
    if total_windows == 0:
        return False
    
    return (match_count / total_windows) >= threshold


def verify_source(source, md_cache):
    """
    Verify a single source against its corresponding markdown file.
    Returns (status, reason) where status is 'matched', 'mismatched', or 'missing_md'.
    """
    page = source.get('page')
    source_text = source.get('text', '')
    
    if not source_text:
        return 'mismatched', 'Empty source text'
    
    if page not in md_cache:
        md_content = load_markdown(page)
        md_cache[page] = md_content
    
    md_content = md_cache[page]
    
    if md_content is None:
        return 'missing_md', f'Markdown file not found for page {page}'
    
    # Normalize both texts
    md_normalized = normalize_text(md_content)
    
    # Extract key phrases from source
    phrases = extract_key_phrases(source_text)
    
    if not phrases:
        return 'mismatched', 'Could not extract key phrases from source text'
    
    # Check how many phrases match
    matched_phrases = 0
    unmatched = []
    
    for phrase in phrases:
        if check_phrase_in_markdown(phrase, md_normalized):
            matched_phrases += 1
        else:
            unmatched.append(phrase[:80])
    
    match_ratio = matched_phrases / len(phrases) if phrases else 0
    
    # Consider it a match if at least 40% of phrases match
    # (some variation is expected between PDF extraction and markdown)
    if match_ratio >= 0.4:
        return 'matched', f'{matched_phrases}/{len(phrases)} phrases matched'
    else:
        reason = f'Only {matched_phrases}/{len(phrases)} phrases matched ({match_ratio:.0%}). Unmatched: {"; ".join(unmatched[:3])}'
        return 'mismatched', reason


def verify_entry(entry, md_cache):
    """
    Verify all sources for an entry. 
    Returns overall status and details.
    """
    sources = entry.get('sources', [])
    if not sources:
        return 'mismatched', 'No sources listed'
    
    all_results = []
    any_missing = False
    any_mismatched = False
    
    for i, source in enumerate(sources):
        status, reason = verify_source(source, md_cache)
        all_results.append((status, reason, source.get('page')))
        if status == 'missing_md':
            any_missing = True
        elif status == 'mismatched':
            any_mismatched = True
    
    if any_missing:
        missing_pages = [r[2] for r in all_results if r[0] == 'missing_md']
        return 'missing_md', f'Missing markdown for pages: {missing_pages}'
    elif any_mismatched:
        mismatch_details = [(r[2], r[1]) for r in all_results if r[0] == 'mismatched']
        return 'mismatched', f'Mismatched sources: {mismatch_details}'
    else:
        return 'matched', 'All sources verified'


def main():
    print("=" * 70)
    print("Source Verification Report")
    print("=" * 70)
    
    # Load all entries from 0final.jsonl
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
    
    # Build entry lookup
    entry_by_id = {e['id']: e for e in all_entries}
    
    # Determine which entries to check:
    # 1. All problematic entries
    # 2. A stratified sample of at least 200 non-problematic entries across categories
    
    entries_to_check = {}
    
    # Add all problematic entries
    for entry in all_entries:
        if entry['id'] in problematic_ids:
            entries_to_check[entry['id']] = entry
    
    # Stratified sample of non-problematic entries
    non_problematic_by_cat = defaultdict(list)
    for entry in all_entries:
        if entry['id'] not in problematic_ids:
            cat = entry.get('category', 'unknown')
            non_problematic_by_cat[cat].append(entry)
    
    # Sample proportionally, at least 200 total
    total_non_prob = sum(len(v) for v in non_problematic_by_cat.values())
    sample_target = max(200, total_non_prob)  # Check all entries actually
    
    # Since user asked to sample at least 200, let's check ALL entries for thoroughness
    # but mark which ones are problematic vs sampled
    for entry in all_entries:
        entries_to_check[entry['id']] = entry
    
    print(f"Entries to verify: {len(entries_to_check)} (all entries)")
    print()
    
    # Verify entries
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
    
    for idx, (entry_id, entry) in enumerate(entries_to_check.items()):
        if (idx + 1) % 500 == 0:
            print(f"  Verified {idx + 1}/{len(entries_to_check)} entries...")
        
        status, reason = verify_entry(entry, md_cache)
        results['total_checked'] += 1
        
        is_problematic = entry_id in problematic_ids
        cat = entry.get('category', 'unknown')
        
        if cat not in results['by_category']:
            results['by_category'][cat] = {'matched': 0, 'mismatched': 0, 'missing_md': 0}
        
        if status == 'matched':
            results['matched'] += 1
            results['by_category'][cat]['matched'] += 1
            if is_problematic:
                results['problematic_results']['matched'] += 1
            else:
                results['non_problematic_results']['matched'] += 1
        elif status == 'missing_md':
            results['missing_md'] += 1
            results['by_category'][cat]['missing_md'] += 1
            results['missing_md_entries'].append({
                'id': entry_id,
                'page': entry['sources'][0]['page'] if entry.get('sources') else None,
                'reason': reason,
                'is_problematic': is_problematic,
                'category': cat
            })
            if is_problematic:
                results['problematic_results']['missing_md'] += 1
            else:
                results['non_problematic_results']['missing_md'] += 1
        else:  # mismatched
            results['mismatched'] += 1
            results['by_category'][cat]['mismatched'] += 1
            source_pages = [s['page'] for s in entry.get('sources', [])]
            results['mismatched_entries'].append({
                'id': entry_id,
                'page': source_pages[0] if source_pages else None,
                'all_pages': source_pages,
                'reason': reason,
                'is_problematic': is_problematic,
                'category': cat
            })
            if is_problematic:
                results['problematic_results']['mismatched'] += 1
            else:
                results['non_problematic_results']['mismatched'] += 1
    
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
    print(f"Total checked:  {results['total_checked']}")
    print(f"Matched:        {results['matched']} ({results['matched']/results['total_checked']*100:.1f}%)")
    print(f"Mismatched:     {results['mismatched']} ({results['mismatched']/results['total_checked']*100:.1f}%)")
    print(f"Missing MD:     {results['missing_md']} ({results['missing_md']/results['total_checked']*100:.1f}%)")
    
    print()
    print("PROBLEMATIC ENTRIES")
    print(f"  Total: {results['problematic_results']['total']}")
    print(f"  Matched: {results['problematic_results']['matched']}")
    print(f"  Mismatched: {results['problematic_results']['mismatched']}")
    print(f"  Missing MD: {results['problematic_results']['missing_md']}")
    
    print()
    print("NON-PROBLEMATIC ENTRIES")
    print(f"  Total: {results['non_problematic_results']['total']}")
    print(f"  Matched: {results['non_problematic_results']['matched']}")
    print(f"  Mismatched: {results['non_problematic_results']['mismatched']}")
    print(f"  Missing MD: {results['non_problematic_results']['missing_md']}")
    
    print()
    print("BY CATEGORY:")
    for cat, stats in sorted(results['by_category'].items()):
        total_cat = stats['matched'] + stats['mismatched'] + stats['missing_md']
        match_pct = stats['matched'] / total_cat * 100 if total_cat > 0 else 0
        print(f"  {cat}: {stats['matched']}/{total_cat} matched ({match_pct:.1f}%), "
              f"{stats['mismatched']} mismatched, {stats['missing_md']} missing")
    
    if results['mismatched_entries']:
        print()
        print("SAMPLE MISMATCHED ENTRIES (first 20):")
        for entry in results['mismatched_entries'][:20]:
            print(f"  ID: {entry['id']}, Pages: {entry.get('all_pages', entry.get('page'))}, "
                  f"Problematic: {entry['is_problematic']}")
            reason = entry['reason']
            if len(reason) > 200:
                reason = reason[:200] + "..."
            print(f"    Reason: {reason}")
    
    if results['missing_md_entries']:
        print()
        print("MISSING MARKDOWN ENTRIES (first 10):")
        for entry in results['missing_md_entries'][:10]:
            print(f"  ID: {entry['id']}, Page: {entry['page']}, "
                  f"Problematic: {entry['is_problematic']}")
    
    # Save results
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print()
    print(f"Full report saved to: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
