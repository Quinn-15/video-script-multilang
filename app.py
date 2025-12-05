import streamlit as st
import pandas as pd
from googletrans import Translator

st.set_page_config(page_title="多语言视频脚本生成器", layout="wide")

# ---------- 全局配置 ----------
LANGS = ["zh", "en", "id"]
LANG_LABEL = {"zh": "中文", "en": "English", "id": "Bahasa"}
LANG_FULL = {"zh": "zh-cn", "en": "en", "id": "id"}

translator = Translator()


# ---------- 场景结构 ----------
def new_scene(scene_id: int) -> dict:
    return {
        "id": scene_id,
        "image_name": "",
        "image_data": None,  # bytes
        "visual": {lang: "" for lang in LANGS},
        "outline": {lang: "" for lang in LANGS},
        "dialogue": {lang: "" for lang in LANGS},
    }


# ---------- 初始化「多拍摄计划」 ----------
if "projects" not in st.session_state:
    # projects: {project_name: {"scenes": [...], "next_scene_id": int}}
    st.session_state.projects = {
        "默认拍摄计划": {
            "scenes": [],
            "next_scene_id": 1,
        }
    }

if "current_project" not in st.session_state:
    st.session_state.current_project = "默认拍摄计划"

projects = st.session_state.projects
project_names = list(projects.keys())

# ---------- 顶部：项目选择 + 全局设置 ----------
st.title("Multilingual Video Script Generator")
st.markdown("**多语言视频脚本生成器（中文 / English / Bahasa）**")

header = st.container()
with header:
    col_proj, col_lang, col_info, col_add_scene, col_deploy = st.columns(
        [2.5, 2, 4, 2, 1.5]
    )

    # 当前拍摄计划选择
    with col_proj:
        st.markdown("**当前拍摄计划 Project**")
        selected_project = st.selectbox(
            "",
            options=project_names,
            index=project_names.index(st.session_state.current_project),
            key="project_select",
        )

        if selected_project != st.session_state.current_project:
            st.session_state.current_project = selected_project
            st.rerun()

        # 新建拍摄计划
        new_proj_name = st.text_input(
            "新拍摄计划名称（回车或点击下方按钮）",
            value="",
            key="new_project_name",
        )
        if st.button("➕ 创建新拍摄计划"):
            name = new_proj_name.strip()
            if name and name not in projects:
                projects[name] = {"scenes": [], "next_scene_id": 1}
                st.session_state.projects = projects
                st.session_state.current_project = name
                st.rerun()

    # 当前拍摄计划的数据引用
    current_project_name = st.session_state.current_project
    project = projects[current_project_name]

    # 给当前项目生成一个前缀，用于区分不同项目的控件 key
    proj_index = project_names.index(current_project_name)
    proj_prefix = f"p{proj_index}"

    # 默认原文语言
    with col_lang:
        base_lang = st.selectbox(
            "默认原文语言 Default Source Language",
            options=LANGS,
            format_func=lambda x: LANG_LABEL[x],
            key=f"{proj_prefix}_base_lang",
        )

    # 翻译规则说明
    with col_info:
        st.info(
            "翻译逻辑（Translation Logic）：\n"
            "1️⃣ 优先使用你选择的默认原文语言；\n"
            "2️⃣ 如果该语言为空，则依次使用：中文 → English → Bahasa；\n"
            "3️⃣ 仅填充空白语言，不会覆盖你手动输入的内容。"
        )

    # 为当前项目新增场景
    with col_add_scene:
        if st.button("➕ 新增一个空场景", key=f"{proj_prefix}_add_scene"):
            sid = project["next_scene_id"]
            project["next_scene_id"] += 1
            project["scenes"].append(new_scene(sid))
            st.session_state.projects = projects
            st.rerun()

    # Deploy 占位按钮
    with col_deploy:
        st.button("🚀 Deploy", help="后续可以接入云端部署平台（当前为占位按钮）")

st.markdown("---")
st.markdown(f"### 🎨 Storyboard · 当前拍摄计划：{current_project_name}")

scenes = project["scenes"]


