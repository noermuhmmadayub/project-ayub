from __future__ import annotations

from datetime import datetime
import hashlib
import hmac
import io
import logging
import re
import shutil
from pathlib import Path
from typing import Dict, List

import altair as alt
import pandas as pd
import streamlit as st
from fpdf import FPDF

from src.config.settings import Settings, get_settings
from src.database.connection import DatabaseConnection
from src.database.repository import ChatRepository
from src.observability import setup_app_logging
from src.services.chatbot import GeminiChatbotService
from src.services.rag import SimpleRAG

MENU_CHAT = "Chat"
MENU_DASHBOARD = "Dashboard Mahasiswa"
MENU_ADMIN = "Admin"


def list_knowledge_filenames() -> List[str]:
    root = Path("data/knowledge")
    if not root.exists():
        return []
    names: List[str] = []
    for file_path in sorted(root.rglob("*")):
        if file_path.is_file() and file_path.suffix.lower() in {".md", ".txt"}:
            names.append(file_path.name)
    return sorted(names)


def apply_ui_theme(theme_mode: str) -> None:
    is_light = theme_mode == "Light"
    bg = "#eef3fb" if is_light else "radial-gradient(circle at top, #11203d 0%, #0b1324 48%, #080d18 100%)"
    text = "#172640" if is_light else "#e6edf8"
    banner_border = "#7ea4de" if is_light else "#274978"
    banner_bg = "rgba(208, 226, 252, 0.78)" if is_light else "rgba(30, 71, 130, 0.28)"
    chat_border = "rgba(95, 127, 178, 0.34)" if is_light else "rgba(100, 140, 215, 0.25)"
    chat_bg = "rgba(255, 255, 255, 0.96)" if is_light else "rgba(14, 25, 45, 0.62)"
    input_bg = "rgba(246, 250, 255, 0.98)" if is_light else "rgba(8, 13, 24, 0.95)"
    rag_bg = "rgba(240, 246, 255, 0.96)" if is_light else "rgba(20, 39, 69, 0.55)"
    accent = "#1f4d92" if is_light else "#b7d5ff"
    css = """
    <style>
        .stApp {{
            background: {bg};
        }}
        .main .block-container {{
            max-width: 980px;
            padding-top: 1.3rem;
        }}
        [data-testid="stSidebar"] {{
            border-right: 1px solid {chat_border};
            background: {chat_bg};
        }}
        [data-testid="stSidebar"] .block-container {{
            padding-top: 1rem;
        }}
        .sidebar-brand {{
            border: 1px solid {chat_border};
            background: {chat_bg};
            border-radius: 14px;
            padding: 12px 12px 10px 12px;
            margin-bottom: 10px;
        }}
        .sidebar-brand-title {{
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 3px;
        }}
        .sidebar-brand-subtitle {{
            opacity: 0.8;
            font-size: 0.82rem;
        }}
        .sidebar-profile {{
            border: 1px solid {chat_border};
            background: {rag_bg};
            border-radius: 12px;
            padding: 10px;
            margin: 6px 0 10px 0;
        }}
        .sidebar-section-title {{
            font-size: 1.02rem;
            font-weight: 700;
            margin: 8px 0 2px 0;
        }}
        .sidebar-caption {{
            font-size: 0.8rem;
            opacity: 0.8;
            margin-bottom: 6px;
        }}
        h1, h2, h3, p, label, span, div {{
            color: {text};
        }}
        .hero-title {{
            margin: 0;
            font-size: 1.8rem;
            line-height: 1.2;
            font-weight: 700;
        }}
        .hero-subtitle {{
            margin-top: 0.35rem;
            opacity: 0.92;
            font-size: 0.97rem;
        }}
        .content-shell {{
            border: 1px solid {chat_border};
            background: {chat_bg};
            border-radius: 14px;
            padding: 12px 14px;
            margin-bottom: 12px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0,1fr));
            gap: 10px;
            margin: 10px 0 14px 0;
        }}
        .stat-card {{
            border: 1px solid {chat_border};
            background: {chat_bg};
            border-radius: 12px;
            padding: 10px 12px;
        }}
        .stat-label {{
            font-size: 0.78rem;
            opacity: 0.85;
        }}
        .stat-value {{
            font-size: 1.05rem;
            font-weight: 700;
            margin-top: 2px;
        }}
        .edu-banner {{
            padding: 14px 16px;
            border-radius: 14px;
            border: 1px solid {banner_border};
            background: {banner_bg};
            margin-bottom: 14px;
        }}
        .edu-banner strong {{
            color: {accent};
        }}
        .stChatMessage {{
            border-radius: 14px;
            border: 1px solid {chat_border};
            background: {chat_bg};
        }}
        [data-testid="stChatMessageContent"] p {{
            line-height: 1.65;
            font-size: 0.98rem;
        }}
        .stButton > button {{
            border-radius: 10px;
            border: 1px solid {chat_border};
        }}
        .stDownloadButton > button {{
            border-radius: 10px;
            border: 1px solid {chat_border};
        }}
        .stChatInputContainer {{
            border-top: 1px solid {chat_border};
            background: {input_bg};
        }}
        .rag-box {{
            margin-top: 0.8rem;
            padding: 10px 12px;
            border-radius: 10px;
            border: 1px dashed #456b9d;
            background: {rag_bg};
            font-size: 0.9rem;
        }}
        .flashcard {{
            border: 1px solid {chat_border};
            border-radius: 12px;
            padding: 10px 12px;
            margin-bottom: 8px;
            background: {chat_bg};
        }}
        .auth-hero {{
            border: 1px solid {chat_border};
            border-radius: 14px;
            padding: 20px;
            background: {chat_bg};
            margin-bottom: 14px;
        }}
        .auth-hero-title {{
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 8px;
        }}
        .auth-hero-subtitle {{
            font-size: 0.95rem;
            opacity: 0.9;
            line-height: 1.6;
        }}
        .auth-feature-list {{
            margin-top: 10px;
            padding-left: 20px;
        }}
        .auth-feature-list li {{
            margin-bottom: 6px;
        }}
    </style>
    """.format(
        bg=bg,
        text=text,
        banner_border=banner_border,
        banner_bg=banner_bg,
        accent=accent,
        chat_border=chat_border,
        chat_bg=chat_bg,
        input_bg=input_bg,
        rag_bg=rag_bg,
    )
    st.markdown(css, unsafe_allow_html=True)


