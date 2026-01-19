import streamlit as st
import google.generativeai as genai
from PIL import Image
import time
from datetime import datetime

# --- 配置页面 ---
st.set_page_config(
    page_title="AI 视频提示词生成助手",
    page_icon="🎬",
    layout="wide"
)

# --- API Key 配置 (Streamlit Secrets) ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except (FileNotFoundError, KeyError):
    st.error("🚨 未检测到 Google API Key。请在 Streamlit Cloud Secrets 中配置 `GOOGLE_API_KEY`。")
    st.stop()

# --- 状态初始化 ---
if "history" not in st.session_state:
    st.session_state["history"] = []

# --- Gemini 调用封装 ---
def call_gemini(current_api_key, system_instruction, user_content, media_files=None, chat_history=None):
    if not current_api_key: return "API Key缺失。"
    try:
        genai.configure(api_key=current_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_instruction)
        content_parts = [user_content]
        if media_files:
            for media in media_files:
                content_parts.append(media)
        
        if chat_history:
            chat = model.start_chat(history=chat_history)
            response = chat.send_message(content_parts)
            return response.text
        
        response = model.generate_content(content_parts)
        return response.text
    except Exception as e:
        return f"API Error: {str(e)}"

# --- 主页面 Tabs ---
tab1, tab2 = st.tabs(["🚀 立即生成", "📝 历史记录与优化"])

# ==========================================
# TAB 1: 生成工作台
# ==========================================
with tab1:
    # 已移除使用说明 Expander

    with st.form("generation_form"):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### 1. 基础信息")
            market = st.selectbox("投放市场 (必填)", ["美国 (US)", "英国 (UK)", "东南亚", "欧洲其他", "全球"], index=0)
            product_name = st.text_input("商品名称 (必填)")
            selling_points = st.text_area("商品卖点 (必填)", height=100)
            copywriting = st.text_area("相关文案 (选填)", height=68)
            prompt_count = st.slider("生成 Prompt 条数", 1, 5, 3)

        with col2:
            st.markdown("#### 2. 附件与工具")
            uploaded_image = st.file_uploader("上传商品图片 (必填★)", type=["jpg", "png", "jpeg"])
            uploaded_video = st.file_uploader("上传参考视频 (选填☆)", type=["mp4", "mov"])
            
            st.markdown("---")
            st.markdown("**选择细分工具：**")
            tool_type = st.radio(
                "工具类型",
                ("1、图生视频 (Image-to-Video)", "2、图生 Clip (Image-to-Clip)", "3、视频模仿 (Video Mimic)"),
                label_visibility="collapsed"
            )

        submit_btn = st.form_submit_button("✨ 点击立即生成", use_container_width=True)

    if submit_btn:
        if not product_name or not selling_points:
            st.error("⚠️ 请填写完整的【商品名称】和【商品卖点】！")
        elif not uploaded_image:
             st.error("⚠️ 请上传【商品图片】（必填项）！")
        else:
            with st.spinner("正在生成中..."):
                # 处理图片
                image_part = Image.open(uploaded_image)
                media_list = [image_part]
                
                # 预处理变量（您可以在下方的 prompt 字符串中直接使用 f-string 引用这些变量）
                # 可用变量：{market}, {product_name}, {selling_points}, {copywriting}, {prompt_count}
                
                system_instruction = ""
                user_prompt = ""

                # =========================================================
                # 👇👇👇 请在此处填入您准备好的提示词 👇👇👇
                # =========================================================

                if "图生视频" in tool_type:
                    # [标识 1] 图生视频 - 提示词配置
                    system_instruction = """
                    👉 【在此处粘贴您的 System Prompt / 角色设定】
                    """
                    user_prompt = f"""
                    👉 【在此处粘贴您的 User Prompt】
                    (提示：可以使用变量，例如：商品是 {product_name}，卖点是 {selling_points}，需要生成 {prompt_count} 条)
                    """
                
                elif "图生 Clip" in tool_type:
                    # [标识 2] 图生 Clip - 提示词配置
                    system_instruction = """
                    👉 【在此处粘贴您的 System Prompt / 角色设定】
                    """
                    user_prompt = f"""
                    👉 【在此处粘贴您的 User Prompt】
                    """
                
                elif "视频模仿" in tool_type:
                    # [标识 3] 视频模仿 - 提示词配置
                    # 提示：如果用户没传视频，uploaded_video 为 None
                    video_status = "已提供参考视频" if uploaded_video else "未提供参考视频，请自由发挥"
                    
                    system_instruction = """
                    👉 【在此处粘贴您的 System Prompt / 角色设定】
                    """
                    user_prompt = f"""
                    👉 【在此处粘贴您的 User Prompt】
                    (当前视频状态：{video_status})
                    """

                # =========================================================
                # 👆👆👆 提示词配置结束 👆👆👆
                # =========================================================

                # 调用 API
                result_text = call_gemini(api_key, system_instruction, user_prompt, media_list)

                # 保存历史
                initial_chat_history = [
                    {"role": "user", "parts": [f"[图片上下文] {user_prompt}"]},
                    {"role": "model", "parts": [result_text]}
                ]

                new_record = {
                    "id": str(int(time.time())),
                    "timestamp": datetime.now().strftime("%m-%d %H:%M"),
                    "tool": tool_type.split(' ')[0],
                    "product": product_name,
                    "inputs_summary": f"卖点：{selling_points[:30]}...",
                    "chat_history": initial_chat_history,
                    "system_instruction": system_instruction
                }
                st.session_state.history.insert(0, new_record) 
                
                st.success("✅ 生成完成！")
                st.markdown("### 结果预览：")
                st.write(result_text)

# ==========================================
# TAB 2: 历史记录与优化
# ==========================================
with tab2:
    st.subheader("📜 生成记录与对话式优化")
    
    if not st.session_state.history:
        st.info("暂无记录。")
    
    for record in st.session_state.history:
        with st.expander(f"[{record['timestamp']}] {record['tool']} | {record['product']}"):
            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.markdown("**原始需求摘要**")
                st.caption(record['inputs_summary'])
                st.divider()
                st.info("在右侧对话框可进行修改")
            
            with col_b:
                chat_container = st.container(height=500)
                for msg in record['chat_history']:
                    with chat_container.chat_message(msg['role']):
                        if msg['role'] == 'user' and "[图片上下文]" in msg['parts'][0]:
                             with st.expander("查看初始请求", expanded=False): st.write(msg['parts'][0])
                        else:
                            st.markdown(msg['parts'][0])

                if prompt := st.chat_input(f"修改指令...", key=f"chat_{record['id']}"):
                    with chat_container.chat_message("user"): st.markdown(prompt)
                    
                    with chat_container.chat_message("model"):
                        with st.spinner("修改中..."):
                            resp = call_gemini(api_key, record['system_instruction'], prompt, None, record['chat_history'])
                            st.markdown(resp)
                    
                    record['chat_history'].append({"role": "user", "parts": [prompt]})
                    record['chat_history'].append({"role": "model", "parts": [resp]})
                    st.rerun()