# ---------- 翻译相关 ----------
def translate_text(text: str, src_lang: str, tgt_lang: str) -> str:
    if not text or not text.strip():
        return ""
    try:
        result = translator.translate(
            text, src=LANG_FULL[src_lang], dest=LANG_FULL[tgt_lang]
        )
        return result.text
    except Exception as e:
        st.warning(f"翻译失败（{src_lang} → {tgt_lang}）：{e}")
        return text  # 出错就先返回原文


def translate_block(scene: dict, field: str, base_lang: str, proj_prefix: str):
    """
    field: 'outline' / 'visual' / 'dialogue'
    直接操作 scene[field][lang]，并同步回 session_state。
    """
    texts = {lang: scene[field][lang].strip() for lang in LANGS}

    # 原文语言优先顺序：base_lang -> zh -> en -> id
    order = [base_lang, "zh", "en", "id"]
    src_lang = None
    for lang in order:
        if texts.get(lang):
            src_lang = lang
            break
    if src_lang is None:
        return

    src_text = texts[src_lang]

    # 翻译到其它空语言，不覆盖已有内容
    for lang in LANGS:
        if lang == src_lang:
            continue
        if texts.get(lang):  # 已有内容，不覆盖
            continue
        translated = translate_text(src_text, src_lang, lang)
        scene[field][lang] = translated
        key = f"{proj_prefix}_{field}_{scene['id']}_{lang}"
        st.session_state[key] = translated

    # 再把原文写回一次，确保不会被清空
    key_src = f"{proj_prefix}_{field}_{scene['id']}_{src_lang}"
    st.session_state[key_src] = src_text
    scene[field][src_lang] = src_text


def translate_scene(scene: dict, base_lang: str, proj_prefix: str):
    for field in ["visual", "outline", "dialogue"]:
        translate_block(scene, field, base_lang, proj_prefix)
    st.session_state.projects = projects
    st.rerun()


# ---------- 文本输入绑定 ----------
def bind_text_field(scene: dict, field: str, lang: str, proj_prefix: str, height: int = 100):
    """
    field: 'outline' / 'visual' / 'dialogue'
    lang: 'zh' / 'en' / 'id'
    把 textarea 内容双向绑定到 scene 和 session_state
    """
    key = f"{proj_prefix}_{field}_{scene['id']}_{lang}"
    # 初始化时从 scene 填充到 session_state
    if key not in st.session_state:
        st.session_state[key] = scene[field][lang]

    st.text_area("", key=key, height=height)
    # 再把 session_state 内最新值写回 scene
    scene[field][lang] = st.session_state[key]


