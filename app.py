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
    # Pompian(2008) 기준: a가 많으면(6개 이상) Active
    is_active = active_a >= 6
    
    # Grable & Lytton(1999) 기준 등급 [cite: 792-831]
    if rt_score <= 22:
        rt_level = "Low"
    elif rt_score <= 32:
        rt_level = "Medium"
    else:
        rt_level = "High"
    
    # 최종 매칭
    if not is_active:
        return "보존가 (Passive Preserver)" if rt_level == "Low" else "추종자 (Friendly Follower)"
    else:
        return "축적가 (Active Accumulator)" if rt_level == "High" else "독립가 (Independent Individualist)"

# --- 설문 문항 및 점수 매핑 데이터 ---
POMPIAN_QUESTIONS = [
    ("1. 미래에 보유할 자산의 대부분을 본인의 노력과 소득으로 직접 일구고 싶습니까?", {"예": 1, "아니오": 0}),
    ("2. 자산을 형성하는 과정에서 본인의 자본을 직접 위험에 노출(창업, 공격적 투자 등)시킬 의향이 있습니까?", {"예": 1, "아니오": 0}),
    ("3. 당신은 어떤 목표가 더 강합니까?", {"위험을 감수하더라도 큰 부를 쌓기": 1, "현재 가진 것을 안전하게 지키기": 0}),
    ("4. 투자를 관리할 때 본인이 직접 결정권을 갖고 싶습니까, 아니면 전문가에게 전적으로 맡기고 싶습니까?", {"직접 결정": 1, "전문가 위임": 0}),
    ("5. 당신은 스스로가 투자자로서 높은 능력을 갖추게 될 것이라고 믿습니까?", {"예": 1, "아니오": 0}),
    ("6. 두 가지 포트폴리오 중 하나를 고른다면?", {"주식 80%, 채권 20%": 1, "주식 40%, 채권 60%": 0}),
    ("7. 당신의 부의 목표는 무엇입니까?", {"생활 수준을 희생해서라도 큰 자산 축적": 1, "현재의 편안한 생활 수준 유지": 0}),
    ("8. 사회생활이나 공부를 할 때 당신은 주로 스스로 일을 찾아 하는 편입니까, 아니면 가이드라인을 따르는 편입니까?", {"자기 주도형": 1, "가이드라인 선호": 0}),
    ("9. 투자 시 무엇에 더 매력을 느낍니까?", {"큰 수익을 위해 자본을 위험에 노출하기": 1, "정기적이고 안정적인 수익 창출": 0}),
    ("10. 대출을 활용한 투자(레버리지)에 대해 어떻게 생각합니까?", {"부를 불리는 유용한 도구다": 1, "가급적 피해야 할 위험한 일이다": 0})
]

