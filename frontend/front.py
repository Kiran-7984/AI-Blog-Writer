import streamlit as st
import requests
import json
import time
from datetime import datetime
from io import BytesIO
import re
import html

from io import BytesIO
import re
import html

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    Preformatted,
    KeepTogether,
)

if "final_blog" not in st.session_state:
    st.session_state.final_blog = ""

st.set_page_config(
    page_title="AI Blog Writer",
    page_icon="🤖",
    layout="wide"
)


# ------------------ CSS ------------------

st.markdown("""
<style>

.stApp{
    background:#0f172a;
    color:white;
}

.block-container{
    padding-top:2rem;
}

.main-title{
    font-size:42px;
    font-weight:700;
    text-align:center;
    color:white;
}

.subtitle{
    text-align:center;
    color:#94a3b8;
    margin-bottom:30px;
}

.card{
    background:#1e293b;
    border-radius:15px;
    padding:18px;
    border:1px solid #334155;
}

.metric{
    background:#1e293b;
    border-radius:12px;
    padding:15px;
    text-align:center;
}

.workflow-box{
    background:#1e293b;
    border-radius:12px;
    padding:15px;
    margin-bottom:12px;
    border-left:6px solid gray;
}

.running{
    border-left:6px solid orange;
}

.completed{
    border-left:6px solid #22c55e;
}

.waiting{
    border-left:6px solid gray;
}

.terminal{
    background:black;
    color:#22c55e;
    border-radius:10px;
    padding:15px;
    height:280px;
    overflow:auto;
    font-family:monospace;
}

.stButton>button{
    width:100%;
    background:#2563eb;
    color:white;
    height:52px;
    border-radius:10px;
    font-size:18px;
    border:none;
}

.stButton>button:hover{
    background:#1d4ed8;
}

</style>
""", unsafe_allow_html=True)

# ---------------- Header ----------------

st.markdown(
    "<div class='main-title'>🤖 AI Multi-Agent Blog Writer</div>",
    unsafe_allow_html=True
)

st.markdown(
    "<div class='subtitle'>Powered by LangGraph | FastAPI</div>",
    unsafe_allow_html=True
)

# ---------------- Input ----------------

topic = st.text_area(
    "Blog Topic",
    placeholder="Example: Explain LangGraph in depth...",
    height=120
)

generate = st.button("🚀 Generate Blog")

st.divider()

# ---------------- Metrics ----------------

m1,m2,m3 = st.columns(3)

with m1:
    st.markdown(
        "<div class='metric'><h3>Status</h3><h2>Idle</h2></div>",
        unsafe_allow_html=True
    )

with m2:
    st.markdown(
        "<div class='metric'><h3>Current Node</h3><h2>---</h2></div>",
        unsafe_allow_html=True
    )

with m3:
    st.markdown(
        "<div class='metric'><h3>Elapsed</h3><h2>0 s</h2></div>",
        unsafe_allow_html=True
    )

st.write("")

# ---------------- Layout ----------------

left,right = st.columns([1,1])

# Workflow

with left:

    st.subheader("⚡ Workflow")

    workflow_placeholder = st.empty()

# Terminal

with right:

    st.subheader("💻 Live Terminal")

    terminal_container = st.empty()

terminal_container.markdown(
"""
<div class='terminal'>

Waiting for execution...

</div>
""",
unsafe_allow_html=True
)

nodes = [
    "router",
    "research",
    "orchestrator",
    "worker",
    "reducer"
]

status_map = {
    node:"waiting"
    for node in nodes
}

