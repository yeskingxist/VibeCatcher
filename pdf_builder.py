import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

DOWNLOADS_DIR = Path(__file__).parent / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

def generate_cumulative_pdf(pdf_filename: str, history_data: list) -> str:
    """
    Generates a styled, cumulative PDF summary report from all parsed Reels and their DMs.
    """
    file_path = DOWNLOADS_DIR / pdf_filename
    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#6366f1'),
        spaceAfter=5
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=15
    )

    reel_header_style = ParagraphStyle(
        'ReelHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#4f46e5'),
        spaceBefore=14,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'H2Header',
        parent=styles['Heading3'],
        fontSize=11,
        textColor=colors.HexColor('#0f172a'),
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#334155'),
        spaceAfter=6
    )

    story = []

    # Title & Overall Meta
    story.append(Paragraph("Instagram Reels Consolidated Summary Report", title_style))
    story.append(Paragraph(f"Compiled Reels: {len(history_data)} &nbsp;|&nbsp; Persistent Resource Harvesting", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#6366f1'), spaceAfter=15))

    if not history_data:
        story.append(Paragraph("No Reel resources harvested yet.", body_style))
    else:
        for idx, entry in enumerate(history_data, 1):
            creator = entry.get("creator", "Unknown")
            reel_url = entry.get("reel_url", "N/A")
            resources = entry.get("resources", [])

            # Reel Section Header
            story.append(Paragraph(f"Reel #{idx}: @{creator}", reel_header_style))
            story.append(Paragraph(f"<b>Reel Link:</b> <a href='{reel_url}' color='#4f46e5'>{reel_url}</a>", body_style))
            story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor('#e2e8f0'), spaceAfter=10))

            if not resources:
                story.append(Paragraph("No resources extracted for this Reel.", body_style))
            else:
                for r_idx, res in enumerate(resources, 1):
                    url = res.get("url", "N/A")
                    title = res.get("title", f"Resource #{r_idx}")
                    summary = res.get("summary", "No summary available.")
                    snippets = res.get("snippets", [])

                    story.append(Paragraph(f"<b>Resource {idx}.{r_idx}: {title}</b>", h2_style))
                    story.append(Paragraph(f"<b>URL:</b> <a href='{url}' color='#2563eb'>{url}</a>", body_style))
                    story.append(Paragraph(f"<b>Summary:</b> {summary}", body_style))

                    if snippets:
                        story.append(Paragraph("<b>Key Highlights:</b>", body_style))
                        for snip in snippets:
                            story.append(Paragraph(f"• {snip}", body_style))
                    
                    story.append(Spacer(1, 4))
            
            story.append(Spacer(1, 10))
            story.append(HRFlowable(width="100%", thickness=1.2, color=colors.HexColor('#cbd5e1'), spaceBefore=10, spaceAfter=15))

    doc.build(story)
    return str(file_path.name)

