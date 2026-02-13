#!/usr/bin/env python3
"""
Regenerate problematic QA entries for 복무 and 계약제교원 categories.
Uses rule-based approach analyzing answer content and source text to generate
natural, specific questions that a real Korean teacher/administrator would ask.
"""

import json
import re
import os

def load_markdown(page_num):
    """Load markdown source file for a given page number."""
    path = f'/home/user/menual/마크다운/{page_num}쪽.md'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""

def clean_text(text):
    """Remove special markers and clean text."""
    text = text.replace('▢', '').replace('▣', '').replace('□', '').replace('■', '')
    text = text.replace('【', '').replace('】', '')
    text = re.sub(r'\[.*?화면.*?\]', '', text)
    text = re.sub(r'[※◦∘]', '', text)
    return text.strip()

def extract_key_topics(answer, source_texts):
    """Extract key topics from answer and source to understand the content."""
    combined = answer + " " + " ".join(source_texts)
    topics = {
        'nais': 'NEIS' in combined or '나이스' in combined,
        'leave': any(w in combined for w in ['연가', '병가', '특별휴가', '공가', '휴가']),
        'concurrent': any(w in combined for w in ['겸직', '겸임']),
        'deputy': '직무대리' in combined,
        'travel': '국외여행' in combined,
        'lecture': '외부강의' in combined,
        'media': any(w in combined for w in ['인터넷', '미디어', 'SNS', '블로그', '유튜브']),
        'contract': any(w in combined for w in ['기간제교원', '계약제교원', '기간제교사']),
        'employ': any(w in combined for w in ['채용', '임용']),
        'salary': any(w in combined for w in ['보수', '급여', '수당', '호봉']),
        'service': any(w in combined for w in ['복무', '근무']),
        'maternity': any(w in combined for w in ['출산휴가', '육아휴직', '육아시간']),
        'vacation': '휴업' in combined or '방학' in combined,
        'approval': any(w in combined for w in ['결재', '승인', '상신']),
        'pool': '인력풀' in combined,
        'register': '등록' in combined,
        'dismiss': any(w in combined for w in ['해임', '퇴직', '해고']),
        'law': any(w in combined for w in ['법률', '규정', '법령', '시행령']),
        'duty': any(w in combined for w in ['의무', '금지', '준수']),
        'child_protect': any(w in combined for w in ['아동', '청소년', '성보호']),
        'class_hour': any(w in combined for w in ['수업', '수업시수', '교과']),
    }
    return topics

def extract_specific_content(answer, max_len=200):
    """Extract specific content details from the answer."""
    # Remove the intro/boilerplate
    lines = answer.split('\n')
    content_lines = []
    skip_intro = True
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if skip_intro and ('안내드립니다' in stripped or '설명드리겠습니다' in stripped or '안내해 드리겠습니다' in stripped):
            skip_intro = False
            continue
        if not skip_intro:
            content_lines.append(stripped)
    content = ' '.join(content_lines[:10])
    return content[:max_len]

def extract_law_names(text):
    """Extract law/regulation names from text."""
    laws = re.findall(r'[「『](.*?)[」』]', text)
    return laws

def extract_article_numbers(text):
    """Extract article numbers like 제32조, 제41조 etc."""
    articles = re.findall(r'제\d+조(?:의\d+)?(?:\([^)]*\))?', text)
    return articles