def bootstrap_dependencies(settings: Settings) -> tuple[ChatRepository, GeminiChatbotService]:
    database = DatabaseConnection(settings.db_path)
    schema_path = Path("src/database/schema.sql")
    database.initialize_schema(str(schema_path))

    repository = ChatRepository(database)
    rag = SimpleRAG(
        knowledge_dir="data/knowledge",
        api_key=settings.gemini_api_key,
        embedding_model_name=settings.embedding_model_name,
    )
    chatbot = GeminiChatbotService(settings=settings, rag=rag)
    return repository, chatbot


def initialize_state() -> None:
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("user_id", None)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("active_session_id", None)
    st.session_state.setdefault("search_page", 0)
    st.session_state.setdefault("search_term_prev", "")
    st.session_state.setdefault("answer_mode", "Penjelasan Detail")
    st.session_state.setdefault("pending_prompt", "")
    st.session_state.setdefault("theme_mode", "Dark")
    st.session_state.setdefault("latest_assistant_answer", "")
    st.session_state.setdefault("learning_artifact_title", "")
    st.session_state.setdefault("learning_artifact_content", "")


def _make_auth_signature(payload: str, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()


def _build_auth_token(user_id: int, username: str, secret: str) -> str:
    payload = f"{user_id}:{username}"
    signature = _make_auth_signature(payload, secret)
    return f"{payload}:{signature}"


def _parse_auth_token(token: str, secret: str) -> tuple[int, str] | None:
    parts = token.split(":", maxsplit=2)
    if len(parts) != 3:
        return None
    raw_user_id, username, signature = parts
    if not raw_user_id.isdigit() or not username:
        return None
    payload = f"{raw_user_id}:{username}"
    expected = _make_auth_signature(payload, secret)
    if not hmac.compare_digest(signature, expected):
        return None
    return int(raw_user_id), username


def restore_auth_from_query(settings: Settings, repository: ChatRepository) -> None:
    if st.session_state.get("authenticated") and st.session_state.get("user_id"):
        return
    token = st.query_params.get("auth")
    if not token:
        return

    parsed = _parse_auth_token(str(token), settings.auth_secret_key)
    if not parsed:
        st.query_params.pop("auth", None)
        return

    user_id, username = parsed
    user = repository.get_user_by_id(user_id)
    if not user or str(user["username"]) != username:
        st.query_params.pop("auth", None)
        return

    st.session_state["authenticated"] = True
    st.session_state["user_id"] = user_id
    st.session_state["username"] = username
    if st.session_state.get("active_session_id") is None:
        st.session_state["active_session_id"] = repository.get_latest_session_id(user_id)


def load_chat_history(repository: ChatRepository, session_id: int) -> List[Dict[str, str]]:
    messages = repository.list_messages(session_id)
    return [{"id": msg.id, "role": msg.role, "content": msg.content} for msg in messages]


def export_chat_markdown(title: str, messages: List[Dict[str, str]]) -> str:
    lines = [f"# {title}", ""]
    for item in messages:
        speaker = "Pengguna" if item["role"] == "user" else "Asisten"
        lines.append(f"## {speaker}")
        lines.append(item["content"])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def export_chat_text(messages: List[Dict[str, str]]) -> str:
    lines: List[str] = []
    for item in messages:
        speaker = "USER" if item["role"] == "user" else "ASSISTANT"
        lines.append(f"{speaker}: {item['content']}")
    return "\n\n".join(lines).strip() + "\n"


def export_chat_pdf(title: str, username: str, messages: List[Dict[str, str]]) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)

    safe_title = title.encode("latin-1", "replace").decode("latin-1")
    safe_user = username.encode("latin-1", "replace").decode("latin-1")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, txt=safe_title, ln=True)
    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 8, txt=f"User: {safe_user}", ln=True)
    pdf.cell(0, 8, txt=f"Generated at: {generated_at}", ln=True)
    pdf.ln(2)

    for item in messages:
        role = "Pengguna" if item["role"] == "user" else "Asisten"
        safe_role = role.encode("latin-1", "replace").decode("latin-1")
        safe_content = item["content"].encode("latin-1", "replace").decode("latin-1")
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 8, txt=f"{safe_role}:", ln=True)
        pdf.set_font("Helvetica", size=10)
        pdf.multi_cell(0, 6, txt=safe_content)
        pdf.ln(2)

    raw_pdf = pdf.output(dest="S")
    if isinstance(raw_pdf, (bytes, bytearray)):
        return bytes(raw_pdf)
    return str(raw_pdf).encode("latin-1", "replace")


