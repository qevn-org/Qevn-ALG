"""Export service producing CSV, JSON, and professional multi-sheet Excel workbooks."""

import io
import json

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from linkedin_intelligence.models.lead import Lead


def export_leads_csv(leads: list[Lead], selected_columns: list[str] | None = None) -> bytes:
    """Export flat lead records as UTF-8 CSV bytes."""
    if not leads:
        return b""

    flat_records = [lead.to_flat_dict() for lead in leads]
    cols = selected_columns or list(flat_records[0].keys())

    import pandas as pd
    df = pd.DataFrame(flat_records)
    valid_cols = [c for c in cols if c in df.columns]
    output = io.StringIO()
    df[valid_cols].to_csv(output, index=False)
    return output.getvalue().encode("utf-8")


def export_leads_json(leads: list[Lead]) -> str:
    """Export canonical leads as formatted JSON."""
    return json.dumps([lead.model_dump() for lead in leads], indent=2, default=str)


def export_leads_xlsx(leads: list[Lead]) -> bytes:
    """Export professional 5-sheet styled Excel workbook."""
    wb = openpyxl.Workbook()
    # Default sheet
    ws_leads = wb.active
    ws_leads.title = "Leads"

    # Sheets to create
    ws_contacts = wb.create_sheet(title="Contacts")
    ws_signals = wb.create_sheet(title="Signals")
    ws_evidence = wb.create_sheet(title="Evidence")
    ws_scoring = wb.create_sheet(title="Scoring")

    # Styling definitions
    header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")  # Navy
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Arial", size=10)
    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )
    align_left = Alignment(horizontal="left", vertical="center")
    align_center = Alignment(horizontal="center", vertical="center")

    # 1. SHEET 1: LEADS
    flat_records = [lead.to_flat_dict() for lead in leads] if leads else []
    if flat_records:
        headers = list(flat_records[0].keys())
        # Omit internal id
        if "id" in headers:
            headers.remove("id")

        ws_leads.append(headers)
        for row_idx, rec in enumerate(flat_records, start=2):
            row_data = [rec.get(h, "") for h in headers]
            ws_leads.append(row_data)

    # 2. SHEET 2: CONTACTS
    contact_headers = [
        "Company", "Person Name", "Contact Type", "Contact Value",
        "Verification Status", "Confidence", "Source URL", "Source Type"
    ]
    ws_contacts.append(contact_headers)
    for lead in leads:
        for c in lead.contacts:
            ws_contacts.append([
                lead.company.name,
                lead.person.name,
                c.type,
                c.value,
                c.verification_status,
                f"{int(c.confidence * 100)}%",
                c.source_url or "",
                c.source_type,
            ])

    # 3. SHEET 3: SIGNALS
    signal_headers = [
        "Company", "Lead Score", "Temperature", "Detected Intent",
        "Signal Type", "Requirement", "Technology Need", "Why Detected"
    ]
    ws_signals.append(signal_headers)
    for lead in leads:
        ws_signals.append([
            lead.company.name,
            lead.score,
            lead.temperature,
            lead.intent.detected_intent,
            lead.intent.signal_type,
            lead.intent.detected_requirement,
            lead.intent.technology_need,
            ", ".join(lead.why_detected),
        ])

    # 4. SHEET 4: EVIDENCE
    evidence_headers = ["Company", "Post ID", "Author Name", "Author Headline", "Post Date", "Post URL", "Content Snippet"]
    ws_evidence.append(evidence_headers)
    for lead in leads:
        ws_evidence.append([
            lead.company.name,
            lead.source.post_id or "",
            lead.source.author_name or "",
            lead.source.author_headline or "",
            lead.source.post_date or "",
            lead.source.post_url or "",
            (lead.source.raw_post_content or "")[:250],
        ])

    # 5. SHEET 5: SCORING (18 features breakdown)
    scoring_headers = [
        "Company", "Person", "Final Score", "Temperature",
        "Hiring Intent", "Buying Intent", "Tech Intent", "Decision Maker Prob",
        "Post Freshness", "Urgency", "Company Fit", "Company Size Score",
        "Industry Fit", "Geo Fit", "Role Relevance", "Vendor Search",
        "Hiring Velocity", "Evidence Conf"
    ]
    ws_scoring.append(scoring_headers)
    for lead in leads:
        feat = lead.feature_vector or {}
        ws_scoring.append([
            lead.company.name,
            lead.person.name,
            lead.score,
            lead.temperature,
            feat.get("hiring_intent", 0),
            feat.get("buying_intent", 0),
            feat.get("technology_intent", 0),
            feat.get("decision_maker_probability", 0),
            feat.get("post_freshness", 0),
            feat.get("urgency", 0),
            feat.get("company_fit", 0),
            feat.get("company_size_score", 0),
            feat.get("industry_fit", 0),
            feat.get("geographic_fit", 0),
            feat.get("role_relevance", 0),
            feat.get("explicit_vendor_search", 0),
            feat.get("hiring_velocity", 0),
            feat.get("evidence_confidence", 0),
        ])

    # Apply formatting to all 5 sheets
    for ws in [ws_leads, ws_contacts, ws_signals, ws_evidence, ws_scoring]:
        # Freeze top row
        ws.freeze_panes = "A2"

        # Enable auto-filter
        max_col_letter = get_column_letter(ws.max_column) if ws.max_column > 0 else "A"
        ws.auto_filter.ref = f"A1:{max_col_letter}{max(1, ws.max_row)}"

        # Style header
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = align_center

        # Style data cells & auto-adjust column width
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                cell.border = thin_border
                if cell.row > 1:
                    cell.font = data_font
                    cell.alignment = align_left
                val_str = str(cell.value or "")
                max_len = max(max_len, min(len(val_str), 45))

            ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