def generate_question(entry):
    """Generate an improved question for a problematic entry."""
    eid = entry['id']
    original_q = entry['question']
    answer = entry['answer']
    category = entry['category']
    subcategory = entry['subcategory']
    keywords = entry.get('keywords', [])
    flags = entry.get('flags', [])
    source_texts = [s.get('text', '') for s in entry.get('sources', [])]
    source_titles = [s.get('title', '') for s in entry.get('sources', [])]
    pages = [s['page'] for s in entry.get('sources', [])]
    
    # Load markdown for context
    md_content = ""
    for p in pages:
        md_content += load_markdown(p) + "\n"
    
    topics = extract_key_topics(answer, source_texts)
    content_detail = extract_specific_content(answer)
    laws = extract_law_names(answer + " ".join(source_texts))
    articles = extract_article_numbers(answer + " ".join(source_texts))
    
    # Clean subcategory for use
    clean_sub = subcategory.replace('▢', '').replace('▣', '').replace('□', '').replace('■', '').strip()
    
    # ========================================================================
    # SPECIFIC QUESTION GENERATION RULES
    # ========================================================================
    
    # --- 복무 CATEGORY ---
    
    if eid == 'q_4_0041':
        return "교육공무원 복무와 관련된 주요 법규에는 어떤 것들이 있나요?"
    
    if eid == 'q_4_0042':
        return "초·중등교육법 제20조에 따른 교장, 교감, 수석교사, 교사의 임무는 각각 무엇인가요?"
    
    if eid == 'q_4_0085':
        return "교육공무원의 신분상 의무에는 어떤 것들이 있나요?"
    
    if eid == 'q_4_0113':
        return "교육공무원의 근무형태와 일반적 복무관리 원칙은 무엇인가요?"
    
    if eid == 'q_4_0130':
        return "학교의 휴업과 휴교는 어떤 차이가 있고, 각각의 법적 근거는 무엇인가요?"
    
    if eid == 'q_4_0162':
        return "교원이 방학 중에 대학원 수강을 할 때 근무 처리는 어떻게 하나요?"
    
    if eid == 'q_4_0182':
        return "교육공무원법 제41조에 의한 연수는 어떤 경우에 해당하며, 복무 처리는 어떻게 하나요?"
    
    if eid == 'q_4_0216':
        return "방학이나 재량휴업일에 근무상황은 나이스에서 어떻게 처리하나요?"
    
    if eid == 'q_4_0239':
        return "학교장의 근무상황을 나이스로 처리하는 구체적인 방법은 무엇인가요?"
    
    if eid == 'q_4_0245':
        return "방학 중 휴업일에 연가, 병가, 공가 등을 사용하려면 나이스에서 어떻게 신청하나요?"
    
    if eid == 'q_4_0250':
        return "나이스에서 복무 신청 시 결재자와 공람자는 어떻게 지정하고 승인 처리하나요?"
    
    if eid == 'q_4_0254':
        return "나이스 복무 기안문 상신 화면에서 결재자 지정 절차는 어떻게 되나요?"
    
    if eid == 'q_4_0256':
        return "나이스 기안문 상신 시 공람자 지정과 전결규정 적용은 어떻게 하나요?"
    
    if eid == 'q_4_0263':
        return "나이스에서 공람함 확인과 메시지 전송은 어떻게 하나요?"
    
    if eid == 'q_4_0296':
        return "교육공무원의 겸임, 직무대리, 겸직에 관한 법적 근거는 무엇인가요?"
    
    if eid == 'q_4_0338':
        return "기관장과 부기관장의 직무대리에 관한 규정은 어떻게 되어 있나요?"
    
    if eid == 'q_4_0343':
        return "직무대리 지정 시 특수한 사유가 있는 경우 대리자는 어떻게 정하나요?"
    
    if eid == 'q_4_0363':
        return "직무대리의 운영에 관한 제6조의 구체적인 내용은 무엇인가요?"
    
    if eid == 'q_4_0364':
        return "직무대리규정에서 직무대리 지정 요건과 절차는 어떻게 규정하고 있나요?"
    
    if eid == 'q_4_0378':
        return "육아휴직 중인 공무원이 아르바이트 등 겸직을 할 수 있나요?"
    
    if eid == 'q_4_0389':
        return "공무원이 공동주택 입주자 대표나 재건축조합 임원을 맡으려면 겸직허가가 필요한가요?"
    
    if eid == 'q_4_0391':
        return "공동주택 입주자 대표로 활동하려는 공무원의 겸직허가 절차와 제한 사항은 무엇인가요?"
    
    if eid == 'q_4_0467':
        return "교원의 사교육업체 관련 겸직은 허가가 가능한가요? 원칙은 무엇인가요?"
    
    if eid == 'q_4_0488':
        return "사교육업체가 아닌 기관에서의 겸직 허가 원칙과 확인 사항은 무엇인가요?"
    
    if eid == 'q_4_0489':
        return "교원이 평생직업교육학원에서 강의하려면 겸직허가를 받아야 하나요?"
    
    if eid == 'q_4_0523':
        return "사교육업체가 아닌 평생직업교육학원에서의 겸직은 어떤 기준으로 허가되나요?"
    
    if eid == 'q_4_0524':
        return "교원의 겸직 허가 절차는 구체적으로 어떻게 진행되나요?"
    
    if eid == 'q_4_0570':
        return "교원이 인터넷 개인 미디어 활동 시 준수해야 할 복무규정은 무엇인가요?"
    
    if eid == 'q_4_0572':
        return "교원의 인터넷 미디어 활동에서 비밀 누설 금지와 품위 유지 의무는 어떻게 적용되나요?"
    
    if eid == 'q_4_0574':
        return "교원의 인터넷 개인 미디어 활동과 관련된 징계 사례가 있나요?"
    
    if eid == 'q_4_0584':
        return "교원이 유튜브나 블로그 등 개인 미디어 활동을 할 때 주의해야 할 사항은 무엇인가요?"
    
    if eid == 'q_4_0589':
        return "교원 인터넷 개인 미디어 활동 지침에서 말하는 '인터넷 개인 미디어 활동'이란 무엇인가요?"
    
    if eid == 'q_4_0593':
        return "교원의 인터넷 개인 미디어 활동이 인사상 불이익이나 징계 사유가 될 수 있나요?"
    
    if eid == 'q_4_0601':
        return "교원이 인터넷 개인 미디어 활동에서 해서는 안 되는 행위는 구체적으로 무엇인가요?"
    
    if eid == 'q_4_0604':
        return "교원의 인터넷 미디어 활동에서 정치적 의견 표명이나 영리행위는 금지되나요?"
    
    if eid == 'q_4_0614':
        return "교원 인터넷 개인 미디어 활동 지침의 주요 내용을 전반적으로 알려주세요."
    
    if eid == 'q_4_0616':
        return "교원 인터넷 개인 미디어 활동과 관련된 주요 질의·응답 사례는 어떤 것이 있나요?"
    
    if eid == 'q_4_0652':
        return "교원의 겸직허가와 인터넷 개인 미디어 활동은 어떤 관계가 있나요?"
    
    if eid == 'q_4_0719':
        return "교원의 겸직 허가를 받으려면 어떤 절차를 거쳐야 하나요?"
    
    if eid == 'q_4_0755':
        return "교원이 외부강의에 출강할 때 복무 처리는 어떻게 해야 하나요?"
    
    if eid == 'q_4_0774':
        return "교원의 외부강의에 적용되는 관련 규정에는 어떤 것들이 있나요?"
    
    if eid == 'q_4_0777':
        return "교원이 외부강의를 하려면 사전에 어떤 사항을 확인하고 처리해야 하나요?"
    
    if eid == 'q_4_0838':
        return "외부강의 시 초과사례금 수수가 제한되는 기준과 금액은 어떻게 되나요?"
    
    if eid == 'q_4_0852':
        return "교원에게 외부강의가 제한되는 경우는 어떤 경우인가요?"
    
    if eid == 'q_4_0880':
        return "청탁금지법에 따른 외부강의 신고 의무와 초과사례금 수수 제한은 어떻게 되나요?"
    
    if eid == 'q_4_0960':
        return "교원 인터넷 미디어 활동이 겸직허가 대상인지 판단하는 기준은 무엇인가요?"
    
    if eid == 'q_4_0988':
        return "교원의 휴가에 관한 특례 적용 대상은 누구이며, 공무외 국외여행은 어떻게 처리하나요?"
    
    if eid == 'q_4_1035':
        return "교원의 휴가일수는 어떻게 계산하나요?"
    
    if eid == 'q_4_1036':
        return "교원이 휴가를 실시할 때 유의해야 할 사항은 무엇인가요?"
    
    if eid == 'q_4_1091':
        return "휴가 실시에 있어서 사전 승인, 잔여 연가 관리 등 유의사항은 무엇인가요?"
    
    if eid == 'q_4_1092':
        return "연가, 병가, 공가, 특별휴가 등 휴가 종류별 실시방법의 기본 기준은 무엇인가요?"
    
    if eid == 'q_4_1108':
        return "교원휴가에 관한 예규 제5조 제1항의 내용은 무엇인가요?"
    
    if eid == 'q_4_1132':
        return "교원의 연가 승인 절차와 기준은 어떻게 되나요?"
    
    if eid == 'q_4_1160':
        return "재직기간별 연가일수와 연가일수 공제 기준은 어떻게 되나요?"
    
    if eid == 'q_4_1170':
        return "교원의 병가 승인 절차와 요건은 어떻게 되나요?"
    
    if eid == 'q_4_1193':
        return "교원의 휴가 종류별(연가, 병가, 공가, 특별휴가) 실시방법을 전반적으로 알려주세요."
    
    if eid == 'q_4_1195':
        return "교원 병가 승인의 세부 기준과 휴직 후 복직 시 병가 처리는 어떻게 되나요?"
    
    if eid == 'q_4_1216':
        return "교원 병가와 관련된 구체적인 사례에는 어떤 것이 있나요?"
    
    if eid == 'q_4_1246':
        return "교원에게 공가가 승인되는 구체적인 사유에는 어떤 것들이 있나요?"
    
    if eid == 'q_4_1247':
        return "공가 승인 사유와 공가제도 운영 시 유의사항은 무엇인가요?"
    
    if eid == 'q_4_1248':
        return "교원 휴가 종류별 실시방법에 관한 법적 근거는 무엇인가요?"
    
    if eid == 'q_4_1256':
        return "공가제도를 운영할 때 주의해야 할 사항은 무엇인가요?"
    
    if eid == 'q_4_1320':
        return "교원의 경조사휴가 일수와 대상 범위는 어떻게 되나요?"
    
    if eid == 'q_4_1334':
        return "교원의 출산휴가 기간과 급여 지급 기준은 어떻게 되나요?"
    
    if eid == 'q_4_1339':
        return "교원에게 부여되는 특별휴가의 종류와 내용은 무엇인가요?"
    
    if eid == 'q_4_1340':
        return "교원의 출산휴가 관련 세부 규정과 기준은 무엇인가요?"
    
    if eid == 'q_4_1346':
        return "교원의 출산휴가 신청 절차와 기간 계산 방법은 어떻게 되나요?"
    
    if eid == 'q_4_1366':
        return "특별휴가의 세부 종류별 부여 기준과 일수는 어떻게 되나요?"
    
    if eid == 'q_4_1367':
        return "출산휴가를 신청할 때 제출해야 할 서류와 확인 사항은 무엇인가요?"
    
    if eid == 'q_4_1423':
        return "교원의 육아시간 사용 요건과 신청 방법은 어떻게 되나요?"
    
    if eid == 'q_4_1437':
        return "육아시간의 사용 기간, 대상 자녀 연령 등 세부 기준은 무엇인가요?"
    
    if eid == 'q_4_1454':
        return "교원의 수업휴가는 어떤 경우에 부여되며, 기간과 조건은 무엇인가요?"
    
    if eid == 'q_4_1462':
        return "육아시간 신청 시 필요한 서류와 행정 처리 절차는 무엇인가요?"
    
    if eid == 'q_4_1531':
        return "교원 공무외 국외여행의 기본방침은 무엇인가요?"
    
    if eid == 'q_4_1556':
        return "교원의 공무외 국외여행 허가 기준과 절차는 어떻게 되나요?"
    
    if eid == 'q_4_1558':
        return "교원이 공무외 국외여행을 신청할 때 확인해야 할 사항은 무엇인가요?"
    
    if eid == 'q_4_1601':
        return "공무외 국외여행과 관련된 기타 유의사항은 무엇인가요?"
    
    if eid == 'q_4_1608':
        return "공무외 국외여행을 나이스에서 상신하는 구체적인 방법은 무엇인가요?"
    
    if eid == 'q_4_1614':
        return "나이스에서 근무상신이 잘못된 경우 어떻게 수정하나요?"
    
    if eid == 'q_4_1627':
        return "교원의 공무외 국외여행에 관한 전반적인 규정과 절차를 알려주세요."
    
    if eid == 'q_4_1629':
        return "공무외 국외여행을 나이스에서 복무 상신하는 방법과 절차는 무엇인가요?"
    
    if eid == 'q_4_1630':
        return "공무외 국외여행 나이스 상신 후 오류가 발생했을 때 수정하는 방법은 무엇인가요?"
    
    # --- 계약제교원 CATEGORY ---
    
    if eid == 'q_5_0029':
        return "계약제교원이란 무엇이며, 기간제교원과 산학겸임교사의 차이는 무엇인가요?"
    
    if eid == 'q_5_0030':
        return "계약제교원을 채용할 수 있는 조건은 무엇인가요?"
    
    if eid == 'q_5_0033':
        return "계약제교원 제도의 운영 목적과 활용 방안은 무엇인가요?"
    
    if eid == 'q_5_0116':
        return "계약제교원 운영의 공통사항에 관한 법적 근거는 무엇인가요?"
    
    if eid == 'q_5_0142':
        return "계약제교원 종류별(기간제교원, 산학겸임교사, 강사 등) 운영 지침의 주요 내용은 무엇인가요?"
    
    if eid == 'q_5_0143':
        return "계약제교원 운영 시 임용권자가 확인해야 할 행정 사항은 무엇인가요?"
    
    if eid == 'q_5_0155':
        return "기간제교원과 산학겸임교사 등 종류별 운영 지침의 차이점은 무엇인가요?"
    
    if eid == 'q_5_0160':
        return "기간제교원의 임용 사유와 자격 요건에 관한 법적 근거는 무엇인가요?"
    
    if eid == 'q_5_0219':
        return "기간제교원 채용 시 가산점은 어떤 경우에 부여되나요?"
    
    if eid == 'q_5_0274':
        return "기간제교원의 인사 관리는 어떻게 이루어지나요?"
    
    if eid == 'q_5_0334':
        return "계약제교원 종류별로 채용, 복무, 보수 등의 운영 기준은 어떻게 다른가요?"
    
    if eid == 'q_5_0338':
        return "계약제교원 종류별 운영 시 학교에서 확인해야 할 사항은 무엇인가요?"
    
    if eid == 'q_5_0376':
        return "계약제교원의 임용 형태에는 어떤 것들이 있나요?"
    
    if eid == 'q_5_0384':
        return "예·체능 및 특성화 교과담당 강사의 채용 절차와 자격 요건은 무엇인가요?"
    
    if eid == 'q_5_0431':
        return "계약제교원에 대한 임금명세서 교부 의무는 어떻게 되나요?"
    
    if eid == 'q_5_0447':
        return "계약제교원의 보수와 처우에 관한 법적 근거는 무엇인가요?"
    
    if eid == 'q_5_0461':
        return "계약제교원의 복무 규정은 어떤 내용을 포함하고 있나요?"
    
    if eid == 'q_5_0463':
        return "계약제교원의 근무시간은 어떻게 정해지나요?"
    
    if eid == 'q_5_0518':
        return "계약제교원에게도 정치활동 금지 규정이 적용되나요?"
    
    if eid == 'q_5_0548':
        return "계약제교원에게 적용되는 근로기준법과 근로기준법 시행규칙의 주요 내용은 무엇인가요?"
    
    if eid == 'q_5_0572':
        return "기간제교원의 수업 결손을 방지하기 위한 조치에는 무엇이 있나요?"
    
    if eid == 'q_5_0573':
        return "계약제교원의 복무에 관한 법적 근거에는 어떤 것들이 있나요?"
    
    if eid == 'q_5_0629':
        return "기간제교원의 계약 기간에 '3월 1일'이 시점으로 포함되는지 여부는 어떻게 판단하나요?"
    
    if eid == 'q_5_0753':
        return "기간제교원에 관한 교육공무원법의 주요 규정은 무엇인가요?"
    
    if eid == 'q_5_0770':
        return "계약제교원 관련 참고자료에는 어떤 법령과 규정이 포함되어 있나요?"
    
    if eid == 'q_5_0772':
        return "계약제교원 제도의 법적 운용 근거는 무엇인가요?"
    
    if eid == 'q_5_0774':
        return "계약제교원 운용에서 임용권자의 역할과 권한은 무엇인가요?"
    
    if eid == 'q_5_0776':
        return "기간제교원의 임용 사유와 자격 요건은 교육공무원법에서 어떻게 규정하고 있나요?"
    
    if eid == 'q_5_0804':
        return "기간제교원 임용 시 특정교과 한시적 담당이란 구체적으로 어떤 경우인가요?"
    
    if eid == 'q_5_0806':
        return "계약제교원 관련하여 교원이 반드시 알아야 할 법령과 규정은 무엇인가요?"
    
    if eid == 'q_5_0807':
        return "계약제교원 운용 근거가 되는 법령에는 어떤 것들이 있나요?"
    
    if eid == 'q_5_0823':
        return "계약제교원과 관련된 교육공무원법, 초·중등교육법 등 주요 규정을 정리해 주세요."
    
    if eid == 'q_5_0824':
        return "교육공무원법과 초·중등교육법에서 계약제교원 운용 근거는 무엇인가요?"
    
    if eid == 'q_5_0825':
        return "공무원보수규정에서 계약제교원의 보수에 관한 내용은 무엇인가요?"
    
    if eid == 'q_5_0826':
        return "계약제교원 관련 법령이 실제 학교 현장에서 어떻게 적용되나요?"
    
    if eid == 'q_5_0839':
        return "초·중등교육법에서 계약제교원과 관련된 조항은 무엇인가요?"
    
    if eid == 'q_5_0851':
        return "계약제교원 관련 주요 법령과 규정의 핵심 내용을 요약해 주세요."
    
    if eid == 'q_5_0854':
        return "계약제교원 관련 법령 적용 시 행정 담당자가 확인해야 할 사항은 무엇인가요?"
    
    if eid == 'q_5_0855':
        return "명예교사와 강사에 관한 법적 규정과 운영 기준은 무엇인가요?"
    
    if eid == 'q_5_0882':
        return "계약제교원 운용에서 관련 법령을 정확히 파악하는 것이 왜 중요한가요?"
    
    if eid == 'q_5_0913':
        return "계약제교원 관련 법령의 구체적인 적용 기준과 범위는 어떻게 되나요?"
    
    if eid == 'q_5_0916':
        return "기간제교원의 담당과목과 관련되는 분야의 직무에는 어떤 것들이 있나요?"
    
    if eid == 'q_5_0958':
        return "기간제 및 단시간근로자 보호법이 계약제교원에게 어떻게 적용되나요?"
    
    if eid == 'q_5_0959':
        return "기간제 및 단시간근로자 보호 등에 관한 법률에서 기간제교원에 관한 규정은 무엇인가요?"
    
    if eid == 'q_5_0982':
        return "아동·청소년의 성보호에 관한 법률 시행령이 계약제교원 채용에 어떻게 적용되나요?"
    
    if eid == 'q_5_0985':
        return "아동·청소년 성보호법 시행령에서 교원 결격사유에 관한 규정은 무엇인가요?"
    
    if eid == 'q_5_0995':
        return "아동복지법 제29조의4에서 규정하는 교원의 결격사유는 무엇인가요?"
    
    if eid == 'q_5_1009':
        return "아동복지법에서 계약제교원 채용 시 확인해야 할 결격사유 규정은 무엇인가요?"
    
    if eid == 'q_5_1011':
        return "계약제교원 채용 시 아동복지법에 따른 결격사유 조회 절차는 어떻게 되나요?"
    
    if eid == 'q_5_1048':
        return "NEIS에서 기간제교원의 인사기록은 어떻게 관리하나요?"
    
    if eid == 'q_5_1075':
        return "NEIS에서 기간제교원 인사기록 자료를 전송하는 방법은 무엇인가요?"
    
    if eid == 'q_5_1076':
        return "기간제교원 인사기록 관리에 관한 법적 근거는 무엇인가요?"
    
    if eid == 'q_5_1078':
        return "기간제교원 인사기록 자료 전송 시 확인해야 할 사항은 무엇인가요?"
    
    if eid == 'q_5_1089':
        return "NEIS에서 기간제교원 인사기록을 관리하는 기준과 절차는 무엇인가요?"
    
    if eid == 'q_5_1090':
        return "NEIS에서 기간제교원의 직전 근무경력을 등록하는 방법은 무엇인가요?"
    
    if eid == 'q_5_1101':
        return "기간제교원의 퇴직 처리 절차는 어떻게 되나요?"
    
    if eid == 'q_5_1107':
        return "NEIS에서 계약제교원 퇴직 처리 화면은 어떻게 사용하나요?"
    
    if eid == 'q_5_1119':
        return "NEIS 기간제교원 인사기록 관리에서 경력증명 관련 규정은 무엇인가요?"
    
    if eid == 'q_5_1121':
        return "기간제교원 인사기록 관리가 교원의 경력 인정에 어떤 영향을 미치나요?"
    
    if eid == 'q_5_1122':
        return "NEIS 기간제교원 인사기록 관리와 관련된 법적 근거는 무엇인가요?"
    
    if eid == 'q_5_1125':
        return "기간제교원 인력풀 등록 절차의 처리 기한은 어떻게 되나요?"
    
    if eid == 'q_5_1126':
        return "기간제교원 인력풀에 등록하려면 어떤 절차를 거쳐야 하나요?"
    
    if eid == 'q_5_1129':
        return "NEIS 기간제교원 인력풀의 조회 권한은 누구에게 부여되나요?"
    
    if eid == 'q_5_1130':
        return "기간제교원 인력풀의 등록 대상은 누구이며, 조회 권한은 어떻게 되나요?"
    
    if eid == 'q_5_1133':
        return "기간제교원 인력풀 등록 희망자에 대한 임용권자의 승인 역할은 무엇인가요?"
    
    if eid == 'q_5_1135':
        return "NEIS 기간제교원 인력풀을 이용하는 구체적인 방법은 무엇인가요?"
    
    if eid == 'q_5_1136':
        return "NEIS 기간제교원 인력풀 이용 시 필요한 조건은 무엇인가요?"
    
    if eid == 'q_5_1137':
        return "학교에서 NEIS 기간제교원 인력풀을 통해 교원을 채용하려면 어떻게 해야 하나요?"
    
    if eid == 'q_5_1139':
        return "NEIS 기간제교원 인력풀의 유효기간은 어떻게 계산하나요?"
    
    if eid == 'q_5_1141':
        return "NEIS 기간제교원 인력풀에 관해 자주 묻는 질문에는 어떤 것이 있나요?"
    
    if eid == 'q_5_1145':
        return "NEIS 기간제교원 인력풀 이용 방법의 구체적인 절차는 무엇인가요?"
    
    if eid == 'q_5_1146':
        return "NEIS 기간제교원 인력풀 검색 화면에서 교원을 조회하는 방법은 무엇인가요?"
    
    if eid == 'q_5_1148':
        return "NEIS 기간제교원 인력풀 이용 시 행정 담당자가 확인해야 할 사항은 무엇인가요?"
    
    if eid == 'q_5_1151':
        return "NEIS 기간제교원 인력풀에 등록하기 위한 자격 요건은 무엇인가요?"
    
    if eid == 'q_5_1152':
        return "NEIS 기간제교원 인력풀 등록 시 필요한 제출 서류는 무엇인가요?"
    
    if eid == 'q_5_1154':
        return "NEIS 기간제교원 인력풀의 등록 기간과 갱신 횟수는 어떻게 되나요?"
    
    if eid == 'q_5_1163':
        return "기간제교원 인력풀 등록이 교원의 신분에 미치는 영향은 무엇인가요?"
    
    if eid == 'q_5_1164':
        return "기간제교원 인력풀 등록 시 서류 제출 기한은 어떻게 되나요?"
    
    if eid == 'q_5_1190':
        return "기간제교원 인력풀에서 신청서를 선택하고 작성하는 방법은 무엇인가요?"
    
    if eid == 'q_5_1202':
        return "계약제교원 인력풀에 본인이 직접 신청하는 방법은 무엇인가요?"
    
    if eid == 'q_5_1526':
        return "기간제교사 육아휴직 시행에 관한 전반적인 안내 내용은 무엇인가요?"
    
    if eid == 'q_5_1532':
        return "기간제교사가 출산휴가와 연계하여 육아휴직을 사용할 수 있나요?"
    
    if eid == 'q_5_1557':
        return "기간제교원의 육아휴직과 복직을 NEIS에서 발령 처리하는 방법은 무엇인가요?"
    
    # ========================================================================
    # FALLBACK: Generate based on pattern analysis
    # ========================================================================
    
    # If we reach here, use content-based generation
    return generate_fallback_question(entry, answer, content_detail, topics, clean_sub, laws, articles, md_content)


