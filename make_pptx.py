"""
RAG Architecture Overview .pptx 생성 스크립트
실행: python make_pptx.py
"""
from __future__ import annotations

import os
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Cm, Pt

# ──────────────────────────────────────────────
# 공통 색상 팔레트
# ──────────────────────────────────────────────
C_WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
C_BLACK   = RGBColor(0x1A, 0x1A, 0x2E)
C_BLUE1   = RGBColor(0x00, 0x5F, 0xB5)   # 타이틀 계열
C_BLUE2   = RGBColor(0x00, 0x8D, 0xCE)    # 포인트 박스
C_ACCENT  = RGBColor(0x00, 0xB4, 0xD8)   # 화살표·강조
C_INGEST  = RGBColor(0x1B, 0x7F, 0x4D)   # Ingest 계열 (그린)
C_STREAM  = RGBColor(0x00, 0x5F, 0xB5)   # Stream 계열 (블루)
C_LITE    = RGBColor(0xE8, 0xF4, 0xFF)   # 밝은 배경용
C_GRAY    = RGBColor(0x55, 0x69, 0x7A)   # 보조 텍스트
C_YELLOW  = RGBColor(0xFF, 0xC3, 0x00)   # 경고·강조

# 슬라이드 크기 (와이드 16:9)
SLIDE_W = Cm(33.87)
SLIDE_H = Cm(19.05)

FONT_KO = "나눔고딕"  # 없으면 맑은 고딕으로 대체
FONT_FALLBACK = "맑은 고딕"


# ──────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────

def add_rect(slide, x, y, w, h, fill: RGBColor | None = None,
             line_color: RGBColor | None = None, line_width: int = 1,
             radius: bool = False):
    """채워진 직사각형(rounded 옵션) 도형 추가."""
    from pptx.enum.shapes import MSO_SHAPE_TYPE
    from pptx.util import Emu
    shape = slide.shapes.add_shape(
        1 if not radius else 5,  # 1=RECTANGLE, 5=ROUNDED_RECTANGLE
        x, y, w, h)
    shape.line.width = Pt(line_width)
    if fill:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    else:
        shape.fill.background()
    if line_color:
        shape.line.color.rgb = line_color
    else:
        shape.line.fill.background()
    return shape


def add_textbox(slide, text: str, x, y, w, h,
                font_size=12, bold=False, color: RGBColor = C_BLACK,
                align=PP_ALIGN.LEFT, font=None):
    """텍스트 박스 추가."""
    txb = slide.shapes.add_textbox(x, y, w, h)
    tf = txb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font or FONT_FALLBACK
    return txb


def add_arrow(slide, x1, y1, x2, y2, color=C_ACCENT, width=2):
    """라인 + 화살표 연결선."""
    from pptx.util import Emu
    connector = slide.shapes.add_connector(1, x1, y1, x2, y2)   # 1 = straight
    connector.line.color.rgb = color
    connector.line.width = Pt(width)


def set_slide_bg(slide, color: RGBColor = C_WHITE):
    """슬라이드 배경색 설정."""
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_notes(slide, text: str):
    """발표자 노트 삽입."""
    notes_slide = slide.notes_slide
    tf = notes_slide.notes_text_frame
    tf.text = text


def add_title_bar(slide, title: str, subtitle: str | None = None,
                  bar_color=C_BLUE1):
    """상단 제목 바."""
    bar_h = Cm(2.6)
    add_rect(slide, Cm(0), Cm(0), SLIDE_W, bar_h, fill=bar_color)
    add_textbox(slide, title, Cm(0.7), Cm(0.2), SLIDE_W - Cm(1.4), Cm(1.3),
                font_size=20, bold=True, color=C_WHITE, align=PP_ALIGN.LEFT)
    if subtitle:
        add_textbox(slide, subtitle, Cm(0.7), Cm(1.5), SLIDE_W - Cm(1.4), Cm(0.9),
                    font_size=12, bold=False, color=RGBColor(0xCC, 0xE5, 0xFF),
                    align=PP_ALIGN.LEFT)


def flow_box(slide, label: str, x, y, w=Cm(4.0), h=Cm(1.3),
             fill=C_BLUE2, text_color=C_WHITE, font_size=9, radius=True):
    """플로우 박스 + 텍스트."""
    add_rect(slide, x, y, w, h, fill=fill, radius=radius)
    add_textbox(slide, label, x, y + Cm(0.15), w, h,
                font_size=font_size, bold=True, color=text_color,
                align=PP_ALIGN.CENTER)


def arrow_h(slide, x_start, x_end, y, color=C_ACCENT):
    """수평 화살표."""
    add_arrow(slide, x_start, y, x_end, y, color=color)


def arrow_v(slide, x, y_start, y_end, color=C_ACCENT):
    """수직 화살표."""
    add_arrow(slide, x, y_start, x, y_end, color=color)


# ──────────────────────────────────────────────
# 슬라이드 생성 함수들
# ──────────────────────────────────────────────

