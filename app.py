import streamlit as st
import google.generativeai as genai
from PIL import Image
import time
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(
    page_title="提示词工坊",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- API Key 校验 ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except (FileNotFoundError, KeyError):
    st.error("🚨 请在 Streamlit Cloud Secrets 中配置 `GOOGLE_API_KEY`。")
    st.stop()

# --- 状态初始化 ---
# page_mode: 'home' (首页), 'form' (填写页), 'detail' (详情页)
if "page_mode" not in st.session_state:
    st.session_state.page_mode = "home"
if "selected_tool" not in st.session_state:
    st.session_state.selected_tool = None
if "history" not in st.session_state:
    st.session_state.history = []
if "current_task_id" not in st.session_state:
    st.session_state.current_task_id = None

# --- 工具函数：Gemini 调用 ---
def call_gemini(current_api_key, system_instruction, user_content, media_files=None, chat_history=None):
    if not current_api_key: return "API Key缺失。"
    try:
        genai.configure(api_key=current_api_key)
        model = genai.GenerativeModel('gemini-2.5-pro', system_instruction=system_instruction)
        
        content_parts = [user_content]
        if media_files:
            for media in media_files:
                # 简单的图片处理，如果是视频文件流，实际生产需走 File API，这里做兼容处理
                content_parts.append(media)
        
        if chat_history:
            chat = model.start_chat(history=chat_history)
            response = chat.send_message(content_parts)
            return response.text
        
        response = model.generate_content(content_parts)
        return response.text
    except Exception as e:
        return f"API Error: {str(e)}"

# --- 工具函数：生成任务名称 ---
def generate_task_name(tool_name):
    # 映射工具名到前缀
    prefix_map = {
        "图生视频": "图生视频",
        "图生Clip": "图生Clip",
        "视频模仿": "视频模仿"
    }
    prefix = prefix_map.get(tool_name, "任务")
    
    # 获取日期 (MMDD)
    date_str = datetime.now().strftime("%m%d")
    
    # 计算当日序号
    # 筛选出同名且同日期的任务
    base_name = f"{prefix}{date_str}"
    count = 0
    for task in st.session_state.history:
        if task['name'].startswith(base_name):
            count += 1
    
    # 序号两位数
    seq = f"{count + 1:02d}"
    return f"{base_name}{seq}"

# ==========================================
# 侧边栏布局
# ==========================================
with st.sidebar:
    st.title("工作台")
    
    # 1. 新建任务按钮 (上半部分)
    if st.button("+新建任务", use_container_width=True, type="primary"):
        st.session_state.page_mode = "home"
        st.session_state.current_task_id = None
        st.rerun()

    st.divider()
    
    # 2. 历史记录列表 (下半部分)
    st.subheader("历史任务")
    
    if not st.session_state.history:
        st.caption("暂无历史记录")
    
    for task in st.session_state.history:
        # 点击历史任务，进入详情页
        if st.button(f"{task['name']}", key=f"btn_{task['id']}", use_container_width=True):
            st.session_state.current_task_id = task['id']
            st.session_state.page_mode = "detail"
            st.rerun()

# ==========================================
# 主页面逻辑路由
# ==========================================

# --- 场景 1: 首页 (工具选择) ---
if st.session_state.page_mode == "home":
    st.header("请选择工具")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🖼️图生视频")
        st.caption("Image-to-Video")
        st.info("适合：生成12S的完整视频")
        if st.button("开始使用", key="btn_tool_1"):
            st.session_state.selected_tool = "图生视频"
            st.session_state.page_mode = "form"
            st.rerun()
            
    with col2:
        st.subheader("⚡️图生Clip")
        st.caption("Image-to-Clip")
        st.info("适合：生成4S的视频片段")
        if st.button("开始使用", key="btn_tool_2"):
            st.session_state.selected_tool = "图生Clip"
            st.session_state.page_mode = "form"
            st.rerun()
            
    with col3:
        st.subheader("🎥视频模仿")
        st.caption("Video Mimic")
        st.info("适合：参考已有视频脚本，进行复制")
        if st.button("开始使用", key="btn_tool_3"):
            st.session_state.selected_tool = "视频模仿"
            st.session_state.page_mode = "form"
            st.rerun()

# --- 场景 2: 信息提交表单 ---
elif st.session_state.page_mode == "form":
    tool = st.session_state.selected_tool
    st.button("← 返回首页", on_click=lambda: st.session_state.update(page_mode="home"))
    st.header(f"🛠️ {tool}")
    st.divider()
    
    with st.form("task_form"):
        # 公共变量初始化
        media_list = []
        user_prompt = ""
        system_instruction = ""
        
        # === 1. 图生视频 表单 ===
        if tool == "图生视频":
            col1, col2 = st.columns(2)
            with col1:
                market = st.selectbox("投放市场 (必填)", ["美国", "英国", "东南亚", "全球"], index=0)
                product_name = st.text_input("商品名称 (必填)")
                selling_points = st.text_area("商品卖点 (必填)")
                prompt_count = st.slider("需要的提示词条数", 1, 5, 3)
            with col2:
                copywriting = st.text_area("文案 (选填)")
                uploaded_img = st.file_uploader("商品图片 (选填，建议上传)", type=["jpg", "png", "jpeg"])
                uploaded_video = st.file_uploader("参考视频 (选填)", type=["mp4", "mov"])

            # 提示词构建逻辑
            if st.form_submit_button("立即生成"):
                if not market or not product_name or not selling_points:
                    st.error("请填写必填项！")
                    st.stop()
                
                if uploaded_img:
                    media_list.append(Image.open(uploaded_img))
                
                # [标识] 图生视频 Prompt
                system_instruction = """
                👉 【此处填入图生视频 System Prompt】
                """
                user_prompt = f"""
                👉 【此处填入图生视频 User Prompt】
                信息：市场-{market}, 商品-{product_name}, 卖点-{selling_points}, 文案-{copywriting}, 数量-{prompt_count}
                """

        # === 2. 图生Clip 表单 ===
        elif tool == "图生Clip":
            col1, col2 = st.columns(2)
            with col1:
                market = st.selectbox("投放市场 (必填)", ["美国", "英国", "东南亚", "全球"])
                product_name = st.text_input("商品名称 (必填)")
                selling_points = st.text_area("商品卖点 (必填)")
            with col2:
                prompt_count = st.slider("需要的提示词条数", 1, 5, 3)
                scene_type = st.selectbox("生成场景 (必填)", ["钩子 (Hook)", "产品细节展示", "产品整体展示", "CTA (呼吁行动)"])
                # Clip 通常必须有图，虽未强制但逻辑上需要
                uploaded_img = st.file_uploader("商品图片 (建议上传)", type=["jpg", "png", "jpeg"])

            if st.form_submit_button("立即生成"):
                if not market or not product_name or not selling_points:
                    st.error("请填写必填项！")
                    st.stop()
                
                if uploaded_img:
                    media_list.append(Image.open(uploaded_img))

                # [标识] 图生Clip Prompt
                system_instruction = """
                👉 【此处填入图生Clip System Prompt】
                """
                user_prompt = f"""
                👉 【此处填入图生Clip User Prompt】
                信息：市场-{market}, 商品-{product_name}, 卖点-{selling_points}, 场景-{scene_type}, 数量-{prompt_count}
                """

        # === 3. 视频模仿 表单 ===
        elif tool == "视频模仿":
            col1, col2 = st.columns(2)
            with col1:
                market = st.selectbox("投放市场 (必填)", ["美国", "英国", "东南亚", "全球"])
            with col2:
                uploaded_video = st.file_uploader("参考视频 (必填)", type=["mp4", "mov"])
            
            if st.form_submit_button("立即生成"):
                if not uploaded_video:
                    st.error("视频模仿必须上传参考视频！")
                    st.stop()
                
                # 注意：Streamlit 中视频文件处理较复杂，此处仅作逻辑占位，实际 Prompt 中仅能描述“已提供视频”
                # 如果是 Gemini 1.5 Pro，可以尝试通过 File API 上传，此处简化处理
                
                # [标识] 视频模仿 Prompt
                system_instruction = """
                👉 【此处填入视频模仿 System Prompt】
                """
                user_prompt = f"""
                👉 【此处填入视频模仿 User Prompt】
                信息：市场-{market}, 参考视频已上传(请根据文件名或元数据进行风格分析)。
                """

        # === 执行生成 (通用逻辑) ===
        # 注意：这里处于 form 提交后的缩进块内
        if user_prompt: # 如果 user_prompt 被赋值了，说明校验通过
            with st.spinner(f"正在使用 {tool} 生成中..."):
                result_text = call_gemini(api_key, system_instruction, user_prompt, media_list)
                
                # 生成任务 ID 和 名称
                task_id = str(int(time.time()))
                task_name = generate_task_name(tool)
                
                # 保存到历史
                new_task = {
                    "id": task_id,
                    "name": task_name,
                    "tool": tool,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "system_instruction": system_instruction,
                    "chat_history": [
                        {"role": "user", "parts": [f"【任务配置】\n{user_prompt}"]},
                        {"role": "model", "parts": [result_text]}
                    ]
                }
                
                st.session_state.history.insert(0, new_task)
                st.session_state.current_task_id = task_id
                st.session_state.page_mode = "detail" # 跳转详情页
                st.rerun()

# --- 场景 3: 历史任务详情与对话 ---
elif st.session_state.page_mode == "detail":
    # 获取当前任务对象
    current_task = next((t for t in st.session_state.history if t['id'] == st.session_state.current_task_id), None)
    
    if not current_task:
        st.error("任务不存在")
        st.button("返回首页", on_click=lambda: st.session_state.update(page_mode="home"))
    else:
        # 顶部导航栏
        c1, c2 = st.columns([6, 1])
        with c1:
            st.title(f"📝 {current_task['name']}")
            st.caption(f"创建时间: {current_task['date']} | 工具: {current_task['tool']}")
        with c2:
            if st.button("关闭", type="secondary"):
                st.session_state.page_mode = "home"
                st.rerun()
        
        st.divider()

        # 聊天区域
        chat_container = st.container(height=600)
        
        # 显示历史
        for msg in current_task['chat_history']:
            with chat_container.chat_message(msg['role']):
                # 隐藏初始的大段 Prompt，只显示结果或简略信息
                if msg['role'] == 'user' and "【任务配置】" in msg['parts'][0]:
                    with st.expander("查看原始任务配置"):
                        st.text(msg['parts'][0])
                else:
                    st.markdown(msg['parts'][0])
        
        # 输入框
        if prompt := st.chat_input("对生成结果不满意？输入修改建议..."):
            # 1. 显示用户输入
            with chat_container.chat_message("user"):
                st.markdown(prompt)
            
            # 2. 调用 API 修改
            with chat_container.chat_message("model"):
                with st.spinner("AI 正在修改..."):
                    # 获取当前任务的上下文
                    context_history = current_task['chat_history']
                    response = call_gemini(
                        api_key, 
                        current_task['system_instruction'], 
                        prompt, 
                        None, # 修改阶段不重新传附件
                        context_history
                    )
                    st.markdown(response)
            
            # 3. 更新历史数据
            current_task['chat_history'].append({"role": "user", "parts": [prompt]})
            current_task['chat_history'].append({"role": "model", "parts": [response]})
            st.rerun()