def generate_fallback_question(entry, answer, content_detail, topics, clean_sub, laws, articles, md_content):
    """Fallback question generation based on content analysis."""
    category = entry['category']
    subcategory = entry['subcategory']
    keywords = entry.get('keywords', [])
    flags = entry.get('flags', [])
    
    # Clean keywords
    clean_keywords = [k.replace('▢','').replace('▣','').replace('□','').replace('■','').strip() 
                      for k in keywords if k and k not in ['정직', '교원', '임용', '징계', '교장', '교감', '교사']]
    
    # Extract the main topic from the answer
    main_topic = ""
    answer_lines = [l.strip() for l in answer.split('\n') if l.strip() and '안내드립니다' not in l and '설명드리겠습니다' not in l]
    for line in answer_lines:
        if line.startswith('**') and line.endswith('**'):
            main_topic = line.strip('*').strip()
            break
    
    if not main_topic:
        main_topic = clean_sub
    
    # Remove document structure markers
    main_topic = re.sub(r'[▢▣□■※◦∘【】\[\]]', '', main_topic).strip()
    
    if category == '복무':
        if topics['leave']:
            return f"{main_topic}의 구체적인 내용과 적용 기준은 무엇인가요?"
        elif topics['concurrent']:
            return f"{main_topic}에 관한 규정과 허가 기준은 무엇인가요?"
        elif topics['lecture']:
            return f"교원의 {main_topic}에 관한 세부 규정은 무엇인가요?"
        elif topics['media']:
            return f"교원의 인터넷 개인 미디어 활동에서 {main_topic}의 내용은 무엇인가요?"
        elif topics['travel']:
            return f"교원의 {main_topic}에 관한 절차와 기준은 어떻게 되나요?"
        elif topics['nais']:
            return f"나이스에서 {main_topic}을 처리하는 방법은 무엇인가요?"
        elif topics['deputy']:
            return f"{main_topic}에 관한 규정과 적용 기준은 무엇인가요?"
        else:
            return f"{main_topic}에 관한 구체적인 내용은 무엇인가요?"
    
    elif category == '계약제교원':
        if topics['pool']:
            return f"기간제교원 인력풀에서 {main_topic}의 절차와 방법은 무엇인가요?"
        elif topics['nais']:
            return f"NEIS에서 {main_topic}을 처리하는 방법은 무엇인가요?"
        elif topics['employ']:
            return f"계약제교원 {main_topic}의 구체적인 내용과 기준은 무엇인가요?"
        elif topics['salary']:
            return f"계약제교원의 {main_topic}에 관한 규정은 무엇인가요?"
        elif topics['child_protect']:
            return f"계약제교원 채용 시 {main_topic}에 따른 결격사유 확인은 어떻게 하나요?"
        elif topics['law']:
            return f"{main_topic}에서 계약제교원에 관한 규정은 무엇인가요?"
        else:
            return f"계약제교원의 {main_topic}에 관한 구체적인 내용은 무엇인가요?"
    
    return f"{main_topic}에 관한 구체적인 내용과 적용 기준은 무엇인가요?"


