import streamlit as st
from openai import OpenAI
import pandas as pd
import os

# --- 0. 상수 및 파일 경로 정의 ---
GLOSSARY_FILE = "glossary.csv"
STYLE_GUIDE_FILE = "style_guide.txt"

# --- 1. 설정 및 초기화 ---

# 페이지 제목 설정
st.set_page_config(page_title="팀 번역기", page_icon="🌐", layout="wide")
st.title("🌐 자유공산주의전선 번역기")

# OpenAI 클라이언트 초기화 (st.secrets 사용으로 보안 강화)
try:
    client = OpenAI(api_key=st.secrets["openai"]["api_key"])
except Exception:
    st.error("🚨 OpenAI API 키를 설정해주세요! `.streamlit/secrets.toml` 파일이 필요합니다.")
    st.stop()


# --- 2. 헬퍼 함수 (단어장 및 스타일 가이드) ---

# 단어장 로드
def load_glossary():
    if not os.path.exists(GLOSSARY_FILE):
        # 파일이 없으면 기본 헤더로 생성
        pd.DataFrame(columns=["English", "Korean"]).to_csv(GLOSSARY_FILE, index=False)
    return pd.read_csv(GLOSSARY_FILE)

# 단어장 저장
def save_glossary(df):
    df.to_csv(GLOSSARY_FILE, index=False)

# 스타일 가이드 로드
def load_style_guide():
    if not os.path.exists(STYLE_GUIDE_FILE):
        # 파일이 없으면 기본 내용으로 생성
        default_style = "번역 스타일: 공식적이고 전문적인 톤을 유지하며, 문장은 명확하고 간결하게 작성합니다. 모든 번역은 존댓말을 사용합니다."
        with open(STYLE_GUIDE_FILE, "w", encoding="utf-8") as f:
            f.write(default_style)
    with open(STYLE_GUIDE_FILE, "r", encoding="utf-8") as f:
        return f.read()

# 스타일 가이드 저장
def save_style_guide(style_text):
    with open(STYLE_GUIDE_FILE, "w", encoding="utf-8") as f:
        f.write(style_text)

# --- 3. 핵심 번역 함수 ---

def translate_with_openai(text: str, glossary: pd.DataFrame, style_guide: str) -> str | None:
    if not text.strip():
        return ""

    # 단어장을 프롬프트에 포함시킬 형태로 변환
    glossary_text = "\n".join([f"- {row['English']}: {row['Korean']}" for index, row in glossary.iterrows()])

    # 시스템 프롬프트를 동적으로 구성
    system_prompt = f"""
You are an expert translator. Your only job is to translate the given English text into natural Korean.
Your output must be ONLY the translated text itself, without any additional phrases, explanations, or greetings.

Follow these rules strictly:
1.  **Translation Style**: Adhere to the following style guide.
    --- STYLE GUIDE ---
    {style_guide}
    --- END STYLE GUIDE ---

2.  **Glossary**: You MUST use the translations provided in this glossary for the specified terms.
    --- GLOSSARY ---
    {glossary_text if glossary_text else "No specific terms provided."}
    --- END GLOSSARY ---
"""
    
    try:
        with st.spinner("AI가 번역 중입니다..."):
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.1,
            )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"번역 중 오류가 발생했습니다: {e}")
        return None

# --- 4. 스트림릿 UI 구성 ---

# 세션 상태 초기화
if 'glossary_df' not in st.session_state:
    st.session_state.glossary_df = load_glossary()
if 'style_guide' not in st.session_state:
    st.session_state.style_guide = load_style_guide()
if 'english_text' not in st.session_state:
    st.session_state.english_text = ""
if 'korean_translation' not in st.session_state:
    st.session_state.korean_translation = ""

# 사이드바: 단어장 및 스타일 가이드 관리
with st.sidebar:
    st.header("⚙️ 팀 공유 설정")

    with st.expander("✍️ 번역 스타일 가이드", expanded=True):
        edited_style = st.text_area("팀의 번역 스타일을 정의하세요:", value=st.session_state.style_guide, height=150, key="style_editor")
        if st.button("스타일 저장"):
            save_style_guide(edited_style)
            st.session_state.style_guide = edited_style
            st.success("스타일이 저장되었습니다!")

    with st.expander("📖 공유 단어장", expanded=True):
        edited_df = st.data_editor(st.session_state.glossary_df, num_rows="dynamic", use_container_width=True, key="glossary_editor")
        if st.button("단어장 저장"):
            # Ensure columns exist before dropping NA
            if 'English' in edited_df.columns and 'Korean' in edited_df.columns:
                edited_df.dropna(subset=['English', 'Korean'], how='all', inplace=True)
            else:
                # Handle case where table is empty or columns are missing
                edited_df = pd.DataFrame(columns=["English", "Korean"])
            save_glossary(edited_df)
            st.session_state.glossary_df = edited_df
            st.success("단어장이 저장되었습니다!")

# 메인 화면: 번역기
col1, col2 = st.columns(2)

with col1:
    st.subheader("📜 원문 (영어)")
    st.session_state.english_text = st.text_area("번역할 영어 문장을 입력하세요:", value=st.session_state.english_text, height=300, placeholder="Enter English text here...", label_visibility="collapsed")

with col2:
    st.subheader("📖 번역 결과 (한국어)")
    if st.button("한글로 번역하기", type="primary", use_container_width=True):
        if st.session_state.english_text:
            translation_result = translate_with_openai(st.session_state.english_text, st.session_state.glossary_df, st.session_state.style_guide)
            if translation_result:
                st.session_state.korean_translation = translation_result
        else:
            st.warning("번역할 내용을 입력해주세요.")
    
    st.markdown(f"<div style='height: 300px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; border-radius: 5px;'>{st.session_state.korean_translation}</div>", unsafe_allow_html=True)