def render_auth_controls(repository: ChatRepository) -> None:
    st.sidebar.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-title">🎓 Academic Assistant</div>
            <div class="sidebar-brand-subtitle">Asisten Pembelajaran Interaktif</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.markdown('<div class="sidebar-section-title">Akun Siswa</div>', unsafe_allow_html=True)
    if st.session_state["authenticated"]:
        st.sidebar.markdown(
            f"""
            <div class="sidebar-profile">
                <strong>👤 {st.session_state['username']}</strong><br>
                <span style="opacity:0.8;font-size:0.82rem;">Status: Login aktif</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        action_col1, action_col2 = st.sidebar.columns(2)
        if action_col1.button("🔄 Refresh", use_container_width=True):
            st.rerun()
        if action_col2.button("↩ Logout", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state["user_id"] = None
            st.session_state["username"] = ""
            st.session_state["active_session_id"] = None
            st.query_params.pop("auth", None)
            st.rerun()
        return

    tab_login, tab_register = st.sidebar.tabs(["Login", "Register"])
    with tab_login:
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Masuk", key="login_button", use_container_width=True):
            user_id = repository.authenticate_user(username, password)
            if user_id is None:
                st.sidebar.error("Username/password tidak valid.")
            else:
                st.session_state["authenticated"] = True
                st.session_state["user_id"] = user_id
                st.session_state["username"] = username.strip()
                st.session_state["active_session_id"] = repository.get_latest_session_id(user_id)
                token = _build_auth_token(user_id, username.strip(), get_settings().auth_secret_key)
                st.query_params["auth"] = token
                logging.getLogger(__name__).info("login ok user_id=%s username=%s", user_id, username.strip())
                st.rerun()

    with tab_register:
        new_username = st.text_input("Username baru", key="register_username")
        new_password = st.text_input("Password baru", type="password", key="register_password")
        if st.button("Daftar", key="register_button", use_container_width=True):
            user_id = repository.register_user(new_username, new_password)
            if user_id is None:
                st.sidebar.error("Gagal daftar. Username mungkin sudah ada atau password terlalu pendek.")
            else:
                st.sidebar.success("Registrasi berhasil. Silakan login.")


def render_logged_out_view() -> None:
    left_col, right_col = st.columns([1.4, 1], gap="large")
    with left_col:
        st.markdown(
            """
            <div class="auth-hero">
                <div class="auth-hero-title">Selamat datang di Academic Assistant</div>
                <div class="auth-hero-subtitle">
                    Platform chatbot pendidikan untuk membantu diskusi materi, latihan soal,
                    dan rangkuman pembelajaran secara real-time.
                </div>
                <ul class="auth-feature-list">
                    <li>Multi session untuk tiap topik belajar</li>
                    <li>Riwayat pembelajaran tersimpan otomatis</li>
                    <li>Mode jawaban: ringkas, detail, contoh, dan kuis</li>
                    <li>Dukungan <strong>Retrieval-Augmented Generation (RAG)</strong>:
                        AI mengambil referensi dari sumber belajar terlebih dahulu,
                        lalu menyusun jawaban yang lebih relevan dan akurat.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right_col:
        st.info("Silakan login atau register dari sidebar untuk mulai menggunakan fitur chatbot.")
        st.caption(
            "Tips: gunakan akun testing `tester_edu` jika ingin uji cepat tanpa registrasi ulang."
        )


def render_student_sidebar_extras(
    repository: ChatRepository,
    chatbot: GeminiChatbotService,
    user_id: int,
    active_session_id: int,
) -> None:
    st.sidebar.markdown(
        '<div class="sidebar-section-title">Dashboard Mahasiswa (alat)</div>',
        unsafe_allow_html=True,
    )
    gap = repository.days_since_last_message(user_id)
    total_m = repository.count_messages(user_id)
    if total_m == 0:
        st.sidebar.info("Mulai percakapan pertama lewat area chat.")
    elif gap is not None and gap >= 3:
        st.sidebar.warning(f"Sudah ~{int(gap)} hari sejak pesan terakhir. Yuk lanjut belajar.")

    with st.sidebar.expander("Profil", expanded=False):
        user = repository.get_user_by_id(user_id) or {}
        nim = st.text_input("NIM", value=str(user.get("nim") or ""), key="prof_nim")
        cohort = st.text_input("Angkatan", value=str(user.get("cohort") or ""), key="prof_cohort")
        interests = st.text_area(
            "Minat / topik",
            value=str(user.get("interests") or ""),
            key="prof_interests",
            height=68,
        )
        weekly = st.number_input(
            "Target pesan / minggu (disimpan)",
            min_value=1,
            max_value=999,
            value=int(user.get("weekly_message_goal") or 12),
            key="prof_weekly",
        )
        if st.button("Simpan profil", key="prof_save"):
            repository.update_user_profile(
                user_id,
                nim=nim,
                cohort=cohort,
                interests=interests,
                weekly_message_goal=weekly,
            )
            st.success("Profil diperbarui.")

    with st.sidebar.expander("Filter RAG (sesi ini)", expanded=False):
        current = repository.get_session_rag_scope(user_id, active_session_id)
        idx = 0 if current == "all" else 1
        choice = st.selectbox(
            "Sumber konteks retrieval",
            options=["all", "sttnf"],
            index=idx,
            key=f"rag_scope_sel_{active_session_id}",
            format_func=lambda x: "Semua dokumen" if x == "all" else "Berkas berisi 'sttnf' di nama",
        )
        if choice != current:
            repository.set_session_rag_scope(user_id, active_session_id, choice)
            st.rerun()

    with st.sidebar.expander("Prompt tersimpan", expanded=False):
        prompts = repository.list_saved_prompts(user_id)
        for p in prompts:
            c1, c2 = st.columns([4, 1])
            with c1:
                if st.button(p.title[:36] + ("…" if len(p.title) > 36 else ""), key=f"use_prompt_{p.id}"):
                    st.session_state["pending_prompt"] = p.prompt_text
                    st.rerun()
            with c2:
                if st.button("×", key=f"del_prompt_{p.id}"):
                    repository.delete_saved_prompt(user_id, p.id)
                    st.rerun()
        nt = st.text_input("Judul prompt baru", key="new_prompt_title")
        pt = st.text_area("Teks prompt", key="new_prompt_body", height=72)
        if st.button("Tambah prompt", key="add_prompt"):
            pid = repository.add_saved_prompt(user_id, nt, pt)
            if pid:
                st.success("Tersimpan.")
                st.rerun()
            else:
                st.error("Judul atau teks terlalu pendek.")

    with st.sidebar.expander("Bookmark pesan", expanded=False):
        marks = repository.list_message_bookmarks(user_id)
        if not marks:
            st.caption("Belum ada bookmark.")
        for bm in marks:
            st.caption(f"{bm.session_title}")
            st.text((bm.content_preview or "")[:180])
            if st.button("Hapus", key=f"rmbm_{bm.id}"):
                repository.remove_message_bookmark(user_id, bm.id)
                st.rerun()

    with st.sidebar.expander("Unggah PDF ke RAG", expanded=False):
        up = st.file_uploader("PDF", type=["pdf"], key="rag_pdf_up")
        if up and st.button("Ekstrak & indeks ulang", key="rag_pdf_go"):
            try:
                from pypdf import PdfReader

                reader = PdfReader(io.BytesIO(up.getvalue()))
                parts = [(pg.extract_text() or "") for pg in reader.pages]
                text = "\n".join(parts).strip()
                if not text:
                    st.error("Tidak ada teks yang bisa diekstrak dari PDF ini.")
                else:
                    safe = re.sub(r"[^\w\-.]+", "_", Path(up.name).stem)[:50]
                    dest = Path("data/knowledge/uploads")
                    dest.mkdir(parents=True, exist_ok=True)
                    out = dest / f"u{user_id}_{safe}.txt"
                    out.write_text(text[:250_000], encoding="utf-8")
                    nvec = chatbot.rag.force_rebuild_embedding_cache()
                    st.success(f"Berhasil: {out.name}. Vektor indeks: {nvec} potongan.")
            except Exception as exc:
                st.error(f"Gagal memproses PDF: {exc}")


def render_admin_panel(repository: ChatRepository, admin_user_id: int) -> None:
    st.markdown('<h1 class="hero-title">Panel Admin</h1>', unsafe_allow_html=True)
    if not repository.is_admin(admin_user_id):
        st.error("Anda tidak memiliki akses admin.")
        return

    stats = repository.admin_global_stats()
    c1, c2, c3 = st.columns(3)
    c1.metric("Pengguna", stats["users"])
    c2.metric("Sesi", stats["sessions"])
    c3.metric("Pesan", stats["messages"])

    users = repository.admin_list_users()
    st.markdown("### Daftar pengguna")
    st.dataframe(
        pd.DataFrame(users),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Kelola akun")
    if not users:
        st.info("Belum ada pengguna.")
        return

    labels = [f"{u['id']} — {u['username']} ({u['role']})" for u in users]
    pick = st.selectbox("Pilih pengguna", options=labels, key="admin_pick_user")
    target_id = int(pick.split("—", 1)[0].strip())

    row_a, row_b = st.columns(2)
    with row_a:
        npw = st.text_input("Password baru (min 6 karakter)", type="password", key="admin_new_pw")
        if st.button("Terapkan password", key="admin_set_pw"):
            if repository.admin_set_password(target_id, npw):
                st.success("Password diperbarui.")
            else:
                st.error("Password minimal 6 karakter.")

    with row_b:
        target_user = next((u for u in users if int(u["id"]) == target_id), None)
        role_idx = 1 if target_user and str(target_user.get("role")) == "admin" else 0
        new_role = st.selectbox("Role", options=["user", "admin"], index=role_idx, key="admin_new_role")
        if st.button("Simpan role", key="admin_set_role"):
            if target_id == admin_user_id and new_role == "user":
                st.warning("Jangan hilangkan hak admin pada diri sendiri lewat UI ini.")
            elif repository.admin_set_role(target_id, new_role):
                st.success("Role diperbarui. Muat ulang jika perlu.")
                st.rerun()


def render_sidebar(repository: ChatRepository, settings: Settings) -> None:
    compact_mode = st.sidebar.toggle("Compact sidebar (mobile)", value=False, key="compact_sidebar")
    st.sidebar.markdown('<div class="sidebar-section-title">Navigasi</div>', unsafe_allow_html=True)
    st.sidebar.markdown(
        '<div class="sidebar-caption">Kelola sesi belajar dan fitur pendukung dari panel ini.</div>',
        unsafe_allow_html=True,
    )

    new_session_label = "🆕 Sesi Baru" if compact_mode else "🆕 Sesi Belajar Baru"
    if st.sidebar.button(new_session_label, use_container_width=True):
        session_id = repository.create_session(st.session_state["user_id"], "Sesi Baru")
        st.session_state["active_session_id"] = session_id
        st.rerun()

    st.sidebar.divider()
    st.sidebar.markdown('<div class="sidebar-section-title">Riwayat Belajar</div>', unsafe_allow_html=True)
    sessions = repository.list_sessions(st.session_state["user_id"])
    if not sessions:
        st.sidebar.info("Belum ada percakapan.")
        return

    for session in sessions:
        active = session.id == st.session_state["active_session_id"]
        title = f"[PIN] {session.title}" if session.is_pinned else session.title
        if compact_mode:
            trimmed = title[:22] + ("..." if len(title) > 22 else "")
            label = f"{'●' if active else '○'} {trimmed}"
        else:
            label = f" {'*' if active else ''} {title}"
        if st.sidebar.button(label, key=f"session_{session.id}", use_container_width=True):
            st.session_state["active_session_id"] = session.id
            st.rerun()

    st.sidebar.divider()
    with st.sidebar.expander("🔎 Cari Materi", expanded=False):
        search_term = st.text_input("Kata kunci", key="search_term")
        if search_term.strip():
            if search_term != st.session_state.get("search_term_prev", ""):
                st.session_state["search_page"] = 0
                st.session_state["search_term_prev"] = search_term
            results = repository.search_messages(st.session_state["user_id"], search_term, limit=120)
            if not results:
                st.caption("Tidak ada hasil.")
            else:
                page_size = 8
                max_page = (len(results) - 1) // page_size
                if st.session_state["search_page"] > max_page:
                    st.session_state["search_page"] = max_page

                page = st.session_state["search_page"]
                start = page * page_size
                end = start + page_size
                paged_results = results[start:end]
                st.caption(f"Hasil {start + 1}-{min(end, len(results))} dari {len(results)}")

                col_prev, col_next = st.columns(2)
                if col_prev.button("Prev", key="search_prev", use_container_width=True, disabled=page == 0):
                    st.session_state["search_page"] = max(page - 1, 0)
                    st.rerun()
                if col_next.button(
                    "Next",
                    key="search_next",
                    use_container_width=True,
                    disabled=page >= max_page,
                ):
                    st.session_state["search_page"] = min(page + 1, max_page)
                    st.rerun()

                for index, result in enumerate(paged_results, start=start + 1):
                    preview = result.snippet.replace("\n", " ")
                    button_label = f"{index}. {result.session_title}: {preview[:45]}..."
                    if st.button(
                        button_label,
                        key=f"search_result_{index}_{result.session_id}",
                        use_container_width=True,
                    ):
                        st.session_state["active_session_id"] = result.session_id
                        st.rerun()

    st.sidebar.divider()
    with st.sidebar.expander("⚙️ Kelola Sesi Aktif", expanded=False):
        active_id = st.session_state["active_session_id"]
        active_session = next((item for item in sessions if item.id == active_id), None)
        if active_session:
            new_title = st.text_input(
                "Ubah judul sesi",
                value=active_session.title,
                key=f"rename_title_{active_id}",
            )
            current_pin = repository.is_session_pinned(st.session_state["user_id"], active_id)
            pin_label = "Lepas Pin" if current_pin else "Pin Sesi"
            if st.button(pin_label, use_container_width=True):
                if repository.set_session_pinned(st.session_state["user_id"], active_id, not current_pin):
                    st.rerun()
                else:
                    st.error("Gagal memperbarui status pin.")

            if st.button("Simpan Judul", use_container_width=True):
                if repository.rename_session(st.session_state["user_id"], active_id, new_title):
                    st.success("Judul sesi diperbarui.")
                    st.rerun()
                else:
                    st.error("Gagal memperbarui judul sesi.")

            if st.button("Hapus Sesi Aktif", type="secondary", use_container_width=True):
                if repository.delete_session(st.session_state["user_id"], active_id):
                    next_session_id = repository.get_latest_session_id(st.session_state["user_id"])
                    if next_session_id is None:
                        next_session_id = repository.create_session(st.session_state["user_id"], "Sesi Baru")
                    st.session_state["active_session_id"] = next_session_id
                    st.rerun()
                else:
                    st.error("Gagal menghapus sesi.")

    st.sidebar.divider()
    with st.sidebar.expander("🗄️ Alat Data", expanded=False):
        db_path = Path(settings.db_path)
        if db_path.exists():
            st.download_button(
                "Backup Database (.db)",
                data=db_path.read_bytes(),
                file_name=f"{db_path.stem}-backup.db",
                mime="application/octet-stream",
                use_container_width=True,
            )

        uploaded = st.file_uploader("Restore dari file .db", type=["db"], key="restore_db")
        if uploaded is not None and st.button("Restore Sekarang", use_container_width=True):
            backup_path = db_path.with_suffix(".before-restore.db")
            if db_path.exists():
                shutil.copyfile(db_path, backup_path)
            db_path.write_bytes(uploaded.getvalue())
            st.success("Restore selesai. App akan reload.")
            st.rerun()


def render_learning_toolbar() -> None:
    st.markdown('<div class="content-shell">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="edu-banner">
            <strong>Mode Belajar:</strong> pilih gaya jawaban AI sesuai kebutuhanmu.
        </div>
        """,
        unsafe_allow_html=True,
    )
    options = [
        "Ringkas",
        "Penjelasan Detail",
        "Dengan Contoh Praktis",
        "Mode Kuis",
    ]
    current_mode = st.session_state.get("answer_mode", "Penjelasan Detail")
    mode = st.selectbox(
        "Gaya jawaban",
        options=options,
        index=options.index(current_mode) if current_mode in options else 1,
        key="answer_mode_selector",
    )
    st.session_state["answer_mode"] = mode

    st.caption("Quick prompts")
    row1_col1, row1_col2 = st.columns(2)
    row2_col1, row2_col2 = st.columns(2)
    if row1_col1.button("Jelaskan konsep", use_container_width=True):
        st.session_state["pending_prompt"] = "Jelaskan konsep ini untuk pemula: "
    if row1_col2.button("Buat latihan soal", use_container_width=True):
        st.session_state["pending_prompt"] = "Buat 5 latihan soal beserta pembahasan singkat tentang: "
    if row2_col1.button("Rangkum materi", use_container_width=True):
        st.session_state["pending_prompt"] = "Buat rangkuman poin penting untuk topik berikut: "
    if row2_col2.button("Cek pemahaman", use_container_width=True):
        st.session_state["pending_prompt"] = "Berikan 3 pertanyaan cek pemahaman untuk topik: "
    st.markdown("</div>", unsafe_allow_html=True)


def render_hero(app_name: str, sessions_count: int, messages_count: int, answer_mode: str) -> None:
    st.markdown(f'<h1 class="hero-title">{app_name}</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Asisten belajar interaktif untuk diskusi materi, latihan soal, dan rangkuman cepat.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Sesi</div>
                <div class="stat-value">{sessions_count}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Pesan di Sesi Ini</div>
                <div class="stat-value">{messages_count}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Mode Jawaban</div>
                <div class="stat-value">{answer_mode}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_prompt_with_mode(prompt: str) -> str:
    mode = st.session_state.get("answer_mode", "Penjelasan Detail")
    if mode == "Ringkas":
        instruction = "Jawab ringkas dalam 3-5 poin dengan bahasa sederhana."
    elif mode == "Dengan Contoh Praktis":
        instruction = "Jawab dengan langkah praktis dan minimal 1 contoh nyata."
    elif mode == "Mode Kuis":
        instruction = "Jawab singkat lalu lanjutkan dengan kuis 3 soal dan kunci jawaban di akhir."
    else:
        instruction = "Jawab detail, terstruktur, dan mudah dipahami mahasiswa."
    return f"{prompt}\n\nInstruksi format jawaban: {instruction}"


def extract_flashcards(answer: str, max_cards: int = 4) -> List[str]:
    clean = answer.split("\n\nSumber RAG: ", maxsplit=1)[0].strip()
    bullets = re.findall(r"(?:^|\n)[\-\*\d]+\.\s*(.+)", clean)
    cards = [item.strip() for item in bullets if len(item.strip()) > 20]
    if cards:
        return cards[:max_cards]

    sentences = re.split(r"(?<=[.!?])\s+", clean)
    selected = [sentence.strip() for sentence in sentences if len(sentence.strip()) > 30]
    return selected[:max_cards]


def render_chat_messages(repository: ChatRepository, user_id: int, messages: List[Dict[str, str]]) -> None:
    for message in messages:
        avatar = "👩‍🎓" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            content = message["content"]
            if message["role"] == "assistant" and "\n\nSumber RAG: " in content:
                answer, sources = content.split("\n\nSumber RAG: ", maxsplit=1)
                st.markdown(answer)
                st.markdown(
                    f'<div class="rag-box"><strong>Sumber Belajar:</strong> {sources}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(content)
            mid = message.get("id")
            if mid is not None:
                if st.button("⭐ Bookmark", key=f"bookmark_row_{mid}", help="Simpan cuplikan ke panel Bookmark"):
                    if repository.add_message_bookmark(user_id, int(mid)):
                        st.caption("Ditambahkan ke bookmark.")
                    else:
                        st.caption("Sudah ada atau gagal.")


def render_learning_actions(
    chatbot: GeminiChatbotService,
    history: List[Dict[str, str]],
    rag_scope: str,
) -> None:
    st.markdown('<div class="content-shell">', unsafe_allow_html=True)
    st.markdown("### Aksi Belajar Lanjutan")
    st.caption("Gunakan jawaban terakhir AI untuk memperdalam pemahaman tanpa keluar dari sesi.")

    last_answer = st.session_state.get("latest_assistant_answer", "").strip()
    if not last_answer:
        st.info("Belum ada jawaban AI pada sesi ini.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    action_col1, action_col2 = st.columns(2)
    if action_col1.button("Buat Ringkasan 5 Poin", use_container_width=True):
        prompt = (
            "Dari materi berikut, buat ringkasan dalam 5 poin singkat dengan bahasa mahasiswa.\n\n"
            f"Materi:\n{last_answer}"
        )
        result = ""
        with st.spinner("Menyusun ringkasan..."):
            for token in chatbot.stream_answer(prompt, history=history, rag_scope=rag_scope):
                result += token
        st.session_state["learning_artifact_title"] = "Ringkasan 5 Poin"
        st.session_state["learning_artifact_content"] = result.strip()
        st.rerun()

    if action_col2.button("Buat Kuis 5 Soal", use_container_width=True):
        prompt = (
            "Berdasarkan materi berikut, buat 5 soal kuis singkat tingkat dasar-menengah, "
            "lalu berikan kunci jawaban ringkas di bagian akhir.\n\n"
            f"Materi:\n{last_answer}"
        )
        result = ""
        with st.spinner("Menyusun kuis..."):
            for token in chatbot.stream_answer(prompt, history=history, rag_scope=rag_scope):
                result += token
        st.session_state["learning_artifact_title"] = "Kuis 5 Soal"
        st.session_state["learning_artifact_content"] = result.strip()
        st.rerun()

    artifact_title = st.session_state.get("learning_artifact_title", "")
    artifact_content = st.session_state.get("learning_artifact_content", "")
    if artifact_title and artifact_content:
        with st.expander(f"Hasil: {artifact_title}", expanded=True):
            st.markdown(artifact_content)

    st.markdown("</div>", unsafe_allow_html=True)


def render_dashboard(repository: ChatRepository, user_id: int, app_name: str, username: str) -> None:
    st.markdown(
        f'<h1 class="hero-title">Dashboard Mahasiswa</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="hero-subtitle">Halo <strong>{username}</strong> — ringkasan belajar lewat '
        f'<em>{app_name}</em>: aktivitas chat, target mingguan, sesi pin, dan sumber RAG.</div>',
        unsafe_allow_html=True,
    )

    total_sessions = repository.count_sessions(user_id)
    total_messages = repository.count_messages(user_id)
    avg_messages = round(total_messages / total_sessions, 2) if total_sessions else 0.0
    msgs_week = repository.count_messages_in_last_days(user_id, 7)

    st.markdown(
        f"""
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Sesi</div>
                <div class="stat-value">{total_sessions}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Pesan</div>
                <div class="stat-value">{total_messages}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Rata-rata Pesan / Sesi</div>
                <div class="stat-value">{avg_messages}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    prof = repository.get_user_by_id(user_id) or {}
    db_goal = int(prof.get("weekly_message_goal") or 12)

    goal_col, pin_col, rag_col = st.columns([1.1, 1, 1])
    with goal_col:
        st.markdown("### Target belajar (7 hari)")
        goal = st.number_input(
            "Target jumlah pesan (rolling 7 hari)",
            min_value=1,
            max_value=999,
            value=db_goal,
            key=f"dash_weekly_goal_{user_id}",
            help="Disimpan di profil. Menghitung semua pesan user & asisten.",
        )
        if goal != db_goal:
            repository.update_weekly_message_goal(user_id, goal)
            st.rerun()
        ratio = min(1.0, msgs_week / goal) if goal else 0.0
        st.progress(ratio)
        st.caption(f"Progres: **{msgs_week}** / **{goal}** pesan (rolling 7 hari).")

    sessions = repository.list_sessions(user_id)
    pinned = [s for s in sessions if s.is_pinned]

    with pin_col:
        st.markdown("### Sesi di-pin")
        if pinned:
            for s in pinned:
                row1, row2 = st.columns([2, 1])
                with row1:
                    st.markdown(f"📌 **{s.title}**")
                with row2:
                    if st.button("Buka", key=f"dash_open_pin_{s.id}", use_container_width=True):
                        st.session_state["active_session_id"] = s.id
                        st.session_state["main_menu_v3"] = MENU_CHAT
                        st.rerun()
        else:
            st.info("Belum ada sesi di-pin. Di menu Chat, buka **Kelola Sesi Aktif**.")

    with rag_col:
        st.markdown("### Materi RAG tersedia")
        k_files = list_knowledge_filenames()
        if k_files:
            st.caption(f"{len(k_files)} berkas di `data/knowledge`")
            with st.expander("Lihat daftar", expanded=False):
                for name in k_files:
                    st.markdown(f"- `{name}`")
        else:
            st.warning("Folder `data/knowledge` kosong atau belum ada `.md`/`.txt`.")

    st.divider()

    period_col, view_col = st.columns([1, 1])
    with period_col:
        days = st.selectbox(
            "Periode aktivitas",
            options=[7, 14, 30],
            index=1,
            key="dashboard_days",
            format_func=lambda value: f"{value} hari terakhir",
        )
    with view_col:
        chart_style = st.radio(
            "Tipe grafik aktivitas",
            options=["Line", "Area"],
            horizontal=True,
            key="dashboard_chart_style",
        )

    activity = repository.daily_message_activity(user_id, days=days)
    st.markdown(f"### Aktivitas {days} Hari Terakhir")
    if activity:
        activity_df = pd.DataFrame(activity, columns=["Tanggal", "Jumlah Pesan"])
        activity_df["Tanggal"] = pd.to_datetime(activity_df["Tanggal"])

        base = (
            alt.Chart(activity_df)
            .encode(
                x=alt.X("Tanggal:T", title="Tanggal"),
                y=alt.Y("Jumlah Pesan:Q", title="Jumlah Pesan"),
                tooltip=[
                    alt.Tooltip("Tanggal:T", title="Tanggal"),
                    alt.Tooltip("Jumlah Pesan:Q", title="Jumlah Pesan"),
                ],
            )
        )
        if chart_style == "Area":
            chart = base.mark_area(opacity=0.35, line=True, point=True)
        else:
            chart = base.mark_line(point=True, strokeWidth=3)
        st.altair_chart(chart.interactive(), use_container_width=True)
    else:
        st.info("Belum ada aktivitas pesan untuk ditampilkan.")

    st.markdown("### Sesi Paling Aktif")
    top_sessions = repository.top_sessions_by_message_count(user_id, limit=7)
    if top_sessions:
        sessions_df = pd.DataFrame(top_sessions, columns=["Sesi", "Jumlah Pesan"])
        sessions_df["Sesi"] = sessions_df["Sesi"].apply(
            lambda value: value if len(value) <= 40 else f"{value[:40]}..."
        )
        sessions_chart = (
            alt.Chart(sessions_df)
            .mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6)
            .encode(
                x=alt.X("Jumlah Pesan:Q", title="Jumlah Pesan"),
                y=alt.Y("Sesi:N", sort="-x", title="Sesi"),
                color=alt.Color("Jumlah Pesan:Q", legend=None),
                tooltip=[
                    alt.Tooltip("Sesi:N", title="Sesi"),
                    alt.Tooltip("Jumlah Pesan:Q", title="Jumlah Pesan"),
                ],
            )
        )
        st.altair_chart(sessions_chart, use_container_width=True)

        with st.expander("Detail data sesi", expanded=False):
            st.dataframe(sessions_df, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada data sesi aktif.")

    rag_hits = repository.rag_source_frequency(user_id, limit=10)
    st.markdown("### Sumber belajar (RAG) paling sering dipakai")
    if rag_hits:
        rag_df = pd.DataFrame(rag_hits, columns=["Berkas sumber", "Jumlah"])
        rag_chart = (
            alt.Chart(rag_df)
            .mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6)
            .encode(
                x=alt.X("Jumlah:Q", title="Kutipan dalam jawaban"),
                y=alt.Y("Berkas sumber:N", sort="-x", title="Sumber"),
                color=alt.Color("Jumlah:Q", legend=None),
                tooltip=[
                    alt.Tooltip("Berkas sumber:N", title="Sumber"),
                    alt.Tooltip("Jumlah:Q", title="Jumlah"),
                ],
            )
        )
        st.altair_chart(rag_chart, use_container_width=True)
        st.caption("Dihitung dari jawaban asisten yang memuat blok **Sumber RAG** (nama berkas dalam backtick).")
    else:
        st.info("Belum ada riwayat kutipan RAG. Ajukan pertanyaan terkait materi kampus di menu Chat.")

    st.markdown("### Insight Singkat")
    if total_messages == 0:
        st.caption("Belum ada percakapan. Mulai dari menu Chat untuk membangun data dashboard.")
    else:
        st.caption(
            f"Kamu punya {total_sessions} sesi dengan total {total_messages} pesan "
            f"({msgs_week} pesan dalam 7 hari terakhir). "
            f"Rata-rata {avg_messages} pesan per sesi — lanjutkan pola belajar rutin lewat chat."
        )


def main() -> None:
    settings = get_settings()
    setup_app_logging()
    initialize_state()
    st.set_page_config(page_title=settings.app_name, layout="wide")
    st.sidebar.subheader("Preferensi Tampilan")
    st.session_state["theme_mode"] = st.sidebar.radio(
        "Tema",
        options=["Dark", "Light"],
        index=0 if st.session_state.get("theme_mode") == "Dark" else 1,
        horizontal=True,
        key="theme_mode_toggle",
    )
    st.sidebar.divider()
    apply_ui_theme(st.session_state["theme_mode"])
    if not settings.gemini_api_key:
        st.error("GEMINI_API_KEY belum diatur. Silakan isi .env terlebih dahulu.")
        st.stop()

    repository, chatbot = bootstrap_dependencies(settings)
    restore_auth_from_query(settings, repository)
    render_auth_controls(repository)

    if not st.session_state["authenticated"] or not st.session_state["user_id"]:
        render_logged_out_view()
        st.stop()

    user_id = int(st.session_state["user_id"])
    active_session_id = st.session_state["active_session_id"]
    if active_session_id is None or not repository.session_exists(user_id, active_session_id):
        latest = repository.get_latest_session_id(user_id)
        if latest is None:
            latest = repository.create_session(user_id, "Sesi Baru")
        active_session_id = latest
        st.session_state["active_session_id"] = active_session_id

    st.sidebar.divider()
    st.sidebar.subheader("Menu")
    menu_options = [MENU_CHAT, MENU_DASHBOARD]
    if repository.is_admin(user_id):
        menu_options.append(MENU_ADMIN)
    current_menu = st.sidebar.radio(
        "Pilih halaman",
        options=menu_options,
        key="main_menu_v3",
    )
    if current_menu == MENU_DASHBOARD:
        render_dashboard(repository, user_id, settings.app_name, st.session_state.get("username", ""))
        return
    if current_menu == MENU_ADMIN:
        render_admin_panel(repository, user_id)
        return

    render_sidebar(repository, settings)
    render_student_sidebar_extras(repository, chatbot, user_id, active_session_id)

    history = load_chat_history(repository, active_session_id)
    sessions = repository.list_sessions(user_id)
    rag_scope = repository.get_session_rag_scope(user_id, active_session_id)
    render_hero(
        app_name=settings.app_name,
        sessions_count=len(sessions),
        messages_count=len(history),
        answer_mode=st.session_state.get("answer_mode", "Penjelasan Detail"),
    )
    render_learning_toolbar()
    render_chat_messages(repository, user_id, history)
    render_learning_actions(chatbot, history, rag_scope=rag_scope)

    active_session = next((item for item in sessions if item.id == active_session_id), None)
    export_title = active_session.title if active_session else "Sesi Baru"
    markdown_export = export_chat_markdown(export_title, history)
    text_export = export_chat_text(history)
    pdf_export = export_chat_pdf(export_title, st.session_state.get("username", "unknown"), history)
    with st.expander("Session tools"):
        export_col1, export_col2, export_col3 = st.columns(3)
        with export_col1:
            st.download_button(
                "Export Sesi (.md)",
                data=markdown_export,
                file_name=f"session-{active_session_id}.md",
                mime="text/markdown",
                use_container_width=True,
            )
        with export_col2:
            st.download_button(
                "Export Sesi (.txt)",
                data=text_export,
                file_name=f"session-{active_session_id}.txt",
                mime="text/plain",
                use_container_width=True,
            )
        with export_col3:
            st.download_button(
                "Export Sesi (.pdf)",
                data=pdf_export,
                file_name=f"session-{active_session_id}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

    prompt = st.chat_input(
        "Tulis pertanyaanmu di sini...",
        key="main_chat_input",
    )
    if not prompt and st.session_state.get("pending_prompt"):
        prompt = st.session_state["pending_prompt"]
        st.session_state["pending_prompt"] = ""
    if not prompt:
        return

    final_prompt = format_prompt_with_mode(prompt)

    repository.rename_session_if_default(active_session_id, prompt)
    repository.save_message(active_session_id, "user", prompt)

    with st.chat_message("user", avatar="👩‍🎓"):
        st.markdown(prompt)

    conversation_history = history + [{"role": "user", "content": prompt}]
    with st.chat_message("assistant", avatar="🤖"):
        placeholder = st.empty()
        full_response = ""
        sources: List[str] = []
        try:
            with st.status("AI sedang menyusun jawaban...", expanded=False):
                for token in chatbot.stream_answer(
                    final_prompt,
                    history=conversation_history[:-1],
                    rag_scope=rag_scope,
                ):
                    full_response += token
                    placeholder.markdown(full_response)
            sources = chatbot.get_last_sources()
            if sources:
                citation = "\n\nSumber RAG: " + ", ".join(f"`{source}`" for source in sources)
                full_response += citation
                answer, source_part = full_response.split("\n\nSumber RAG: ", maxsplit=1)
                placeholder.markdown(answer)
                st.markdown(
                    f'<div class="rag-box"><strong>Sumber Belajar:</strong> {source_part}</div>',
                    unsafe_allow_html=True,
                )
        except Exception as exc:
            full_response = (
                "Maaf, terjadi kendala saat menghasilkan jawaban. "
                f"Detail: {exc}"
            )
            placeholder.error(full_response)

    flashcards = extract_flashcards(full_response)
    if flashcards:
        with st.expander("Flashcard Otomatis", expanded=False):
            for idx, card in enumerate(flashcards, start=1):
                st.markdown(
                    f'<div class="flashcard"><strong>Kartu {idx}</strong><br>{card}</div>',
                    unsafe_allow_html=True,
                )

    repository.save_message(active_session_id, "assistant", full_response)
    st.session_state["latest_assistant_answer"] = full_response
    st.rerun()


if __name__ == "__main__":
    main()