def create_pdf(blog):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
        title="AI Generated Blog",
        author="AI Multi-Agent Blog Writer",
        subject="AI Generated Article",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "BlogTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=29,
        alignment=TA_CENTER,
        spaceAfter=12,
        textColor=colors.HexColor("#172554"),
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=20,
    )

    h1_style = ParagraphStyle(
        "BlogH1",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=16,
        spaceAfter=8,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "BlogH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#334155"),
        spaceBefore=13,
        spaceAfter=6,
        keepWithNext=True,
    )

    h3_style = ParagraphStyle(
        "BlogH3",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor("#475569"),
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "BlogBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.2,
        leading=16,
        textColor=colors.HexColor("#1E293B"),
        alignment=TA_LEFT,
        spaceAfter=8,
    )

    bullet_style = ParagraphStyle(
        "Bullet",
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-7,
        spaceAfter=5,
    )

    numbered_style = ParagraphStyle(
        "Numbered",
        parent=body_style,
        leftIndent=17,
        firstLineIndent=-12,
        spaceAfter=5,
    )

    source_style = ParagraphStyle(
        "Source",
        parent=body_style,
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        leftIndent=8,
        textColor=colors.HexColor("#2563EB"),
        spaceBefore=2,
        spaceAfter=10,
    )

    code_style = ParagraphStyle(
        "Code",
        parent=styles["Code"],
        fontName="Courier",
        fontSize=8.5,
        leading=11,
        leftIndent=8,
        rightIndent=8,
        spaceBefore=6,
        spaceAfter=8,
        backColor=colors.HexColor("#F1F5F9"),
        borderColor=colors.HexColor("#CBD5E1"),
        borderWidth=0.5,
        borderPadding=7,
    )

    quote_style = ParagraphStyle(
        "Quote",
        parent=body_style,
        leftIndent=15,
        rightIndent=10,
        fontName="Helvetica-Oblique",
        textColor=colors.HexColor("#475569"),
        borderColor=colors.HexColor("#94A3B8"),
        borderWidth=0.5,
        borderPadding=8,
        backColor=colors.HexColor("#F8FAFC"),
        spaceBefore=6,
        spaceAfter=8,
    )

    def draw_page(canvas, doc):
        canvas.saveState()

        width, height = A4

        canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
        canvas.setLineWidth(0.5)

        canvas.line(
            18 * mm,
            height - 14 * mm,
            width - 18 * mm,
            height - 14 * mm,
        )

        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.HexColor("#475569"))

        canvas.drawString(
            18 * mm,
            height - 10.5 * mm,
            "AI MULTI-AGENT BLOG WRITER",
        )

        canvas.setFont("Helvetica", 8)

        canvas.drawRightString(
            width - 18 * mm,
            height - 10.5 * mm,
            "Research • Write • Review",
        )

        canvas.line(
            18 * mm,
            13 * mm,
            width - 18 * mm,
            13 * mm,
        )

        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#64748B"))

        canvas.drawString(
            18 * mm,
            8 * mm,
            "Generated by AI Multi-Agent Blog Writer",
        )

        canvas.drawRightString(
            width - 18 * mm,
            8 * mm,
            f"Page {doc.page}",
        )

        canvas.restoreState()

    def format_inline(text):
        if not text:
            return ""

        text = html.escape(text)

        placeholders = []

        def save_link(match):
            index = len(placeholders)

            label = match.group(1)
            url = match.group(2)

            safe_url = html.escape(url, quote=True)
            safe_label = html.escape(label)

            if label.strip().lower() == "source":
                placeholders.append(
                    f'<link href="{safe_url}" color="#2563EB">'
                    f'<u>Source</u>'
                    f'</link>'
                )
            else:
                placeholders.append(
                    f'<link href="{safe_url}" color="#2563EB">'
                    f'<u>{safe_label}</u>'
                    f'</link>'
                )

            return f"XLINK{index}X"

        text = re.sub(
            r"\[([^\]]+)\]\((https?://[^)]+)\)",
            save_link,
            text,
        )

        text = re.sub(
            r"\*\*\*(.+?)\*\*\*",
            r"<b><i>\1</i></b>",
            text,
        )

        text = re.sub(
            r"\*\*(.+?)\*\*",
            r"<b>\1</b>",
            text,
        )

        text = re.sub(
            r"__(.+?)__",
            r"<b>\1</b>",
            text,
        )

        text = re.sub(
            r"(?<!\*)\*([^*]+?)\*(?!\*)",
            r"<i>\1</i>",
            text,
        )

        text = re.sub(
            r"(?<!_)_([^_]+?)_(?!_)",
            r"<i>\1</i>",
            text,
        )

        text = re.sub(
            r"`([^`]+)`",
            r'<font name="Courier" color="#475569">\1</font>',
            text,
        )

        for index, link in enumerate(placeholders):
            text = text.replace(
                f"XLINK{index}X",
                link,
            )

        return text

    def clean_source_markdown(text):
        return re.sub(
            r"\(\s*(\[Source\]\(https?://[^)]+\))\s*\)",
            r"\1",
            text,
            flags=re.IGNORECASE,
        )

    blog = blog.replace("\r\n", "\n")
    lines = blog.split("\n")

    title = "AI Generated Blog"

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("# "):
            title = stripped[2:].strip()
            break

    story = []

    story.append(
        Spacer(1, 8 * mm)
    )

    story.append(
        Paragraph(
            format_inline(title),
            title_style,
        )
    )

    story.append(
        Paragraph(
            "AI Multi-Agent Blog Writer",
            subtitle_style,
        )
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor("#CBD5E1"),
            spaceBefore=2,
            spaceAfter=12,
        )
    )

    i = 0

    while i < len(lines):

        line = lines[i].strip()

        if not line:
            story.append(
                Spacer(1, 3)
            )

            i += 1
            continue

        if line.startswith("# "):
            i += 1
            continue

        if line.startswith("## "):

            heading = line[3:].strip()

            story.append(
                Paragraph(
                    format_inline(heading),
                    h1_style,
                )
            )

            i += 1
            continue

        if line.startswith("### "):

            heading = line[4:].strip()

            story.append(
                Paragraph(
                    format_inline(heading),
                    h2_style,
                )
            )

            i += 1
            continue

        if line.startswith("#### "):

            heading = line[5:].strip()

            story.append(
                Paragraph(
                    format_inline(heading),
                    h3_style,
                )
            )

            i += 1
            continue

        if line.startswith("```"):

            code_lines = []

            i += 1

            while (
                i < len(lines)
                and not lines[i].strip().startswith("```")
            ):
                code_lines.append(lines[i])
                i += 1

            if i < len(lines):
                i += 1

            story.append(
                Preformatted(
                    "\n".join(code_lines),
                    code_style,
                )
            )

            continue

        if re.match(r"^[-*+]\s+", line):

            items = []

            while i < len(lines):

                current = lines[i].strip()

                match = re.match(
                    r"^[-*+]\s+(.*)",
                    current,
                )

                if not match:
                    break

                items.append(
                    match.group(1)
                )

                i += 1

            for item in items:

                item = clean_source_markdown(item)

                story.append(
                    Paragraph(
                        "• " + format_inline(item),
                        bullet_style,
                    )
                )

            continue

        if re.match(r"^\d+\.\s+", line):

            items = []

            while i < len(lines):

                current = lines[i].strip()

                match = re.match(
                    r"^(\d+)\.\s+(.*)",
                    current,
                )

                if not match:
                    break

                items.append(
                    (
                        match.group(1),
                        match.group(2),
                    )
                )

                i += 1

            for number, item in items:

                item = clean_source_markdown(item)

                story.append(
                    Paragraph(
                        f"{number}. {format_inline(item)}",
                        numbered_style,
                    )
                )

            continue

        if line.startswith(">"):

            quote_lines = []

            while i < len(lines):

                current = lines[i].strip()

                if not current.startswith(">"):
                    break

                quote_lines.append(
                    current[1:].strip()
                )

                i += 1

            quote_text = " ".join(quote_lines)

            quote_text = clean_source_markdown(
                quote_text
            )

            story.append(
                Paragraph(
                    format_inline(quote_text),
                    quote_style,
                )
            )

            continue

        if "|" in line and i + 1 < len(lines):

            separator = lines[i + 1].strip()

            if re.match(
                r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?$",
                separator,
            ):

                rows = []

                header = [
                    cell.strip()
                    for cell in line.strip("|").split("|")
                ]

                rows.append(header)

                i += 2

                while i < len(lines):

                    current = lines[i].strip()

                    if not current or "|" not in current:
                        break

                    row = [
                        cell.strip()
                        for cell in current.strip("|").split("|")
                    ]

                    rows.append(row)

                    i += 1

                formatted_rows = []

                for row_index, row in enumerate(rows):

                    formatted_row = []

                    for cell in row:

                        cell = clean_source_markdown(cell)

                        cell_style = ParagraphStyle(
                            "TableCell",
                            parent=body_style,
                            fontSize=8.5,
                            leading=11,
                            spaceAfter=0,
                        )

                        if row_index == 0:

                            cell_style = ParagraphStyle(
                                "TableHeader",
                                parent=cell_style,
                                fontName="Helvetica-Bold",
                                textColor=colors.white,
                            )

                        formatted_row.append(
                            Paragraph(
                                format_inline(cell),
                                cell_style,
                            )
                        )

                    formatted_rows.append(
                        formatted_row
                    )

                table = Table(
                    formatted_rows,
                    repeatRows=1,
                    hAlign="LEFT",
                )

                table.setStyle(
                    TableStyle([
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.HexColor("#1E3A8A"),
                        ),
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.4,
                            colors.HexColor("#CBD5E1"),
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "TOP",
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            6,
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            6,
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            6,
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            6,
                        ),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [
                                colors.white,
                                colors.HexColor("#F8FAFC"),
                            ],
                        ),
                    ])
                )

                story.append(
                    Spacer(1, 5)
                )

                story.append(table)

                story.append(
                    Spacer(1, 8)
                )

                continue

        paragraph_lines = [line]

        i += 1

        while i < len(lines):

            next_line = lines[i].strip()

            if not next_line:
                break

            if (
                next_line.startswith("#")
                or re.match(r"^[-*+]\s+", next_line)
                or re.match(r"^\d+\.\s+", next_line)
                or next_line.startswith(">")
                or next_line.startswith("```")
                or next_line.startswith("|")
            ):
                break

            paragraph_lines.append(
                next_line
            )

            i += 1

        paragraph_text = " ".join(
            paragraph_lines
        )

        paragraph_text = clean_source_markdown(
            paragraph_text
        )

        source_match = re.search(
            r"Source(https?://[^)]+)",
            paragraph_text,
            re.IGNORECASE,
        )

        if source_match:

            source_url = source_match.group(1)

            content_text = re.sub(
                r"\s*Sourcehttps?://[^)]+",
                "",
                paragraph_text,
                flags=re.IGNORECASE,
            ).strip()

            if content_text:

                story.append(
                    Paragraph(
                        format_inline(content_text),
                        body_style,
                    )
                )

            safe_url = html.escape(
                source_url,
                quote=True,
            )

            story.append(
                Paragraph(
                    f'<link href="{safe_url}" color="#2563EB">'
                    f'<u>Source</u>'
                    f'</link>',
                    source_style,
                )
            )

        else:

            story.append(
                Paragraph(
                    format_inline(paragraph_text),
                    body_style,
                )
            )

    doc.build(
        story,
        onFirstPage=draw_page,
        onLaterPages=draw_page,
    )

    buffer.seek(0)

    return buffer.getvalue()

