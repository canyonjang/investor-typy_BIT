import streamlit as st
from supabase import create_client, Client

# --- 기본 설정 ---
st.set_page_config(page_title="투자자 DNA 진단 시스템", page_icon="🧬", layout="wide")

# --- Supabase 연결 ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# --- 데이터베이스 헬퍼 함수 ---
def get_experiment_state():
    res = supabase.table("experiment_state").select("is_started").eq("id", 1).execute()
    return res.data[0]['is_started'] if res.data else False

def update_experiment_state(state: bool):
    supabase.table("experiment_state").update({"is_started": state}).eq("id", 1).execute()

def get_student(nickname: str):
    res = supabase.table("student_investor_results").select("*").eq("nickname", nickname).execute()
    return res.data[0] if res.data else None

def create_student(nickname: str):
    supabase.table("student_investor_results").insert({"nickname": nickname}).execute()

def update_student_result(nickname: str, a_count: int, rt_score: int, bit_type: str):
    supabase.table("student_investor_results").update({
        "active_a_count": a_count,
        "rt_total_score": rt_score,
        "bit_type": bit_type,
        "is_finished": True
    }).eq("nickname", nickname).execute()

# --- 로직 함수 ---
def calculate_bit(active_a: int, rt_score: int) -> str:
    # Pompian(2008) 기준: a가 많으면(6개 이상) Active [cite: 542]
    is_active = active_a >= 6
    
    # Grable & Lytton(1999) 기준 등급 [cite: 897, 900-901]
    if rt_score <= 22:
        rt_level = "Low"
    elif rt_score <= 32:
        rt_level = "Medium"
    else:
        rt_level = "High"
    
    # 최종 매칭 [cite: 580-583]
    if not is_active:
        return "보존가 (Passive Preserver)" if rt_level == "Low" else "추종자 (Friendly Follower)"
    else:
        return "축적가 (Active Accumulator)" if rt_level == "High" else "독립가 (Independent Individualist)"