def main():
    # Load problematic entries
    with open('/home/user/menual/problematic_entries.json', 'r', encoding='utf-8') as f:
        all_entries = json.load(f)
    
    # Filter to target categories
    target_entries = [e for e in all_entries if e['category'] in ('복무', '계약제교원')]
    
    print(f"Total problematic entries: {len(all_entries)}")
    print(f"Target entries (복무 + 계약제교원): {len(target_entries)}")
    
    regenerated = []
    unchanged_count = 0
    
    for entry in target_entries:
        new_question = generate_question(entry)
        
        # Clean any remaining ▢ symbols
        new_question = new_question.replace('▢', '').replace('▣', '').replace('□', '').replace('■', '').strip()
        
        # Also clean the answer of leading ▢ 
        new_answer = entry['answer']
        # Don't modify the answer content per instructions, but do clean ▢ from beginning
        
        # Also clean keywords of ▢
        clean_keywords = [k.replace('▢','').replace('▣','').strip() for k in entry.get('keywords', [])]
        clean_keywords = [k for k in clean_keywords if k]  # remove empty
        
        new_entry = {
            'id': entry['id'],
            'question': new_question,
            'answer': new_answer,
            'sources': entry['sources'],
            'category': entry['category'],
            'subcategory': entry['subcategory'],
            'keywords': clean_keywords,
        }
        
        if new_question == entry['question']:
            unchanged_count += 1
        
        regenerated.append(new_entry)
    
    # Write output
    output_path = '/home/user/menual/regenerated_cat4_5.jsonl'
    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in regenerated:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    print(f"\nRegenerated: {len(regenerated)} entries")
    print(f"Unchanged questions: {unchanged_count}")
    print(f"Output: {output_path}")
    
    # Print some examples for verification
    print("\n" + "="*80)
    print("SAMPLE REGENERATED ENTRIES:")
    print("="*80)
    
    for i, (orig, regen) in enumerate(zip(target_entries[:10], regenerated[:10])):
        print(f"\n--- {regen['id']} ---")
        print(f"  OLD: {orig['question']}")
        print(f"  NEW: {regen['question']}")
        print(f"  FLAGS: {orig.get('flags', [])}")

if __name__ == '__main__':
    main()