def draw_workflow():

    with workflow_placeholder.container():

        for node in nodes:

            cls = status_map[node]

            emoji = {
                "waiting": "⚪",
                "running": "🟡",
                "completed": "🟢"
            }[cls]

            st.markdown(
                f"""
<div class='workflow-box {cls}'>
<h4>{emoji} {node.title()}</h4>
</div>
                """,
                unsafe_allow_html=True
            )

draw_workflow()

# ----------------------------------------------
# Backend Connection
# ----------------------------------------------

import sseclient

API_URL = "http://127.0.0.1:8000/generate"

terminal_logs = []


def draw_terminal():

    html = "<div class='terminal'>"

    for log in terminal_logs[-25:]:

        html += f"{log}<br>"

    html += "</div>"

    terminal_container.markdown(
        html,
        unsafe_allow_html=True
    )


if generate:

    if topic.strip() == "":

        st.warning("Please enter a topic.")

        st.stop()

    # reset workflow

    for n in nodes:
        status_map[n] = "waiting"

    draw_workflow()

    terminal_logs.clear()

    terminal_logs.append(
        "Connecting to backend..."
    )

    draw_terminal()

    payload = {
        "topic": topic
    }

    try:

        response = requests.post(
            API_URL,
            json=payload,
            stream=True,
            headers={
                "Accept": "text/event-stream"
            }
        )

        client = sseclient.SSEClient(response)

        start = time.time()

        status_placeholder = m1.empty()
        node_placeholder = m2.empty()
        time_placeholder = m3.empty()

        for event in client.events():

            if not event.data:
                continue

            data = json.loads(event.data)

            event_type = data.get("type")

            # --------------------

            if event_type == "node_start":

                node = data["node"]

                status_map[node] = "running"

                draw_workflow()

                terminal_logs.append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] ▶ Started {node}"
                )

                draw_terminal()

                status_placeholder.markdown(
                    "<div class='metric'><h3>Status</h3><h2>Running</h2></div>",
                    unsafe_allow_html=True
                )

                node_placeholder.markdown(
                    f"<div class='metric'><h3>Current Node</h3><h2>{node.title()}</h2></div>",
                    unsafe_allow_html=True
                )

            # --------------------

            elif event_type == "node_end":

                node = data["node"]

                status_map[node] = "completed"

                draw_workflow()

                terminal_logs.append(
                    f"[{datetime.now().strftime('%H:%M:%S')}] ✔ Finished {node}"
                )

                draw_terminal()

            # --------------------

            elif event_type == "completed":

                status_placeholder.markdown(
                    "<div class='metric'><h3>Status</h3><h2>Completed</h2></div>",
                    unsafe_allow_html=True
                )

                node_placeholder.markdown(
                    "<div class='metric'><h3>Current Node</h3><h2>Done</h2></div>",
                    unsafe_allow_html=True
                )

                st.session_state.final_blog = data.get("final_blog", "")

                terminal_logs.append(
                    "🎉 Workflow Completed Successfully!"
                )

                draw_terminal()

                break

            elapsed = int(time.time() - start)

            time_placeholder.markdown(
                f"<div class='metric'><h3>Elapsed</h3><h2>{elapsed} s</h2></div>",
                unsafe_allow_html=True
            )

    except Exception as e:

        st.error(e)

print("========== FINAL BLOG ==========")
print(st.session_state.final_blog)
print("========== END FINAL BLOG ==========")

pdf = create_pdf(st.session_state.final_blog)

st.download_button(
    "📄 Download Beautiful PDF",
    data=pdf,
    file_name="AI_Blog.pdf",
    mime="application/pdf"
)