def slide_01_title(prs: Presentation):
    """슬라이드 1: 제목."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    set_slide_bg(slide, C_WHITE)

    # 상단 짙은 바
    add_rect(slide, Cm(0), Cm(0), SLIDE_W, Cm(1.2), fill=C_BLUE1)

    # 중앙 블루 배경 박스
    add_rect(slide, Cm(1.5), Cm(2.5), SLIDE_W - Cm(3), Cm(8.0), fill=C_BLUE1, radius=True)

    # 제목
    add_textbox(slide, "RAG Architecture Overview",
                Cm(2.0), Cm(3.5), SLIDE_W - Cm(4), Cm(2.5),
                font_size=36, bold=True, color=C_WHITE, align=PP_ALIGN.CENTER)

    # 부제
    add_textbox(slide,
                "Root_Ingest / Root_Stream 기반\n자연어 처리 및 SQL 응답 생성 워크플로우",
                Cm(2.0), Cm(6.2), SLIDE_W - Cm(4), Cm(2.0),
                font_size=16, bold=False, color=C_ACCENT, align=PP_ALIGN.CENTER)

    # 구분선
    add_rect(slide, Cm(8), Cm(8.7), Cm(18), Cm(0.07), fill=C_ACCENT)

    # 메타 정보
    add_textbox(slide, "DB_TO_LLM  |  기술 리뷰 & 내부 공유용  |  2026",
                Cm(2.0), Cm(9.0), SLIDE_W - Cm(4), Cm(0.8),
                font_size=11, color=RGBColor(0xCC, 0xE5, 0xFF), align=PP_ALIGN.CENTER)

    # 하단 구분 바
    add_rect(slide, Cm(0), SLIDE_H - Cm(1.0), SLIDE_W, Cm(1.0), fill=C_BLUE1)
    add_textbox(slide, "Confidential  –  Internal Use Only",
                Cm(1), SLIDE_H - Cm(0.9), SLIDE_W - Cm(2), Cm(0.8),
                font_size=9, color=C_WHITE, align=PP_ALIGN.RIGHT)

    # 사이드 강조선
    add_rect(slide, Cm(0), Cm(1.2), Cm(0.4), Cm(16.85), fill=C_ACCENT)

    add_notes(slide, "이 발표자료는 DB_TO_LLM 프로젝트의 RAG 아키텍처를 기술 리뷰 및 내부 공유 목적으로 정리한 자료입니다. Root_Ingest(문서 수집/임베딩)와 Root_Stream(질의 응답 처리) 두 축의 역할과 상호작용을 설명합니다.")


def slide_02_overview(prs: Presentation):
    """슬라이드 2: 전체 아키텍처 개요."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_WHITE)
    add_title_bar(slide, "전체 아키텍처 개요",
                  "오프라인 지식 준비(Root_Ingest) ↔ 온라인 질의 응답(Root_Stream)")

    # ── 영역 구분 ──
    ingest_x, stream_x = Cm(0.7), Cm(17.5)
    col_w = Cm(15.5)
    row_y = Cm(3.2)

    # 왼쪽 Ingest 박스
    add_rect(slide, ingest_x, row_y, col_w, Cm(13.5),
             fill=RGBColor(0xE8, 0xF7, 0xEE), line_color=C_INGEST, radius=True)
    add_textbox(slide, "📥  Root_Ingest  (오프라인 파이프라인)",
                ingest_x + Cm(0.3), row_y + Cm(0.2), col_w - Cm(0.6), Cm(0.8),
                font_size=12, bold=True, color=C_INGEST)

    # 오른쪽 Stream 박스
    add_rect(slide, stream_x, row_y, col_w, Cm(13.5),
             fill=C_LITE, line_color=C_BLUE1, radius=True)
    add_textbox(slide, "📤  Root_Stream  (온라인 서빙)",
                stream_x + Cm(0.3), row_y + Cm(0.2), col_w - Cm(0.6), Cm(0.8),
                font_size=12, bold=True, color=C_BLUE1)

    # ── Ingest 단계 박스들 ──
    ig_steps = [
        ("①  Source Docs / SQL", C_INGEST),
        ("②  Parser / Loader", RGBColor(0x2E, 0x9E, 0x5E)),
        ("③  Chunking", RGBColor(0x27, 0x8A, 0x52)),
        ("④  Embedding 생성", RGBColor(0x1F, 0x76, 0x46)),
        ("⑤  Vector Store 적재", RGBColor(0x16, 0x63, 0x3A)),
    ]
    ig_bx, ig_w, ig_h = ingest_x + Cm(1.0), Cm(13.5), Cm(1.5)
    for i, (label, col) in enumerate(ig_steps):
        yy = row_y + Cm(1.4) + i * Cm(2.2)
        flow_box(slide, label, ig_bx, yy, w=ig_w, h=ig_h, fill=col, font_size=10)
        if i < len(ig_steps) - 1:
            arrow_v(slide, ig_bx + ig_w / 2, yy + ig_h, yy + ig_h + Cm(0.7), color=C_INGEST)

    # ── Stream 단계 박스들 ──
    st_steps = [
        ("①  사용자 자연어 입력", C_STREAM),
        ("②  질의 임베딩", RGBColor(0x00, 0x52, 0x9B)),
        ("③  Vector DB 검색", RGBColor(0x00, 0x46, 0x85)),
        ("④  Prompt 조합", RGBColor(0x00, 0x3A, 0x70)),
        ("⑤  LLM 추론 & 응답", RGBColor(0x00, 0x2E, 0x5B)),
    ]
    st_bx, st_w, st_h = stream_x + Cm(1.0), Cm(13.5), Cm(1.5)
    for i, (label, col) in enumerate(st_steps):
        yy = row_y + Cm(1.4) + i * Cm(2.2)
        flow_box(slide, label, st_bx, yy, w=st_w, h=st_h, fill=col, font_size=10)
        if i < len(st_steps) - 1:
            arrow_v(slide, st_bx + st_w / 2, yy + st_h, yy + st_h + Cm(0.7), color=C_STREAM)

    # ── 공통 Vector Store 연결 화살표 ──
    vs_y = row_y + Cm(1.4) + 4 * Cm(2.2) + Cm(0.75)  # Ingest 마지막 박스 중간
    retrieval_y = row_y + Cm(1.4) + 2 * Cm(2.2) + Cm(0.75)  # Stream retrieval 중간

    # (화살표: Ingest Vector Store → Stream Vector DB 검색)
    # 우측 화살표: 좌→우
    add_arrow(slide, ingest_x + col_w, vs_y, stream_x, retrieval_y, color=C_YELLOW, width=2)
    add_textbox(slide, "ChromaDB\n(공유 Vector Store)",
                Cm(15.8), (vs_y + retrieval_y) / 2 - Cm(0.5), Cm(2.0), Cm(1.0),
                font_size=7, bold=True, color=C_YELLOW, align=PP_ALIGN.CENTER)

    add_notes(slide, "왼쪽(Root_Ingest)은 오프라인으로 문서를 처리해 Vector DB에 저장합니다. 오른쪽(Root_Stream)은 사용자 질문을 받아 온라인으로 검색·응답합니다. 두 파이프라인은 ChromaDB를 공유합니다.")


