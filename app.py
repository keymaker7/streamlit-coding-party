import streamlit as st
import pandas as pd
import requests
import base64
import json
import altair as alt

# =====================================================================
# GAS URL (제공된 최신 URL 적용)
# =====================================================================
GAS_API_URL = "https://script.google.com/macros/s/AKfycbwfy-Je2eJmhZ6iHH-8lRfziMzdh-nZ5cfbHkgMAdpv9J8R7zAEDGViwGT23j8GxyHt/exec" 
# =====================================================================

# 이미지 URL (로딩 속도 개선을 위해 이전 이미지 주소를 유지합니다.)
IMAGE_URL = "https://i.imgur.com/1p9X2fB.png" 

# 데이터 조회 (GET 요청) - 캐싱으로 성능 최적화
@st.cache_data(ttl=300) 
def fetch_data(action):
    try:
        response = requests.get(GAS_API_URL, params={'action': action})
        response.raise_for_status() 
        
        result = response.json()
        
        if result.get("status") == "success":
            return {"status": "success", "data": result.get("data")}
        else:
            return {"status": "error", "message": result.get("message", "GAS에서 알 수 없는 오류가 반환되었습니다.")}
            
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"API 통신 오류 (네트워크/권한 문제 확인): {e}"}
    except json.JSONDecodeError:
        return {"status": "error", "message": "API 응답이 유효한 JSON 형식이 아닙니다. (GAS 코드/배포 확인 필요)"}


# 폼 제출 (POST 요청)
def submit_form(grade, class_value, num, name, mission, uploaded_file):
    
    file_data_url = None
    if uploaded_file:
        file_bytes = uploaded_file.read()
        file_type = uploaded_file.type
        file_base64 = base64.b64encode(file_bytes).decode('utf-8')
        file_data_url = f"data:{file_type};base64,{file_base64}"
        
    payload = {
        "grade": grade,
        "classValue": class_value,
        "num": num,
        "name": name,
        "mission": mission,
        "fileDataUrl": file_data_url 
    }

    try:
        st.info("제출 중입니다. 잠시만 기다려 주세요...")
        response = requests.post(GAS_API_URL, json=payload)
        response.raise_for_status() 
        
        result = response.json()
        
        if result.get("status") == "success":
            st.success(f"✅ {result.get('message')}")
            st.cache_data.clear() 
            st.rerun() 
        else:
            st.error(f"❌ 제출 실패: {result.get('message')}")
            
    except requests.exceptions.RequestException as e:
        st.error(f"❌ 제출 중 API 통신 오류가 발생했습니다: {e}")
    except json.JSONDecodeError:
        st.error("❌ API 응답이 유효한 JSON 형식이 아닙니다. GAS 설정을 확인하세요.")


# 순위 및 차트 표시 함수 (UnboundLocalError 수정)
def display_rankings_and_charts():
    # ----------------------------------------------------------------------------------
    # 순위 영역
    # ----------------------------------------------------------------------------------
    st.subheader("🏆 참여王 Top 3")
    top_students_res = fetch_data('top_students')
    
    if top_students_res["status"] == "success":
        # 성공 시에만 top_students 변수 선언 및 사용
        top_students = top_students_res["data"]
        
        if not top_students:
            st.info("🚀 아직 참여한 학생이 없습니다. 첫 번째 주인공이 되어보세요!")
        else:
            for i, student in enumerate(top_students):
                rank = i + 1
                medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉";
                st.markdown(
                    f"<div style='background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-bottom: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>"
                    f"**{medal} {student['student']}** ({student['count']}회 참여)</div>", 
                    unsafe_allow_html=True
                )
    else:
        st.error(f"순위 데이터를 불러올 수 없습니다: {top_students_res['message']}")
        
    st.markdown("---") 
    
    # ----------------------------------------------------------------------------------
    # 차트 영역
    # ----------------------------------------------------------------------------------
    st.subheader("📊 학급별 참여 현황")
    class_ranking_res = fetch_data('class_ranking')
    
    if class_ranking_res["status"] == "success":
        data_arr = class_ranking_res["data"]
        
        if len(data_arr) <= 1:
            st.info("📊 데이터가 부족하여 차트를 표시할 수 없습니다.")
            return

        df = pd.DataFrame(data_arr[1:], columns=data_arr[0])
        df.columns = ['class', 'count'] 
        df['count'] = pd.to_numeric(df['count']) 
        
        df_chart = df.copy() 
        
        # Altair 차트 생성 (가로 막대)
        chart = alt.Chart(df_chart).mark_bar(color='#4a6cf7').encode(
            y=alt.Y('class', title='학년/반', sort='-x'), 
            x=alt.X('count', title='참여 인원'),   
            tooltip=['class', 'count']
        ).properties(
            height=alt.Step(25) 
        ).interactive() 

        st.altair_chart(chart, use_container_width=True) 
    else:
        st.error(f"차트 데이터를 불러올 수 없습니다: {class_ranking_res['message']}")


