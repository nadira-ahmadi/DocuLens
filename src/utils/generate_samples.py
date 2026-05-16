"""
DocuLens — Synthetic German Document Generator
-----------------------------------------------
Generates realistic German invoices and contracts as PDFs
for testing and evaluation — no real data, no NDA issues.

Run directly to create sample files:
    python -m src.utils.generate_samples

Requires: reportlab
    pip install reportlab
"""

import random
from datetime import date, timedelta
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT


# ── Sample data pools ─────────────────────────────────────────────────────────

_COMPANIES = [
    ("TechSolutions GmbH", "Musterstraße 12", "80331 München"),
    ("DataBridge AG", "Hauptstraße 45", "10115 Berlin"),
    ("InnovateTech UG", "Bahnhofplatz 3", "20099 Hamburg"),
    ("Digitale Systeme GmbH", "Schillerstraße 8", "60313 Frankfurt am Main"),
    ("CloudWerk GmbH & Co. KG", "Am Markt 17", "70173 Stuttgart"),
]

_SERVICES = [
    ("Softwareentwicklung", 95.00),
    ("IT-Beratung", 120.00),
    ("Datenbankoptimierung", 85.00),
    ("Cloud-Migration", 110.00),
    ("API-Integration", 90.00),
    ("Projektmanagement", 80.00),
    ("Testing & Qualitätssicherung", 75.00),
    ("Technische Dokumentation", 65.00),
]

_BANKS = [
    ("Commerzbank", "DE89 3704 0044 0532 0130 00", "COBADEFFXXX"),
    ("Deutsche Bank", "DE68 2004 1144 0534 0130 00", "DEUTDEDBHAM"),
    ("Sparkasse München", "DE12 7005 0000 0012 3456 78", "SSKMDEMMXXX"),
]


# ── Invoice generator ─────────────────────────────────────────────────────────

def generate_invoice(output_path: str | Path, seed: int | None = None) -> Path:
    """
    Generate a realistic German invoice PDF.

    Parameters
    ----------
    output_path : path where the PDF will be saved
    seed        : random seed for reproducibility (useful for tests)

    Returns
    -------
    Path to the generated file.
    """
    if seed is not None:
        random.seed(seed)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sender    = random.choice(_COMPANIES)
    recipient = random.choice([c for c in _COMPANIES if c != sender])
    bank      = random.choice(_BANKS)

    invoice_num  = f"RE-{random.randint(2024, 2026)}-{random.randint(1000, 9999)}"
    invoice_date = date.today() - timedelta(days=random.randint(0, 30))
    due_date     = invoice_date + timedelta(days=random.choice([14, 30, 45]))
    tax_id       = f"DE{random.randint(100000000, 999999999)}"

    # Pick 2-4 line items
    items = random.sample(_SERVICES, k=random.randint(2, 4))
    line_items = []
    for name, unit_price in items:
        qty   = random.randint(1, 20)
        price = round(unit_price * qty, 2)
        line_items.append((name, qty, "Std.", unit_price, price))

    subtotal = round(sum(row[4] for row in line_items), 2)
    vat_rate = 0.19
    vat      = round(subtotal * vat_rate, 2)
    total    = round(subtotal + vat, 2)

    # Build PDF
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2.5*cm, bottomMargin=2.5*cm,
    )

    styles = getSampleStyleSheet()
    bold   = ParagraphStyle("bold", parent=styles["Normal"], fontName="Helvetica-Bold")
    right  = ParagraphStyle("right", parent=styles["Normal"], alignment=TA_RIGHT)
    small  = ParagraphStyle("small", parent=styles["Normal"], fontSize=8)
    center = ParagraphStyle("center", parent=styles["Normal"], alignment=TA_CENTER)

    story = []

    # Header: sender info
    story.append(Paragraph(f"<b>{sender[0]}</b>", styles["Heading1"]))
    story.append(Paragraph(sender[1], styles["Normal"]))
    story.append(Paragraph(sender[2], styles["Normal"]))
    story.append(Paragraph(f"USt-ID: {tax_id}", styles["Normal"]))
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 0.5*cm))

    # Recipient
    story.append(Paragraph("<b>Rechnungsempfänger:</b>", bold))
    story.append(Paragraph(recipient[0], styles["Normal"]))
    story.append(Paragraph(recipient[1], styles["Normal"]))
    story.append(Paragraph(recipient[2], styles["Normal"]))
    story.append(Spacer(1, 0.8*cm))

    # Invoice metadata
    meta = [
        ["Rechnungsnummer:", invoice_num],
        ["Rechnungsdatum:", invoice_date.strftime("%d.%m.%Y")],
        ["Fälligkeitsdatum:", due_date.strftime("%d.%m.%Y")],
    ]
    meta_table = Table(meta, colWidths=[5*cm, 8*cm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.8*cm))

    # Title
    story.append(Paragraph(f"<b>RECHNUNG {invoice_num}</b>", styles["Heading2"]))
    story.append(Spacer(1, 0.4*cm))

    # Line items table
    headers = ["Leistungsbeschreibung", "Menge", "Einheit", "Einzelpreis (€)", "Gesamtpreis (€)"]
    rows = [headers]
    for desc, qty, unit, unit_p, total_p in line_items:
        rows.append([desc, str(qty), unit, f"{unit_p:.2f}", f"{total_p:.2f}"])

    col_widths = [7*cm, 2*cm, 2*cm, 3*cm, 3*cm]
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#4A4A8A")),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("ALIGN",      (1,0), (-1,-1), "RIGHT"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    # Totals
    totals_data = [
        ["Nettobetrag:", f"{subtotal:.2f} €"],
        [f"MwSt. ({int(vat_rate*100)}%):", f"{vat:.2f} €"],
        ["Gesamtbetrag:", f"{total:.2f} €"],
    ]
    totals_table = Table(totals_data, colWidths=[12*cm, 4*cm])
    totals_table.setStyle(TableStyle([
        ("ALIGN",    (1,0), (1,-1), "RIGHT"),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("LINEABOVE", (0,-1), (-1,-1), 0.5, colors.grey),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 1*cm))

    # Payment info
    story.append(Paragraph("<b>Bankverbindung:</b>", bold))
    story.append(Paragraph(f"Bank: {bank[0]}", styles["Normal"]))
    story.append(Paragraph(f"IBAN: {bank[1]}", styles["Normal"]))
    story.append(Paragraph(f"BIC:  {bank[2]}", styles["Normal"]))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f"Bitte überweisen Sie den Gesamtbetrag von <b>{total:.2f} €</b> bis zum "
        f"<b>{due_date.strftime('%d.%m.%Y')}</b> unter Angabe der Rechnungsnummer {invoice_num}.",
        styles["Normal"]
    ))
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("Mit freundlichen Grüßen,", styles["Normal"]))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(f"<b>{sender[0]}</b>", bold))

    doc.build(story)
    return output_path


# ── Batch generation ──────────────────────────────────────────────────────────

def generate_batch(output_dir: str | Path, n: int = 10) -> list[Path]:
    """
    Generate n synthetic German invoices for testing.

    Parameters
    ----------
    output_dir : directory to save PDFs
    n          : number of invoices to generate

    Returns
    -------
    List of paths to generated files.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(n):
        path = output_dir / f"rechnung_{i+1:03d}.pdf"
        generate_invoice(path, seed=i)
        print(f"  Generated: {path.name}")
        paths.append(path)
    return paths


if __name__ == "__main__":
    print("Generating 5 sample German invoices...")
    paths = generate_batch("data/samples", n=5)
    print(f"\nDone. {len(paths)} files in data/samples/")