def slide_03_ingest(prs: Presentation):
    """슬라이드 3: Root_Ingest 워크플로우 상세."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_WHITE)
    add_title_bar(slide, "Root_Ingest 워크플로우 상세",
                  "문서 수집 → 파싱 → 청킹 → 임베딩 → Vector DB 적재",
                  bar_color=C_INGEST)

    steps = [
        ("📂\nSource\nDocuments\n(SQL/PDF/…)", "원천 데이터 수집\n(SQL DDL, 문서)"),
        ("🔍\nParser /\nLoader", "다양한 포맷\n파싱·정제"),
        ("✂️\nChunking", "chunk_size=800\noverlap=100"),
        ("🧮\nEmbedding\n생성", "sentence-transformers\nmultilingual"),
        ("🗄️\nVector\nStore 적재", "ChromaDB\nPersistentClient"),
        ("🏷️\nMetadata\n저장", "chunk_id, 출처,\n페이지 정보"),
    ]

    step_w, step_h = Cm(4.4), Cm(4.8)
    total_w = len(steps) * step_w + (len(steps) - 1) * Cm(0.9)
    start_x = (SLIDE_W - total_w) / 2
    box_y = Cm(4.2)

    for i, (icon_label, desc) in enumerate(steps):
        bx = start_x + i * (step_w + Cm(0.9))
        # 박스
        col = RGBColor(
            max(0x1B - i * 5, 0x00),
            max(0x7F - i * 8, 0x30),
            max(0x4D - i * 5, 0x00))
        flow_box(slide, icon_label, bx, box_y, w=step_w, h=Cm(3.0), fill=col, font_size=8)
        # 설명
        add_textbox(slide, desc, bx, box_y + Cm(3.2), step_w, Cm(1.4),
                    font_size=8, color=C_GRAY, align=PP_ALIGN.CENTER)
        # 화살표
        if i < len(steps) - 1:
            arrow_h(slide, bx + step_w, bx + step_w + Cm(0.9),
                    box_y + Cm(1.5), color=C_INGEST)

    # 하단 인사이트 박스
    add_rect(slide, Cm(1.0), Cm(11.5), SLIDE_W - Cm(2), Cm(1.8),
             fill=RGBColor(0xE8, 0xF7, 0xEE), line_color=C_INGEST, radius=True)
    add_textbox(slide,
                "💡  Ingest 품질이 Retrieval 품질을 결정합니다  —  "
                "chunk 단위·overlap·embedding 모델 선택이 답변 정확도에 직접적 영향을 줍니다.",
                Cm(1.5), Cm(11.7), SLIDE_W - Cm(3), Cm(1.3),
                font_size=10, bold=False, color=C_INGEST)

    # 파이프라인 오케스트레이터 설명
    add_textbox(slide, "🔧  ingest_pipeline.py  →  collect → parse → chunk → embed → upsert",
                Cm(1.0), Cm(9.5), SLIDE_W - Cm(2), Cm(0.7),
                font_size=9, color=C_GRAY, align=PP_ALIGN.CENTER)

    add_notes(slide, "Root_Ingest는 ingest_pipeline.py → document_loader → parser → chunk_service → embedding_service → vector_store_service 순서로 실행됩니다. config.yaml로 chunk_size(800), overlap(100), embedding 모델을 조정합니다.")


def slide_04_stream(prs: Presentation):
    """슬라이드 4: Root_Stream 워크플로우 상세."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_WHITE)
    add_title_bar(slide, "Root_Stream 워크플로우 상세",
                  "자연어 입력 → 임베딩 → 벡터 검색 → 프롬프트 → LLM → 응답")

    # 세로 스텝 (좌측)
    steps = [
        ("① 사용자 자연어 입력", "StreamRequest\n(question, mode)", C_BLUE1),
        ("② 모드 라우팅", "natural | prompt | rag_prompt\n→ StreamOrchestrator", C_BLUE1),
        ("③ 질의 임베딩", "embed_query()\n→ list[float]", RGBColor(0x00, 0x52, 0x9B)),
        ("④ Vector DB 검색", "ChromaRetriever.retrieve()\n→ top-k chunks", RGBColor(0x00, 0x46, 0x85)),
        ("⑤ Prompt 조합", "PromptManager.render_prompt()\n→ system + user prompt", RGBColor(0x00, 0x3A, 0x70)),
        ("⑥ LLM 추론", "Ollama / OpenAI client\n→ SQL 생성", RGBColor(0x00, 0x2E, 0x5B)),
        ("⑦ 응답 반환", "StreamResult → HTTPResponse\nor CLI 출력", RGBColor(0x00, 0x22, 0x46)),
    ]

    step_w, step_h = Cm(4.5), Cm(1.3)
    desc_w = Cm(8.5)
    lx = Cm(1.2)
    desc_x = lx + step_w + Cm(0.6)
    start_y = Cm(3.2)
    gap = Cm(1.8)

    for i, (label, desc, col) in enumerate(steps):
        yy = start_y + i * gap
        flow_box(slide, label, lx, yy, w=step_w, h=step_h, fill=col, font_size=9)
        add_textbox(slide, desc, desc_x, yy + Cm(0.15), desc_w, step_h,
                    font_size=8, color=C_GRAY)
        if i < len(steps) - 1:
            arrow_v(slide, lx + step_w / 2,
                    yy + step_h, yy + step_h + Cm(0.5), color=C_STREAM)

    # 오른쪽 컴포넌트 그림
    comp_x = Cm(16.5)
    components = [
        ("mode_natural_llm.py", RGBColor(0x3A, 0x86, 0xFF)),
        ("mode_prompt_llm.py", RGBColor(0x3A, 0x86, 0xFF)),
        ("mode_rag_prompt_llm.py", RGBColor(0x00, 0x5F, 0xB5)),
        ("embedding_service.py", RGBColor(0x00, 0x52, 0x9B)),
        ("chroma_retriever.py", RGBColor(0x00, 0x46, 0x85)),
        ("prompt_manager.py", RGBColor(0x00, 0x3A, 0x70)),
        ("ollama_client.py\nopenai_client.py", RGBColor(0x00, 0x2E, 0x5B)),
    ]
    add_textbox(slide, "🧩  핵심 모듈",
                comp_x, Cm(3.0), Cm(15.5), Cm(0.7),
                font_size=11, bold=True, color=C_BLUE1)
    for i, (name, col) in enumerate(components):
        yy = Cm(3.8) + i * Cm(1.8)
        flow_box(slide, name, comp_x, yy, w=Cm(15.5), h=Cm(1.3), fill=col, font_size=8)

    add_notes(slide, "Root_Stream의 핵심은 StreamOrchestrator가 모드를 선택하고, RAG 모드에서는 embedding → ChromaDB 검색 → Prompt 조합 → LLM 순서로 실행됩니다. FastAPI 서버와 CLI 두 가지 진입점이 존재합니다.")


