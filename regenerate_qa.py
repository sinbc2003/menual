#!/usr/bin/env python3
"""
Regenerate problematic QA entries for categories:
- 평정 업무 (pages 435-526)
- 징계 및 직위해제 (pages 527-596)
- 승급 및 호봉획정 (pages 597-700)

This script reads each problematic entry, analyzes the answer content and source markdown,
then generates a natural, specific question that a real Korean teacher/administrator would ask.
"""

import json
import os
import re

PROBLEMATIC_PATH = '/home/user/menual/problematic_entries.json'
MARKDOWN_DIR = '/home/user/menual/마크다운'
OUTPUT_PATH = '/home/user/menual/regenerated_cat6_8.jsonl'
TARGET_CATS = ['평정 업무', '징계 및 직위해제', '승급 및 호봉획정']


def read_markdown(page_num):
    """Read source markdown file for a given page number."""
    path = os.path.join(MARKDOWN_DIR, f'{page_num}쪽.md')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return ''


def generate_question(entry, md_content):
    """
    Generate a natural, specific question based on the entry's answer,
    source content, keywords, subcategory, and category.
    """
    entry_id = entry['id']

    # ================================================================
    # Manual mapping for each entry based on deep analysis of content
    # Each question is crafted to:
    # 1. Sound like what a real teacher/administrator would ask
    # 2. Be specific to the actual content in the answer
    # 3. Avoid template patterns, doc structure refs, and placeholders
    # ================================================================

    question_map = {
        # === 평정 업무 (category 6) ===

        'q_6_0020': '교육공무원 승진 평정 업무의 일반사항과 평정대상은 누구인가요?',

        'q_6_0021': '교장·교감 승진대상자의 평정대상 요건은 어떻게 되나요?',

        'q_6_0076': '경력평정 시 기본경력과 초과경력의 등급별 평정점 배점 기준은 어떻게 되나요?',

        'q_6_0077': '경력평정에서 가·나·다 경력 등급별로 월수와 일수에 대한 평정점은 각각 얼마인가요?',

        'q_6_0079': '경력평정의 기본경력 15년과 초과경력 5년에 대한 등급별 평정점 계산 방법은 무엇인가요?',

        'q_6_0081': '경력평정 시 기본경력과 초과경력의 평정만점은 등급별로 각각 몇 점인가요?',

        'q_6_0083': '경력 등급별 평정점의 산출 기준과 승진규정 관련 부칙의 경과조치는 어떻게 되나요?',

        'q_6_0089': '경력평정, 연수성적평정, 가산점평정 시 평정자와 확인자는 기관별로 누가 담당하나요?',

        'q_6_0095': '경력평정에서 가경력, 나경력, 다경력에 해당하는 경력의 종류는 각각 무엇인가요?',

        'q_6_0096': '가경력에 해당하는 경력 종별에는 어떤 것들이 있나요?',

        'q_6_0098': '교장·교감·장학관 등 각 직위별 경력은 어떤 등급으로 분류되나요?',

        'q_6_0099': '경력의 등급 및 종별 분류가 승진후보자명부 작성에 어떤 영향을 미치나요?',

        'q_6_0100': '나경력과 다경력에 해당하는 경력 종별에는 각각 어떤 것들이 포함되나요?',

        'q_6_0103': '교육연구관·장학사·교육연구사 경력과 교육부 지정 연구기관 경력은 어떤 등급으로 분류되나요?',

        'q_6_0209': '근무성적평정 시 확인자의 평정점과 다면평가점의 환산율은 어떻게 되나요?',

        'q_6_0225': '파견·겸임 교원의 근무성적평정은 어떻게 하며, 평정의 예외 사항은 무엇인가요?',

        'q_6_0252': '근무성적 평정점은 최근 3년간의 평정점을 어떤 비율로 산정하나요?',

        'q_6_0254': '근무성적 평정점 산정 시 연도별 가중치 비율과 유의할 점은 무엇인가요?',

        'q_6_0286': '근무성적평정에서 평정자와 확인자는 기관별로 누가 담당하나요?',

        'q_6_0303': '연수성적평정은 교육성적평정과 연구실적평정으로 어떻게 구분되며, 배점은 각각 얼마인가요?',

        'q_6_0315': '근무성적평정 결과의 공개 범위와 비공개가 가능한 특별한 사정은 무엇인가요?',

        'q_6_0340': '자격연수 성적 평정의 대상 기간과 직무연수성적의 평정 기준은 어떻게 되나요?',

        'q_6_0401': '연구실적 평정에서 인정되는 연구대회의 종류와 평정 기준은 무엇인가요?',

        'q_6_0462': '학점화된 직무연수 실적 가산점은 어떻게 산정하며, 연도별 인정 한도는 얼마인가요?',

        'q_6_0476': '공통가산점은 어떤 경력에 대해 부여되며, 전직한 경우 가산점은 어떻게 처리되나요?',

        'q_6_0506': '장학사·교육연구사 경력에 대한 가산점은 어떤 기준으로 평정하나요?',

        'q_6_0547': '선택가산점 중 4-H 지도 경력 등 특수활동 관련 가산점 기준은 어떻게 되나요?',

        'q_6_0554': '가산점 초과 제한 범위는 항목별로 각각 몇 점까지인가요?',

        'q_6_0563': '청소년단체 지도교사의 가산점 부여 기준과 단체별 가입 학생 수 요건은 어떻게 되나요?',

        'q_6_0577': '선택가산점 항목 간 중복 인정이 불가능한 경우는 어떤 것들이 있나요?',

        'q_6_0660': '교사 다면평가 시 평가대상자 인원별 다면평가자 수 기준은 어떻게 되나요?',

        'q_6_0735': '근무성적평정조정위원회는 어디에 설치하며, 주요 기능은 무엇인가요?',

        'q_6_0050': '교감 자격연수 대상자의 자격 요건은 무엇인가요?',

        'q_6_0051': '교육전문직원의 평정 대상자 요건은 어떻게 되나요?',

        'q_6_0533': '보직교사 경력에 대한 선택가산점은 어떻게 산정하나요?',

        'q_6_0769': '수석교사, 보건교사, 전문상담교사 등 특수직위 교사의 근무성적평정은 어떻게 하나요?',

        # === 징계 및 직위해제 (category 7) ===

        'q_7_0010': '공무원에 대한 징계사유에는 어떤 것들이 있나요?',

        'q_7_0029': '교육공무원 징계의 사유, 종류, 효력 등 징계 일반에 관한 주요 규정은 무엇인가요?',

        'q_7_0165': '징계의결 요구 시 성폭력·성희롱 비위 사건에 대한 전문가 의견서 제출 기준은 어떻게 되나요?',

        'q_7_0194': '징계의결의 기한은 얼마이며, 징계혐의자의 출석 관련 규정은 어떻게 되나요?',

        'q_7_0344': '교육지원청에서 징계위원회를 개최할 때 필요한 서류업무 절차는 어떻게 되나요?',

        'q_7_0373': '교육공무원 징계 시 확인서에 기재해야 할 비위유형에는 어떤 항목들이 있나요?',

        'q_7_0374': '징계 절차에서 사용하는 문답서의 양식과 작성 방법은 어떻게 되나요?',

        'q_7_0436': '교육공무원 징계양정 기준에서 비위유형별 징계 수준은 어떻게 되나요?',

        'q_7_0443': '공무원 비위사건 처리기준에서 비위의 정도와 고의·과실에 따른 징계 수준은 어떻게 달라지나요?',

        'q_7_0452': '성실의무 위반, 품위유지의무 위반 등 비위유형별 징계 처리기준은 구체적으로 어떻게 되나요?',

        'q_7_0546': '징계위원회 출석통지를 받았을 때 수령증에는 어떤 내용이 포함되나요?',

        'q_7_0570': '징계 결과처리 시 징계대상자에게 교부해야 하는 서류에는 어떤 것들이 있나요?',

        'q_7_0572': '징계 결과처리 수령증에 기재해야 하는 항목은 무엇인가요?',

        'q_7_0583': '징계처분 기록 말소 제도의 목적과 법적 근거는 무엇인가요?',

        'q_7_0585': '징계기록 말소 제도는 왜 필요하며, 어떤 법령에 근거하나요?',

        'q_7_0626': '징계처분 기록의 말소제한기간은 어떻게 산정하나요?',

        'q_7_0627': '단일 징계처분을 받은 경우 말소제한기간의 경과는 어떻게 판단하나요?',

        'q_7_0662': '중복 징계처분을 받은 경우 말소제한기간은 어떻게 계산하나요?',

        'q_7_0731': '징계등처분기록 말소 시 대상자에게 통지해야 할 사항은 무엇인가요?',

        'q_7_0733': '징계처분 기록이 말소되었을 때 대상자에게 어떤 방식으로 통지하나요?',

        'q_7_0772': '교육공무원의 직위해제 사유에는 어떤 것들이 있나요?',

        'q_7_0222': '징계 사건의 우선심사를 신청할 수 있는 경우와 절차는 어떻게 되나요?',

        # === 승급 및 호봉획정 (category 8) ===

        'q_8_0050': '초임호봉 획정 시 경력환산율표는 어떻게 적용하나요?',

        'q_8_0068': '초임호봉 획정 시 인정대상 경력기간은 어떻게 계산하나요?',

        'q_8_0155': '초임호봉 획정 시 학령(총 수학연수)의 산정 방법과 복수학위 인정 기준은 무엇인가요?',

        'q_8_0175': '사범계 가산연수와 비사범계 졸업자의 가산연수 인정 기준은 어떻게 다른가요?',

        'q_8_0190': '초임호봉 획정 시 사범계 가산연수와 특수학교 가산연수는 각각 몇 년을 인정하나요?',

        'q_8_0048': '신규채용 교원의 호봉획정 절차와 경력 증명 방법은 어떻게 되나요?',
    }

    # Use the manual mapping
    if entry_id in question_map:
        return question_map[entry_id]

    # Fallback
    print(f"WARNING: No mapping for {entry_id}, using original question")
    return entry.get('question', '')