# --- 설문 문항 데이터 통합 (총 24문항: Pompian 10 + 함정 1 + GL 13) ---
ALL_QUESTIONS = [
    # Part 1 (Pompian)
    {"id": "p1", "part": "Part 1.", "q": "1. 미래에 보유할 자산의 대부분을 본인의 노력과 소득으로 직접 일구고 싶습니까?", "options": {"예": 1, "아니오": 0}},
    {"id": "p2", "part": "Part 1.", "q": "2. 자산을 형성하는 과정에서 본인의 자본을 직접 위험에 노출(창업, 공격적 투자 등)시킬 의향이 있습니까?", "options": {"예": 1, "아니오": 0}},
    {"id": "p3", "part": "Part 1.", "q": "3. 당신은 어떤 목표가 더 강합니까?", "options": {"위험을 감수하더라도 큰 부를 쌓기": 1, "현재 가진 것을 안전하게 지키기": 0}},
    {"id": "p4", "part": "Part 1.", "q": "4. 투자를 관리할 때 본인이 직접 결정권을 갖고 싶습니까, 아니면 전문가에게 전적으로 맡기고 싶습니까?", "options": {"직접 결정": 1, "전문가 위임": 0}},
    {"id": "p5", "part": "Part 1.", "q": "5. 당신은 스스로가 투자자로서 높은 능력을 갖추게 될 것이라고 믿습니까?", "options": {"예": 1, "아니오": 0}},
    {"id": "p6", "part": "Part 1.", "q": "6. 두 가지 포트폴리오 중 하나를 고른다면?", {"주식 80%, 채권 20%": 1, "주식 40%, 채권 60%": 0}},
    {"id": "p7", "part": "Part 1.", "q": "7. 당신의 부의 목표는 무엇입니까?", {"생활 수준을 희생해서라도 큰 자산 축적": 1, "편안한 생활 수준 유지": 0}},
    {"id": "p8", "part": "Part 1.", "q": "8. 사회생활이나 공부를 할 때 당신은 주로 스스로 일을 찾아 하는 편입니까, 아니면 가이드라인을 따르는 편입니까?", {"자기 주도형": 1, "가이드라인 선호": 0}},
    {"id": "p9", "part": "Part 1.", "q": "9. 투자 시 무엇에 더 매력을 느깁니까?", {"큰 수익을 위해 자본을 위험에 노출하기": 1, "정기적이고 안정적인 수익 창출": 0}},
    {"id": "p10", "part": "Part 1.", "q": "10. 대출을 활용한 투자(레버리지)에 대해 어떻게 생각합니까?", {"부를 불리는 유용한 도구다": 1, "가급적 피해야 할 위험한 일이다": 0}},
    
    # 함정 문항 (주의 집중 점검)
    {"id": "trap", "part": "주의 집중 점검", "q": "현재 문항은 여러분이 설문을 꼼꼼히 읽고 있는지 확인하기 위한 문항입니다. 이 문항에서는 '4번'을 선택해 주세요.", "options": {"1번": 0, "2번": 0, "3번": 0, "4번": 0}, "is_trap": True},
    
    # Part 2 (Grable & Lytton)
    {"id": "r1", "part": "Part 2.", "q": "1. 주변 친구들은 당신을 어떤 사람으로 보나요?", {"도박꾼": 4, "철저한 조사 후 위험 감수": 3, "신중함": 2, "위험 회피": 1}},
    {"id": "r2", "part": "Part 2.", "q": "2. 상금이 걸린 퀴즈쇼에서 하나를 고른다면?", {"현금 100만 원 그냥 받기": 1, "50% 확률 500만 원": 2, "25% 확률 1,000만 원": 3, "5% 확률 1억 원": 4}},
    {"id": "r3", "part": "Part 2.", "q": "3. 아르바이트비를 모아 여행 가려는데, 갑자기 노트북이 고장 났습니다.", {"여행 취소": 1, "저렴한 여행으로 변경": 2, "예정대로 가고 노트북은 나중에 고민": 3, "어차피 돈 나갈 거 더 좋은 곳으로 여행 감": 4}},
    {"id": "r4", "part": "Part 2.", "q": "4. 2,600만 원의 종잣돈이 생겼다면 어디에 넣겠습니까?", {"예금/CD": 1, "안전한 우량 채권": 2, "주식형 펀드": 3}},
    {"id": "r5", "part": "Part 2.", "q": "5. 주식 투자를 하는 것에 대해 얼마나 심리적으로 편안함을 느깁니까?", {"전혀 느끼지 못함": 1, "어느 정도 느낌": 2, "매우 편안함": 3}},
    {"id": "r6", "part": "Part 2.", "q": "6. '투자 위험'이라는 단어를 들으면 무엇이 떠오릅니까?", {"손실": 1, "불확실성": 2, "기회": 3, "전율": 4}},
    {"id": "r7", "part": "Part 2.", "q": "7. 전문가들이 가상자산이나 부동산 급등을 예측합니다. 당신은 전액 예금에 있습니다.", {"그대로 유지": 1, "절반만 투자": 2, "전액 투자": 3, "대출까지 받아 투자": 4}},
    {"id": "r8", "part": "Part 2.", "q": "8. 다음 수익 구조 중 무엇이 가장 마음에 드나요?", {"200만원 이익 / 손실 없음": 1, "800만원 이익 / 200만원 손실 가능": 2, "2,600만원 이익 / 800만원 손실 가능": 3, "4,800만원 이익 / 2,400만원 손실 가능": 4}},
    {"id": "r9", "part": "Part 2.", "q": "9. 당신에게 공짜로 100만 원이 생겼다고 가정해 봅시다. 이때 다음 중 하나를 반드시 선택해야 한다면 무엇을 고르겠습니까?", {"확실하게 50만 원을 더 받기": 1, "동전 앞면이 나오면 100만 원을 더 받고, 뒷면이 나오면 아무것도 못 받기": 3}},
    {"id": "r10", "part": "Part 2.", "q": "10. 당신에게 공짜로 200만 원이 생겼는데, 갑자기 세금이나 벌금으로 일부를 내야 하는 상황입니다. 다음 중 하나를 반드시 선택해야 한다면 무엇을 고르겠습니까?", {"확실하게 50만 원을 세금으로 내기": 1, "동전 앞면이 나오면 100만 원을 내고, 뒷면이 나오면 하나도 안 내기": 3}},
    {"id": "r11", "part": "Part 2.", "q": "11. 유산으로 받은 1억 원을 딱 한 곳에만 넣어야 한다면?", {"MMF/예금": 1, "혼합형 펀드": 2, "주식 포트폴리오": 3, "원자재/금": 4}},
    {"id": "r12", "part": "Part 2.", "q": "12. 당신이 2,000만 원을 투자한다면, 다음 중 어떤 포트폴리오(자산 구성) 비중이 가장 매력적으로 느껴지나요?", {"안전한 예적금 60% + 중위험 자산 30% + 고위험 자산 10%": 1, "안전한 예적금 30% + 중위험 자산 40% + 고위험 자산 30%": 2, "안전한 예적금 10% + 중위험 자산 40% + 고위험 자산 50%": 3}},
    {"id": "r13", "part": "Part 2.", "q": "13. 성공 확률 20%인 친구의 벤처 사업에 투자한다면?", {"투자 안 함": 1, "한 달 치 용돈": 2, "석 달 치 용돈": 3, "반년 치 용돈": 4}}
]