def slide_05_e2e(prs: Presentation):
    """슬라이드 5: End-to-End 시퀀스."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_WHITE)
    add_title_bar(slide, "End-to-End 시퀀스 다이어그램",
                  "사용자 질문 입력 → 최종 SQL 응답 생성까지")

    actors = ["사용자", "API / CLI", "StreamOrchestrator", "EmbeddingService", "ChromaDB", "LLM"]
    actor_cols = [C_YELLOW, C_BLUE1, RGBColor(0x00, 0x52, 0x9B),
                  C_INGEST, RGBColor(0x00, 0x46, 0x85), RGBColor(0x8B, 0x00, 0x00)]

    n = len(actors)
    col_gap = (SLIDE_W - Cm(2)) / n
    actor_y = Cm(3.0)
    actor_h = Cm(1.0)
    actor_w = Cm(4.0)
    life_y_start = actor_y + actor_h
    life_y_end = SLIDE_H - Cm(2.5)

    actor_centers = []
    for i, (name, col) in enumerate(zip(actors, actor_cols)):
        cx = Cm(1.0) + i * col_gap + col_gap / 2 - actor_w / 2
        flow_box(slide, name, cx, actor_y, w=actor_w, h=actor_h, fill=col, font_size=8)
        center_x = cx + actor_w / 2
        actor_centers.append(center_x)
        # 생명선
        add_rect(slide, center_x - Cm(0.04), life_y_start, Cm(0.08),
                 life_y_end - life_y_start, fill=RGBColor(0xCC, 0xCC, 0xCC))

    # 메시지 시퀀스
    msgs = [
        (0, 1, Cm(4.5), "질문 입력 (question, mode='rag_prompt')"),
        (1, 2, Cm(5.6), "generate_stream_query() 라우팅"),
        (2, 3, Cm(6.7), "embed_query(question) 호출"),
        (3, 2, Cm(7.8), "query_embedding: list[float] 반환"),
        (2, 4, Cm(8.9), "collection.query(embeddings, top_k=3)"),
        (4, 2, Cm(10.0), "top-k 청크 + distance 반환"),
        (2, 2, Cm(11.1), "render_prompt(context, question)"),   # self
        (2, 5, Cm(12.2), "generate(system_prompt, user_prompt)"),
        (5, 2, Cm(13.3), "생성된 SQL 반환"),
        (2, 1, Cm(14.4), "StreamResult 반환"),
        (1, 0, Cm(15.5), "HTTP 응답 / CLI 출력"),
    ]

    msg_colors = [C_BLUE1, C_BLUE1, C_INGEST, C_INGEST,
                  RGBColor(0x00, 0x46, 0x85), RGBColor(0x00, 0x46, 0x85),
                  C_GRAY, RGBColor(0x8B, 0x00, 0x00), RGBColor(0x8B, 0x00, 0x00),
                  C_BLUE1, C_YELLOW]

    for idx, (src, dst, yy, label) in enumerate(msgs):
        col = msg_colors[idx]
        x1 = actor_centers[src]
        if src == dst:
            # self-call 루프 (작은 박스로 표현)
            add_rect(slide, x1 + Cm(0.1), yy, Cm(3.5), Cm(0.5),
                     fill=RGBColor(0xE8, 0xF7, 0xFF), line_color=col, radius=True)
            add_textbox(slide, label, x1 + Cm(0.2), yy + Cm(0.05), Cm(3.3), Cm(0.45),
                        font_size=6.5, color=col)
        else:
            x2 = actor_centers[dst]
            add_arrow(slide, x1, yy, x2, yy, color=col, width=1)
            mx = min(x1, x2) + abs(x2 - x1) / 2 - Cm(1)
            add_textbox(slide, label, mx - Cm(2.5), yy - Cm(0.38), Cm(5.0), Cm(0.4),
                        font_size=6, color=col, align=PP_ALIGN.CENTER)

    add_notes(slide, "시퀀스: 사용자 → API → Orchestrator → EmbeddingService(임베딩) → ChromaDB(검색) → PromptManager(프롬프트 렌더) → LLM(SQL 생성) → 사용자 응답. RAG 모드 기준 흐름입니다.")


def slide_06_compare(prs: Presentation):
    """슬라이드 6: Ingest vs Stream 비교."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_WHITE)
    add_title_bar(slide, "Root_Ingest vs Root_Stream 비교",
                  "오프라인 지식 준비 파이프라인 vs 온라인 실시간 서빙 파이프라인")

    headers = ["구분", "Root_Ingest\n(오프라인)", "Root_Stream\n(온라인)"]
    rows = [
        ("목적",           "문서를 임베딩해 Vector DB에 적재",   "사용자 질문에 실시간 응답"),
        ("실행 시점",      "데이터 변경 시 배치 실행",            "사용자 요청마다 즉시 실행"),
        ("주요 입력",      "SQL DDL·문서 파일",                   "자연어 질문 (question)"),
        ("주요 출력",      "ChromaDB 벡터 인덱스",                "생성된 SQL / 자연어 응답"),
        ("핵심 성능 관심", "임베딩 품질·청킹 전략",              "Retrieval 정확도·LLM 응답 품질"),
        ("실행 주체",      "배치 스크립트 / 노트북",              "FastAPI 서버 / CLI"),
        ("대표 모듈",      "ingest_pipeline.py",                  "stream_orchestrator.py"),
    ]

    # 헤더
    col_widths = [Cm(4.5), Cm(13.5), Cm(13.5)]
    col_starts = [Cm(0.7), Cm(5.3), Cm(19.0)]
    header_y = Cm(3.3)
    header_h = Cm(1.2)
    header_fills = [C_BLUE1, C_INGEST, C_BLUE1]

    for j, (hname, cx, cw, cf) in enumerate(zip(headers, col_starts, col_widths, header_fills)):
        flow_box(slide, hname, cx, header_y, w=cw, h=header_h, fill=cf, font_size=9)

    # 데이터 행
    row_h = Cm(1.45)
    for ri, row in enumerate(rows):
        yy = header_y + header_h + ri * row_h
        bg = C_LITE if ri % 2 == 0 else C_WHITE
        for j, (cell, cx, cw) in enumerate(zip(row, col_starts, col_widths)):
            fc = C_GRAY if j == 0 else (C_INGEST if j == 1 else C_BLUE1)
            add_rect(slide, cx, yy, cw, row_h, fill=bg, line_color=RGBColor(0xCC, 0xCC, 0xCC))
            bold_flag = (j == 0)
            add_textbox(slide, cell, cx + Cm(0.2), yy + Cm(0.2), cw - Cm(0.4), row_h - Cm(0.2),
                        font_size=8.5, bold=bold_flag, color=fc)

    # 하단 포인트
    add_rect(slide, Cm(0.7), Cm(16.0), SLIDE_W - Cm(1.4), Cm(1.2),
             fill=C_LITE, line_color=C_ACCENT, radius=True)
    add_textbox(slide,
                "💡  Ingest 품질이 낮으면 Stream의 Retrieval 품질도 저하됩니다. "
                "두 파이프라인을 함께 관리하는 것이 고품질 응답의 핵심입니다.",
                Cm(1.2), Cm(16.1), SLIDE_W - Cm(2.4), Cm(1.0),
                font_size=9, color=C_BLUE1)

    add_notes(slide, "두 파이프라인은 ChromaDB를 공유합니다. Ingest가 잘못되면 Stream 검색 결과도 나빠집니다. 실무에서는 데이터 변경 시 Ingest를 재실행하고, Stream은 항상 최신 Vector DB를 바라보게 설정하는 것이 중요합니다.")