# Streamlit 메인 함수
def main():
    st.set_page_config(page_title="코딩 파티 제출 (Streamlit)", layout="wide") 
    
    # ----------------------------------------------------
    # 화면 분할: 좌측에 이미지만 (2), 우측에 모든 콘텐츠 (3)
    # ----------------------------------------------------
    col_image, col_content = st.columns([2, 3]) 
    
    # [1] 좌측 열: 배경 이미지
    with col_image:
        st.image(IMAGE_URL, use_container_width=True) 
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True) 
        
    # [2] 우측 열: 모든 콘텐츠 (제목, 폼, 순위, 차트)
    with col_content:
        # 타이틀과 설명은 콘텐츠 영역 상단에 배치
        st.title("💻 [시즌2]효행초 코딩 파티 대전 ✨")
        st.markdown("코딩 미션에 참여하고 결과를 제출하여 우리 반 순위를 올려보세요!")
        st.link_button("🎮 코딩파티 사이트 바로가기", "https://www.software.kr/")
        st.markdown("---")
        
        # 폼 제출 영역
        st.header("🎉 미션 결과 제출하기")
        with st.form("mission_form", clear_on_submit=True):
            st.markdown("### 학생 정보")
            # 학년, 반, 번호, 이름을 4개 열로 분할
            col1, col2, col3, col4 = st.columns(4) 
            
            with col1:
                st.selectbox("학년", options=[''] + [str(i) for i in range(1, 7)], label_visibility="collapsed", key='grade')
            
            # 학년 선택에 따른 반 옵션 동적 설정 (Session State 이용)
            grade = st.session_state.grade
            class_options_map = {'1': 6, '2': 8, '3': 9, '4': 11, '5': 10, '6': 10}
            max_class = class_options_map.get(grade, 10) if grade else 10
            
            with col2:
                st.selectbox("반", options=[''] + [str(i) for i in range(1, max_class + 1)], label_visibility="collapsed", key='class_value')
                
            with col3:
                st.selectbox("번호", options=[''] + [str(i) for i in range(1, 31)], label_visibility="collapsed", key='num')
            
            with col4:
                st.text_input("이름", placeholder="이름", label_visibility="collapsed", key='name')
            
            st.markdown("---") 
            
            st.markdown("### 참여 미션")
            mission_options = [''] + [
                '구해줘! 펭수', '달려라! 펭수', '뚜앙과 블록코딩 첫걸음', '잡지마! 펭수', '점박이와 코딩을!', 
                '옥토스튜디오로 지구 살리기 - 도전! 퓨처비 챌리지 미니', '마인크래프트 히어로의 여정 (Minecraft Hero\'s Journey)', 
                '뮤직랩 (Music Lab: Jam Session)', '코딩은 동물도 춤추게 한다?', '엔트리로 만드는 교과세상', 
                '코드아카데미', '구름콩콩', '블록코딩 챌린지', '흰동가리를 찾아라', '알고리즘으로 여는 세상', 
                '처음 시작하는 코딩', '하랑이와 함께 하는 한글 코딩', '파이썬으로 떠나는 헬로빗의 당근 수집 여행', 
                '달려라! AI펭카', '날아라! 펭보드', '인공지능 스마트팜', '바다환경을 위한 AI (AI for Oceans)', 
                '댄스파티 (Dance Party) AI 에디션', '지피틴즈 AI와 함께하는 진로탐험', '스크래치로 함께 공부하는 AI', 
                '누구를 구할까요', '나의 AI 프라이버시', '판다공항', '챗코에게 질문해요', 'S.O.S 세계수를 구하라!', 
                '모모의 신비한 AI상점', '도와줘! 펭카페', '체셔의 퀴즈', '펫 키우기', '알고리즘 온라인저지', 
                'CT 잠재력 테스트', '코드 아케이드', '매직 핑거', 'AI 탐험대'
            ]
            st.selectbox("참여한 코딩파티 미션을 선택하세요", options=mission_options, label_visibility="collapsed", key='mission')
            
            st.markdown("---") 

            st.markdown("### 수료증 또는 활동 캡처 사진 제출")
            uploaded_file = st.file_uploader("📷 클릭 또는 파일을 드래그하여 업로드", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
            
            submitted = st.form_submit_button("🎉 참여 완료하기", use_container_width=True)
            
            if submitted:
                # 폼에서 입력된 값들을 세션 상태에서 가져옴
                grade_val = st.session_state.grade
                class_val = st.session_state.class_value
                num_val = st.session_state.num
                name_val = st.session_state.name
                mission_val = st.session_state.mission

                if not all([grade_val, class_val, num_val, name_val, mission_val, uploaded_file]):
                    st.error("모든 항목을 입력하고 파일을 첨부해주세요.")
                else:
                    submit_form(grade_val, class_val, num_val, name_val, mission_val, uploaded_file)
        
        st.markdown("---")
        
        # 순위 및 차트 표시 영역
        st.header("✨ 실시간 참여 현황")
        display_rankings_and_charts()


if __name__ == "__main__":
    # 세션 상태 초기화 (UnboundLocalError 방지)
    if 'grade' not in st.session_state: st.session_state.grade = ''
    if 'class_value' not in st.session_state: st.session_state.class_value = ''
    if 'num' not in st.session_state: st.session_state.num = ''
    if 'name' not in st.session_state: st.session_state.name = ''
    if 'mission' not in st.session_state: st.session_state.mission = ''
    
    main()