# --- UI 섹션 ---
st.sidebar.title("🔐 로그인")
role = st.sidebar.radio("접속 모드", ["학생용", "교수용(관리자)"])

if role == "교수용(관리자)":
    admin_pw = st.secrets["admin_password"]
    password = st.sidebar.text_input("관리자 비번", type="password")
    
    if password == admin_pw:
        st.header("👨‍🏫 실험 통제 및 결과 대시보드")
        is_started = get_experiment_state()
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 실험 시작", use_container_width=True, disabled=is_started):
                update_experiment_state(True)
                st.rerun()
        with col2:
            if st.button("🔄 실험 초기화 (대기 상태로)", use_container_width=True, disabled=not is_started):
                update_experiment_state(False)
                st.rerun()

        st.divider()
        
        if st.button("📊 현황 새로고침"):
            res = supabase.table("student_investor_results").select("*").order("created_at").execute().data
            total_students = len(res)
            finished_students = [r for r in res if r['is_finished']]
            st.metric("참여 인원", f"{total_students}명", f"완료: {len(finished_students)}명")
            
            if finished_students:
                st.subheader("📋 학생별 상세 결과")
                display_data = []
                for r in finished_students:
                    display_data.append({
                        "이름": r['nickname'],
                        "능동성": "Active" if r['active_a_count'] >= 6 else "Passive",
                        "RT점수": r['rt_total_score'],
                        "최종 유형": r['bit_type']
                    })
                st.dataframe(display_data, use_container_width=True)
                st.subheader("📈 최종 유형 분포")
                types = [r['bit_type'] for r in finished_students]
                st.bar_chart({t: types.count(t) for t in set(types)})
    elif password:
        st.error("비밀번호가 틀렸습니다.")

else: # 학생용 화면
    nickname = st.sidebar.text_input("본인의 별명을 입력하세요")
    if nickname:
        student = get_student(nickname)
        if not student:
            create_student(nickname)
            student = get_student(nickname)
            
        is_started = get_experiment_state()
        
        if not is_started:
            st.warning(f"안녕하세요 {nickname}님! 교수님이 실험을 시작하실 때까지 대기해 주세요.")
            if st.button("🚀 교수님이 '시작'하셨다고 하면 누르세요!"):
                st.rerun()
        elif student['is_finished']:
            st.success("진단이 완료되었습니다.")
        else:
            # --- 세션 기반 1페이지 1문항 로직 ---
            if 'q_idx' not in st.session_state:
                st.session_state.q_idx = 0
            if 'answers' not in st.session_state:
                st.session_state.answers = {}

            q_idx = st.session_state.q_idx
            total_q = len(ALL_QUESTIONS)
            current_q = ALL_QUESTIONS[q_idx]
            
            # --- 아바타 진화 및 프로그레스 바 ---
            progress = (q_idx + 1) / total_q
            if q_idx < 5: avatar = "🥚 (알)"
            elif q_idx < 15: avatar = "🐥 (병아리)"
            elif q_idx < 23: avatar = "🐓 (닭)"
            else: avatar = "🦅 (독수리)"

            col_avatar, col_prog = st.columns([1, 4])
            with col_avatar:
                st.markdown(f"### {avatar}")
            with col_prog:
                st.progress(progress)
                st.caption(f"문항 진행도: {q_idx + 1} / {total_q}")

            st.divider()
            
            # 문항 표시
            st.write(f"**{current_q['part']}**")
            choice = st.radio(current_q['q'], list(current_q['options'].keys()), index=None, key=f"q_{q_idx}")

            col_prev, col_next = st.columns(2)
            with col_next:
                if q_idx < total_q - 1:
                    if st.button("다음 ➡️", use_container_width=True):
                        if choice is not None:
                            st.session_state.answers[current_q['id']] = current_q['options'][choice]
                            st.session_state.q_idx += 1
                            st.rerun()
                        else:
                            st.error("답변을 선택해 주세요.")
                else:
                    if st.button("제출하기 ✅", use_container_width=True):
                        if choice is not None:
                            # 마지막 문항 저장 및 최종 계산
                            st.session_state.answers[current_q['id']] = current_q['options'][choice]
                            
                            # 점수 합산
                            a_count = sum([v for k, v in st.session_state.answers.items() if k.startswith('p')])
                            rt_score = sum([v for k, v in st.session_state.answers.items() if k.startswith('r')])
                            
                            final_bit = calculate_bit(a_count, rt_score)
                            update_student_result(nickname, a_count, rt_score, final_bit)
                            st.rerun()
                        else:
                            st.error("마지막 답변을 선택해 주세요.")
            
            with col_prev:
                if q_idx > 0:
                    if st.button("⬅️ 이전", use_container_width=True):
                        st.session_state.q_idx -= 1
                        st.rerun()