def slide_07_example(prs: Presentation):
    """슬라이드 7: 예시 질의 처리 흐름."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_WHITE)
    add_title_bar(slide, "예시 질의 처리 흐름",
                  "실제 자연어 질문이 SQL로 변환되는 과정")

    # 질문 박스
    add_rect(slide, Cm(1.0), Cm(3.2), SLIDE_W - Cm(2), Cm(1.5),
             fill=RGBColor(0xFF, 0xF9, 0xE6), line_color=C_YELLOW, radius=True)
    add_textbox(slide, "❓  사용자 질문:",
                Cm(1.4), Cm(3.3), Cm(4), Cm(0.6),
                font_size=9, bold=True, color=RGBColor(0x99, 0x60, 0x00))
    add_textbox(slide, '"최근 30일 동안 각 설비별 첫 오류 발생 시각과 마지막 오류 발생 시각, 그리고 총 오류 건수를 함께 보여줘."',
                Cm(5.5), Cm(3.35), SLIDE_W - Cm(6.5), Cm(1.2),
                font_size=9, bold=True, color=C_BLACK)

    # 단계 화살표 흐름 (좌→우, 3열 2행)
    stages = [
        [
            ("🔢  임베딩 변환", "embed_query()\n→ 벡터 [0.12, -0.34, …] 생성", C_INGEST),
            ("🔍  Vector 검색", "ChromaDB top-3 청크 검색\ndistance < 0.4인 문서 반환", C_BLUE1),
            ("📋  Chunk 내용", "ERROR_LOG 테이블 DDL,\n컬럼 설명, 인덱스 정보 포함", RGBColor(0x00, 0x3A, 0x70)),
        ],
        [
            ("🧩  Prompt 구성", "시스템 프롬프트 + Context +\n사용자 질문 조합", RGBColor(0x6A, 0x00, 0x8E)),
            ("🤖  LLM 추론", "Ollama(qwen2.5-coder)\nSQL 생성 요청", RGBColor(0x8B, 0x00, 0x00)),
            ("✅  최종 SQL 출력", "SELECT … FROM ERROR_LOG\nGROUP BY …", RGBColor(0x1B, 0x5E, 0x20)),
        ],
    ]

    bw, bh = Cm(9.5), Cm(2.5)
    for row_i, row in enumerate(stages):
        gy = Cm(5.5) + row_i * Cm(4.2)
        for col_i, (title, desc, col) in enumerate(row):
            gx = Cm(1.0) + col_i * Cm(10.8)
            flow_box(slide, title, gx, gy, w=bw, h=Cm(0.9), fill=col, font_size=9)
            add_rect(slide, gx, gy + Cm(0.9), bw, Cm(1.6),
                     fill=C_LITE, line_color=col, radius=False)
            add_textbox(slide, desc, gx + Cm(0.2), gy + Cm(1.0), bw - Cm(0.4), Cm(1.5),
                        font_size=8, color=C_GRAY)
            # 화살표
            if col_i < 2:
                arrow_h(slide, gx + bw, gx + bw + Cm(1.3), gy + Cm(0.45), color=col)
        # 행 사이 화살표
        if row_i == 0:
            # 오른쪽 끝에서 다음 행 시작으로 (우→하→좌)
            add_textbox(slide, "↓", Cm(16.0), Cm(9.5), Cm(1), Cm(0.8),
                        font_size=18, bold=True, color=C_GRAY, align=PP_ALIGN.CENTER)

    # SQL 출력 샘플
    sql_sample = (
        "SELECT equipment_id,\n"
        "       MIN(error_time) AS first_error,\n"
        "       MAX(error_time) AS last_error,\n"
        "       COUNT(*)        AS total_errors\n"
        "FROM   ERROR_LOG\n"
        "WHERE  error_time >= DATEADD(DAY,-30,GETDATE())\n"
        "GROUP  BY equipment_id\n"
        "ORDER  BY total_errors DESC;"
    )
    add_rect(slide, Cm(1.0), Cm(14.0), SLIDE_W - Cm(2), Cm(4.5),
             fill=RGBColor(0x1A, 0x1A, 0x2E), radius=True)
    add_textbox(slide, sql_sample,
                Cm(1.4), Cm(14.1), SLIDE_W - Cm(2.8), Cm(4.2),
                font_size=8.5, color=RGBColor(0xA8, 0xFF, 0xC4))

    add_notes(slide, "이 예시는 실제 프로젝트에서 테스트한 질문입니다. Vector DB에서 ERROR_LOG 관련 청크가 검색되고, LLM이 해당 컨텍스트를 바탕으로 올바른 GROUP BY + DATE 필터 SQL을 생성합니다.")


def slide_08_ops(prs: Presentation):
    """슬라이드 8: 운영 관점 고려사항."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_WHITE)
    add_title_bar(slide, "운영 관점 고려사항",
                  "실무 체크포인트 — Latency · Quality · Safety · Observability")

    items = [
        ("⚡  Latency",          "임베딩·LLM은 네트워크·GPU 사용량에 민감\n→ 로컬 Ollama 사용으로 네트워크 제거",      RGBColor(0x3A, 0x86, 0xFF)),
        ("🎯  Retrieval Quality","chunk_size, overlap, embedding 모델 선택이 검색 품질 결정\n→ 실험 노트북으로 파라미터 최적화",     C_INGEST),
        ("🔒  SQL 안전성",       "SqlGuard: 금지 키워드(DROP/DELETE) 차단\n→ SELECT-Only 검증 적용",                    RGBColor(0xE6, 0x37, 0x00)),
        ("🌀  Hallucination 방지","컨텍스트 기반 프롬프트 + 예시 SQL 포함\n→ LLM이 추론이 아닌 검색 결과에 의존하도록",  RGBColor(0x8B, 0x00, 0x00)),
        ("💾  Caching",          "동일 질문 임베딩 재사용 고려\n→ Redis/In-memory 캐시 적용 가능",                     C_GRAY),
        ("📊  Monitoring",       "로그 파일(data/logs/) 기록\n→ 응답 시간·오류율·Retrieval 개수 추적",                  RGBColor(0x6A, 0x00, 0x8E)),
        ("🔄  Feedback Loop",    "잘못된 SQL은 재학습 데이터로 활용\n→ 저품질 청크 식별 후 Ingest 재실행",              C_YELLOW),
        ("📦  Chunk 전략",       "너무 짧으면 정보 부족, 너무 길면 노이즈 증가\n→ chunk_size=800, overlap=100 기본 권장", C_BLUE1),
    ]

    cols = 2
    bw, bh = (SLIDE_W - Cm(2.4)) / cols - Cm(0.5), Cm(2.2)
    for i, (title, desc, col) in enumerate(items):
        r, c = divmod(i, cols)
        gx = Cm(0.7) + c * (bw + Cm(0.6))
        gy = Cm(3.4) + r * (bh + Cm(0.35))
        add_rect(slide, gx, gy, bw, bh, fill=C_LITE, line_color=col, radius=True)
        add_textbox(slide, title, gx + Cm(0.3), gy + Cm(0.15), bw - Cm(0.3), Cm(0.7),
                    font_size=9, bold=True, color=col)
        add_textbox(slide, desc, gx + Cm(0.3), gy + Cm(0.75), bw - Cm(0.3), Cm(1.3),
                    font_size=7.5, color=C_GRAY)

    add_notes(slide, "운영 시 가장 중요한 것은 Retrieval 품질과 SQL 안전성입니다. Ingest 파라미터를 노트북에서 실험해 최적화하고, SqlGuard로 위험한 쿼리를 차단하세요.")