def main():
    # Load problematic entries
    with open(PROBLEMATIC_PATH, 'r', encoding='utf-8') as f:
        all_entries = json.load(f)

    # Filter to target categories
    target_entries = [e for e in all_entries if e.get('category') in TARGET_CATS]
    print(f"Found {len(target_entries)} entries in target categories")

    # Process each entry
    regenerated = []
    for entry in target_entries:
        # Get source pages
        pages = [s.get('page') for s in entry.get('sources', []) if s.get('page')]

        # Read markdown for the first source page
        md_content = ''
        for p in pages:
            md = read_markdown(p)
            if md:
                md_content += md + '\n'

        # Generate new question
        new_question = generate_question(entry, md_content)

        # Clean up: remove placeholder symbols
        new_question = new_question.replace('▢', '').strip()

        # Build the output entry - same format as original but with improved question
        output_entry = {
            'id': entry['id'],
            'question': new_question,
            'answer': entry['answer'],
            'sources': entry['sources'],
            'category': entry['category'],
            'subcategory': entry.get('subcategory', ''),
            'keywords': entry.get('keywords', []),
        }

        regenerated.append(output_entry)
        old_q = entry['question'][:45]
        new_q = new_question[:45]
        print(f"  {entry['id']}: \"{old_q}...\" -> \"{new_q}...\"")

    # Write output
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        for entry in regenerated:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f"\nWrote {len(regenerated)} regenerated entries to {OUTPUT_PATH}")

    # Validate: check no entries have problematic patterns
    issues = 0
    for entry in regenerated:
        q = entry['question']
        eid = entry['id']

        checks = [
            ('▢', '▢ placeholder'),
            ('[별표', '[별표] doc reference'),
        ]

        template_checks = [
            ('전체 구조와 내용을 설명해주세요', 'structure_template'),
            ('어떤 과정을 거치나요', 'process_template2'),
            ('결과는 어떻게 처리되나요', 'result_template'),
        ]

        for pattern, label in checks:
            if pattern in q:
                print(f"  ISSUE ({label}): {eid}: {q}")
                issues += 1

        for pattern, label in template_checks:
            if pattern in q:
                print(f"  ISSUE ({label}): {eid}: {q}")
                issues += 1

        # Check for "관련하여 ... 기준은 무엇인가요" pattern
        if '관련하여' in q and '기준은 무엇인가요' in q:
            print(f"  ISSUE (standard_template): {eid}: {q}")
            issues += 1

        # Check for "과정에서 ... 어떻게 적용되나요" pattern
        if '과정에서' in q and '어떻게 적용되나요' in q:
            print(f"  ISSUE (process_template): {eid}: {q}")
            issues += 1

        # Check for document structure references in questions
        if re.search(r'서식\s*Ⅶ', q):
            print(f"  ISSUE (doc_structure): {eid}: {q}")
            issues += 1

    if issues == 0:
        print("\nAll questions passed quality validation!")
    else:
        print(f"\n{issues} issues found - please review")


if __name__ == '__main__':
    main()