# ---------- 场景列表 ----------
for idx, scene in enumerate(scenes):
    sid = scene["id"]
    st.markdown("---")

    # 预览文本：主语言的 Outline 前 20 字
    def get_outline_preview():
        text = scene["outline"].get(base_lang, "") or \
               scene["outline"].get("zh", "") or \
               scene["outline"].get("en", "") or \
               scene["outline"].get("id", "")
        text = text.strip()
        if not text:
            return "（暂无大纲内容）"
        return (text[:20] + "…") if len(text) > 20 else text

    # 顶部标题 + 操作区
    title_col, btn_col_up, btn_col_down, btn_col_del = st.columns([5, 1, 1, 1])
    with title_col:
        st.markdown(f"#### Scene {idx + 1}")
        st.caption(f"大纲预览 Preview：{get_outline_preview()}")

    with btn_col_up:
        if st.button("⬆", key=f"{proj_prefix}_up_{sid}") and idx > 0:
            scenes[idx - 1], scenes[idx] = scenes[idx], scenes[idx - 1]
            st.session_state.projects = projects
            st.rerun()

    with btn_col_down:
        if st.button("⬇", key=f"{proj_prefix}_down_{sid}") and idx < len(scenes) - 1:
            scenes[idx + 1], scenes[idx] = scenes[idx], scenes[idx + 1]
            st.session_state.projects = projects
            st.rerun()

    with btn_col_del:
        if st.button("🗑", key=f"{proj_prefix}_del_{sid}"):
            scenes.pop(idx)
            st.session_state.projects = projects
            st.rerun()

    # Scene 主按钮：一键翻译
    if st.button(
        "✨ 一键翻译本场景",
        key=f"{proj_prefix}_tr_{sid}",
        use_container_width=True,
    ):
        translate_scene(scene, base_lang, proj_prefix)

    # 折叠详情
    with st.expander("展开 / 收起 Scene 详情 Show / Hide Scene Details", expanded=(idx == 0)):
        # 参考图（全宽）
        st.markdown("##### 参考图上传 Reference Image")
        img_key = f"{proj_prefix}_img_{sid}"
        img_file = st.file_uploader(
            "上传参考图片（可选）Upload reference image (PNG / JPG / JPEG)",
            type=["png", "jpg", "jpeg"],
            key=img_key,
        )
        if img_file is not None:
            scene["image_name"] = img_file.name
            scene["image_data"] = img_file.getvalue()
        if scene["image_data"]:
            st.image(
                scene["image_data"],
                use_column_width=True,
                caption=scene["image_name"] or "参考图片 Reference Image",
            )

        # 三栏：Outline / Visual / Dialogue（每栏内部用 Tab 切换语言）
        col_outline, col_visual, col_dialogue = st.columns(3)

        # 公用 Tab 组件（每栏用一次）
        def language_tabs_in_column(field_name: str, title: str, desc: str, col):
            with col:
                st.markdown(f"**{title}**")
                st.caption(desc)
                tab_zh, tab_en, tab_id = st.tabs(["中文", "English", "Bahasa"])
                with tab_zh:
                    st.markdown("**中文 Chinese**")
                    bind_text_field(scene, field_name, "zh", proj_prefix, height=120)
                with tab_en:
                    st.markdown("**English**")
                    bind_text_field(scene, field_name, "en", proj_prefix, height=120)
                with tab_id:
                    st.markdown("**Bahasa Indonesia**")
                    bind_text_field(scene, field_name, "id", proj_prefix, height=120)

        # Outline 列
        language_tabs_in_column(
            "outline",
            "Outline 剧情大纲",
            "描述该 Scene 的剧情走向与核心信息。",
            col_outline,
        )

        # Visual 列
        language_tabs_in_column(
            "visual",
            "Visual 画面描述",
            "描述画面构图、角色动作、场景氛围、镜头语言等。",
            col_visual,
        )

        # Dialogue 列
        language_tabs_in_column(
            "dialogue",
            "Dialogue 口播对白",
            "填写人物对白或旁白稿。",
            col_dialogue,
        )

# 写回当前项目数据
project["scenes"] = scenes
projects[current_project_name] = project
st.session_state.projects = projects

# ---------- 底部导出 ----------
st.markdown("---")
st.markdown("### ✅ 完成并下载 CSV（当前拍摄计划）")

rows = []
for order, scene in enumerate(scenes, start=1):
    def get_text(field, lang):
        return scene[field].get(lang, "")

    rows.append(
        {
            "Project": current_project_name,
            "Scene No.": order,
            "Image": scene["image_name"],

            "Outline (Chinese)": get_text("outline", "zh"),
            "Outline (English)": get_text("outline", "en"),
            "Outline (Indonesian)": get_text("outline", "id"),

            "Visual (Chinese)": get_text("visual", "zh"),
            "Visual (English)": get_text("visual", "en"),
            "Visual (Indonesian)": get_text("visual", "id"),

            "Dialogue (Chinese)": get_text("dialogue", "zh"),
            "Dialogue (English)": get_text("dialogue", "en"),
            "Dialogue (Indonesian)": get_text("dialogue", "id"),
        }
    )

df = pd.DataFrame(rows)
csv = df.to_csv(index=False).encode("utf-8-sig")

left, right = st.columns([4, 1])
with right:
    st.download_button(
        "✅ 完成并下载当前计划 CSV",
        data=csv,
        file_name=f"video_script_{current_project_name}.csv",
        mime="text/csv",
        use_container_width=True,
    )