def slide_09_summary(prs: Presentation):
    """슬라이드 9: 최종 요약."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    set_slide_bg(slide, C_WHITE)
    add_title_bar(slide, "최종 요약", "Key Takeaways")

    # 두 파이프라인 요약 박스
    add_rect(slide, Cm(0.8), Cm(3.4), Cm(15.0), Cm(8.5),
             fill=RGBColor(0xE8, 0xF7, 0xEE), line_color=C_INGEST, radius=True)
    add_textbox(slide, "📥  Root_Ingest\n지식 준비 파이프라인",
                Cm(1.2), Cm(3.7), Cm(14.0), Cm(1.2),
                font_size=13, bold=True, color=C_INGEST)
    for i, line in enumerate([
        "•  문서 → 파싱 → 청킹 → 임베딩 → ChromaDB 저장",
        "•  오프라인 배치 실행, 데이터 변경 시 재실행",
        "•  chunk 전략이 응답 품질의 기반",
    ]):
        add_textbox(slide, line, Cm(1.4), Cm(5.1) + i * Cm(1.0), Cm(13.8), Cm(0.9),
                    font_size=9, color=C_BLACK)

    add_rect(slide, Cm(17.3), Cm(3.4), Cm(15.0), Cm(8.5),
             fill=C_LITE, line_color=C_BLUE1, radius=True)
    add_textbox(slide, "📤  Root_Stream\n실시간 질의 응답 파이프라인",
                Cm(17.7), Cm(3.7), Cm(14.0), Cm(1.2),
                font_size=13, bold=True, color=C_BLUE1)
    for i, line in enumerate([
        "•  자연어 → 임베딩 → 검색 → 프롬프트 → LLM → SQL",
        "•  FastAPI 서버 + CLI 두 가지 진입점",
        "•  RAG 모드로 컨텍스트 기반 정확도 향상",
    ]):
        add_textbox(slide, line, Cm(17.9), Cm(5.1) + i * Cm(1.0), Cm(13.8), Cm(0.9),
                    font_size=9, color=C_BLACK)

    # 중간 연결
    add_textbox(slide, "⇄\nChromaDB\n공유", Cm(15.4), Cm(6.2), Cm(2.0), Cm(1.8),
                font_size=8, bold=True, color=C_YELLOW, align=PP_ALIGN.CENTER)

    # Key Takeaway 박스 3개
    takeaways = [
        ("1️⃣  Ingest = 지식의 품질",
         "임베딩 모델·청킹 전략이\n모든 응답 품질의 기반",
         C_INGEST),
        ("2️⃣  Stream = 실시간 지성",
         "Retrieval + Context + LLM으로\n자연어를 정확한 SQL로 변환",
         C_BLUE1),
        ("3️⃣  운영 = 지속적 개선",
         "Monitoring + Feedback Loop으로\n품질을 지속적으로 향상",
         RGBColor(0x6A, 0x00, 0x8E)),
    ]
    bw = (SLIDE_W - Cm(2.4)) / 3 - Cm(0.3)
    for i, (title, desc, col) in enumerate(takeaways):
        gx = Cm(0.7) + i * (bw + Cm(0.35))
        gy = Cm(13.0)
        add_rect(slide, gx, gy, bw, Cm(4.3), fill=col, radius=True)
        add_textbox(slide, title, gx + Cm(0.3), gy + Cm(0.3), bw - Cm(0.4), Cm(0.9),
                    font_size=9, bold=True, color=C_WHITE)
        add_textbox(slide, desc, gx + Cm(0.3), gy + Cm(1.3), bw - Cm(0.4), Cm(2.5),
                    font_size=9, color=C_WHITE)

    # 슬라이드 번호
    add_textbox(slide, "DB_TO_LLM  RAG Architecture  |  2026",
                Cm(1), SLIDE_H - Cm(0.9), SLIDE_W - Cm(2), Cm(0.7),
                font_size=8, color=C_GRAY, align=PP_ALIGN.CENTER)

    add_notes(slide, "핵심 요약: Ingest 없이는 좋은 Stream 응답 없음. 두 파이프라인을 함께 관리하고, 지속적인 모니터링과 피드백 루프로 품질을 높이는 것이 운영의 핵심입니다.")


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────

def build_pptx(output_path: str) -> None:
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H

    slide_01_title(prs)
    slide_02_overview(prs)
    slide_03_ingest(prs)
    slide_04_stream(prs)
    slide_05_e2e(prs)
    slide_06_compare(prs)
    slide_07_example(prs)
    slide_08_ops(prs)
    slide_09_summary(prs)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    prs.save(output_path)
    print(f"✅ 저장 완료: {output_path}")


if __name__ == "__main__":
    OUT = r"C:\Users\김민한\Desktop\docs\LLM\RAG_Architecture_Overview.pptx"
    build_pptx(OUT)