GL_QUESTIONS = [
    ("1. 주변 친구들은 당신을 어떤 사람으로 보나요?", {"도박꾼": 4, "철저한 조사 후 위험 감수": 3, "신중함": 2, "위험 회피": 1}),
    ("2. 상금이 걸린 퀴즈쇼에서 하나를 고른다면?", {"현금 100만 원 그냥 받기": 1, "50% 확률 500만 원": 2, "25% 확률 1,000만 원": 3, "5% 확률 1억 원": 4}),
    ("3. 아르바이트비를 모아 여행 가려는데, 갑자기 노트북이 고장 났습니다.", {"여행 취소": 1, "저렴한 여행으로 변경": 2, "예정대로 가고 노트북은 나중에 고민": 3, "어차피 돈 나갈 거 더 좋은 곳으로 여행 감": 4}),
    ("4. 2,600만 원의 종잣돈이 생겼다면 어디에 넣겠습니까?", {"예금/CD": 1, "안전한 우량 채권": 2, "주식형 펀드": 3}),
    ("5. 주식 투자를 하는 것에 대해 얼마나 심리적으로 편안함을 느낍니까?", {"전혀 느끼지 못함": 1, "어느 정도 느낌": 2, "매우 편안함": 3}),
    ("6. '투자 위험'이라는 단어를 들으면?", {"손실": 1, "불확실성": 2, "기회": 3, "전율": 4}),
    ("7. 전문가들이 가상자산이나 부동산 급등을 예측합니다. 당신은 전액 예금에 있습니다.", {"그대로 유지": 1, "절반만 투자": 2, "전액 투자": 3, "대출까지 받아 투자": 4}),
    ("8. 다음 수익 구조 중 무엇이 가장 마음에 드나요?", {"$200 이익 / 손실 없음": 1, "$800 이익 / $200 손실 가능": 2, "$2,600 이익 / $800 손실 가능": 3, "$4,800 이익 / $2,400 손실 가능": 4}),
    ("9. 당신에게 공짜로 100만 원이 생겼다고 가정해 봅시다. 이때 다음 중 하나를 반드시 선택해야 한다면 무엇을 고르겠습니까?", {"확실하게 50만 원을 더 받기": 1, "동전 앞면이 나오면 100만 원을 더 받고, 뒷면이 나오면 아무것도 못 받기": 3}),
    ("10. 당신에게 공짜로 200만 원이 생겼는데, 갑자기 세금이나 벌금으로 일부를 내야 하는 상황입니다. 다음 중 하나를 반드시 선택해야 한다면 무엇을 고르겠습니까?", {"확실하게 50만 원을 세금으로 내기": 1, "동전 앞면이 나오면 100만 원을 내고, 뒷면이 나오면 하나도 안 내기": 3}),
    ("11. 유산으로 받은 1억 원을 딱 한 곳에만 넣어야 한다면?", {"MMF/예금": 1, "혼합형 펀드": 2, "주식 포트폴리오": 3, "원자재/금": 4}),
    ("12. 당신이 2,000만 원을 투자한다면, 다음 중 어떤 포트폴리오(자산 구성) 비중이 가장 매력적으로 느껴지나요?", {"안전한 예적금 60% + 중위험 자산 30% + 고위험 자산 10%": 1, "안전한 예적금 30% + 중위험 자산 40% + 고위험 자산 30%": 2, "안전한 예적금 10% + 중위험 자산 40% + 고위험 자산 50%": 3}),
    ("13. 성공 확률 20%인 친구의 벤처 사업에 투자한다면?", {"투자 안 함": 1, "한 달 치 용돈": 2, "석 달 치 용돈": 3, "반년 치 용돈": 4})
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
            if st.button("🛑 실험 종료", use_container_width=True, disabled=not is_started):
                update_experiment_state(False)
                st.rerun()

        st.divider()
        
        if st.button("🔄 현황 새로고침"):
            res = supabase.table("student_investor_results").select("*").order("created_at").execute().data
            total_students = len(res)
            finished_students = [r for r in res if r['is_finished']]
            
            st.metric("참여 인원", f"{total_students}명", f"완료: {len(finished_students)}명")
            
            if finished_students:
                st.subheader("📊 학생별 상세 결과")
                display_data = []
                for r in finished_students:
                    display_data.append({
                        "이름": r['nickname'],
                        "능동성 (Active/Passive)": "Active" if r['active_a_count'] >= 6 else "Passive",
                        "위험 수용도 (점수 합계)": r['rt_total_score'],
                        "최종 유형 (BIT)": r['bit_type']
                    })
                st.dataframe(display_data, use_container_width=True)
                
                st.subheader("📈 최종 유형 (BIT) 분포")
                types = [r['bit_type'] for r in finished_students]
                type_counts = {t: types.count(t) for t in set(types)}
                st.bar_chart(type_counts)
    elif password:
        st.error("비밀번호가 틀렸습니다.")

else:
    st.title("💸 나의 투자 DNA 찾기")
    nickname = st.sidebar.text_input("본인의 별명을 입력하세요")
    
    if nickname:
        student = get_student(nickname)
        if not student:
            create_student(nickname)
            student = get_student(nickname)
            
        is_started = get_experiment_state()
        
        if not is_started:
            st.warning(f"안녕하세요 {nickname}님! 교수님이 실험을 시작하실 때까지 대기해 주세요.")
        elif student['is_finished']:
            st.success("🎉 진단이 완료되었습니다!")
            st.markdown(f"### {nickname}님의 투자자 유형은 **[{student['bit_type']}]** 입니다.")
            
            # 흥미 요소: 유형별 슬로건 및 주의할 편향 빌런
            slogans = {
                "보존가 (Passive Preserver)": ("내 자산은 내가 지킨다! 철벽 방어의 수호자 🛡️", "손실 회피 빌런 (내 사전에 손절이란 없다!)"),
                "추종자 (Friendly Follower)": ("트렌드는 놓칠 수 없지! 친절한 유행 선도자 🌊", "최근 편향 빌런 (요즘 뜨는 게 무조건 최고야!)"),
                "독립가 (Independent Individualist)": ("나만의 길을 간다! 확신에 찬 분석가 🕵️‍♂️", "확증 편향 빌런 (내 분석은 절대 틀리지 않아!)"),
                "축적가 (Active Accumulator)": ("공격이 최선의 방어! 열정적인 자산가 ⚔️", "통제의 환상 빌런 (이 시장은 내가 지배한다!)")
            }
            
            if student['bit_type'] in slogans:
                st.info(f"✨ **특징:** {slogans[student['bit_type']][0]}")
                st.error(f"👾 **주의해야 할 내 안의 빌런:** {slogans[student['bit_type']][1]}")
                
            st.write("교수님의 해설 강의를 통해 본인의 유형이 가진 장단점을 확인해 보세요!")
        else:
            with st.form("investor_test"):
                st.subheader("Part 1. 미래의 자산 형성 태도 (능동성 진단)")
                pompian_responses = []
                for q, options in POMPIAN_QUESTIONS:
                    resp = st.radio(q, list(options.keys()), index=None)
                    pompian_responses.append((resp, options))
                    
                st.divider()
                
                st.subheader("Part 2. 재무적 위험 수용도 진단")
                gl_responses = []
                for q, options in GL_QUESTIONS:
                    resp = st.radio(q, list(options.keys()), index=None)
                    gl_responses.append((resp, options))
                
                submitted = st.form_submit_button("결과 확인하기")
                
                if submitted:
                    # 응답 누락 확인
                    if any(r[0] is None for r in pompian_responses) or any(r[0] is None for r in gl_responses):
                        st.error("모든 문항에 응답해 주세요.")
                    else:
                        # 점수 계산
                        a_count = sum(opts[ans] for ans, opts in pompian_responses)
                        rt_total = sum(opts[ans] for ans, opts in gl_responses)
                        
                        final_bit = calculate_bit(a_count, rt_total)
                        update_student_result(nickname, a_count, rt_total, final_bit)
                        st.rerun()