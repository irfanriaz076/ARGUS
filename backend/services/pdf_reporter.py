from io import BytesIO
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, HRFlowable, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether,
)

W, H = A4

# ── Palette (print-safe black & white with red accents) ──────────────────────
RED       = HexColor('#CC1111')
DARK_RED  = HexColor('#990000')
BLACK     = HexColor('#111111')
DARK_GRAY = HexColor('#333333')
MID_GRAY  = HexColor('#666666')
LIGHT_GRAY= HexColor('#AAAAAA')
BG_LIGHT  = HexColor('#F5F5F5')
BG_WHITE  = white
BORDER    = HexColor('#CCCCCC')

SEV_COLOR = {
    'critical': HexColor('#CC0000'),
    'high':     HexColor('#CC5500'),
    'medium':   HexColor('#AA7700'),
    'low':      HexColor('#227722'),
    'info':     MID_GRAY,
}
SEV_BG = {
    'critical': HexColor('#FFF0F0'),
    'high':     HexColor('#FFF5EE'),
    'medium':   HexColor('#FFFBEE'),
    'low':      HexColor('#F0FFF0'),
    'info':     HexColor('#F8F8F8'),
}

# Hex strings for inline <font color> markup
SEV_HEX = {
    'critical': '#CC0000', 'high': '#CC5500', 'medium': '#AA7700',
    'low': '#227722', 'info': '#666666',
}
RATING_HEX = {'Critical': '#CC0000', 'High': '#CC5500', 'Medium': '#AA7700', 'Low': '#227722'}


def _esc(s: Any) -> str:
    """Escape text destined for a reportlab Paragraph (LLM output may contain & < >)."""
    return _xml_escape(str(s if s is not None else ''))


# ── Styles ────────────────────────────────────────────────────────────────────
def _styles():
    b = ParagraphStyle

    return {
        'cover_title': b('CoverTitle',
            fontName='Helvetica-Bold', fontSize=36,
            textColor=RED, alignment=TA_CENTER, spaceAfter=2*mm),

        'cover_sub': b('CoverSub',
            fontName='Helvetica', fontSize=13,
            textColor=DARK_GRAY, alignment=TA_CENTER, spaceAfter=6*mm),

        'cover_field': b('CoverField',
            fontName='Helvetica-Bold', fontSize=14,
            textColor=BLACK, alignment=TA_CENTER, spaceAfter=3*mm),

        'cover_meta': b('CoverMeta',
            fontName='Helvetica', fontSize=10,
            textColor=MID_GRAY, alignment=TA_CENTER, spaceAfter=2*mm),

        'h1': b('H1',
            fontName='Helvetica-Bold', fontSize=16,
            textColor=BLACK, spaceBefore=4*mm, spaceAfter=2*mm),

        'h2': b('H2',
            fontName='Helvetica-Bold', fontSize=12,
            textColor=RED, spaceBefore=4*mm, spaceAfter=2*mm),

        'body': b('Body',
            fontName='Helvetica', fontSize=9,
            textColor=DARK_GRAY, leading=14, spaceAfter=1*mm),

        'mono': b('Mono',
            fontName='Courier', fontSize=8,
            textColor=DARK_GRAY, leading=12, spaceAfter=1*mm),

        'label': b('Label',
            fontName='Helvetica-Bold', fontSize=8,
            textColor=MID_GRAY, spaceAfter=0.5*mm),

        'finding_title': b('FindingTitle',
            fontName='Helvetica-Bold', fontSize=10,
            textColor=BLACK, spaceAfter=1*mm),

        'evidence': b('Evidence',
            fontName='Courier', fontSize=7.5,
            textColor=DARK_GRAY, leading=11,
            backColor=BG_LIGHT, leftIndent=4*mm,
            spaceAfter=1*mm),
    }


# ── Page templates ────────────────────────────────────────────────────────────
def _cover_bg(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(white)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    # Top red band
    canvas.setFillColor(RED)
    canvas.rect(0, H - 3*cm, W, 3*cm, fill=1, stroke=0)
    # Bottom red band
    canvas.setFillColor(RED)
    canvas.rect(0, 0, W, 1.5*cm, fill=1, stroke=0)
    # "ARGUS" in white on red band
    canvas.setFont('Helvetica-Bold', 22)
    canvas.setFillColor(white)
    canvas.drawCentredString(W / 2, H - 1.8*cm, 'ARGUS')
    canvas.setFont('Helvetica', 9)
    canvas.drawCentredString(W / 2, H - 2.5*cm, 'AUTONOMOUS RECONNAISSANCE & GUIDED UNIFIED SCANNER')
    # Footer text
    canvas.setFont('Helvetica', 8)
    canvas.drawCentredString(W / 2, 0.55*cm, 'CONFIDENTIAL — FOR AUTHORISED PERSONNEL ONLY')
    canvas.restoreState()


def _body_header(canvas, doc):
    canvas.saveState()
    # Top bar
    canvas.setFillColor(RED)
    canvas.rect(0, H - 1.5*cm, W, 1.5*cm, fill=1, stroke=0)
    canvas.setFont('Helvetica-Bold', 9)
    canvas.setFillColor(white)
    canvas.drawString(1.5*cm, H - 0.95*cm, 'ARGUS')
    canvas.setFont('Helvetica', 8)
    title = getattr(doc, 'report_title', 'Security Assessment Report')
    canvas.drawCentredString(W / 2, H - 0.95*cm, title)
    canvas.drawRightString(W - 1.5*cm, H - 0.95*cm, f'Page {doc.page}')
    # Bottom rule
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(1.5*cm, 1.4*cm, W - 1.5*cm, 1.4*cm)
    canvas.setFont('Helvetica', 7)
    canvas.setFillColor(MID_GRAY)
    canvas.drawString(1.5*cm, 0.9*cm, 'CONFIDENTIAL — FOR AUTHORISED PERSONNEL ONLY')
    canvas.drawRightString(W - 1.5*cm, 0.9*cm,
        datetime.now(timezone.utc).strftime('%Y-%m-%d'))
    canvas.restoreState()


# ── Content builders ──────────────────────────────────────────────────────────
def _cover(engagement, S):
    scope_str = ' · '.join(engagement.scope[:6]) if engagement.scope else 'N/A'
    return [
        Spacer(1, 4*cm),
        Paragraph('ATTACK SURFACE ASSESSMENT REPORT', S['cover_sub']),
        Spacer(1, 8*mm),
        HRFlowable(width='60%', thickness=2, color=RED, hAlign='CENTER'),
        Spacer(1, 8*mm),
        Paragraph(_esc(engagement.name), S['cover_field']),
        Spacer(1, 4*mm),
        Paragraph(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            S['cover_meta']),
        Paragraph(f"Scope: {_esc(scope_str)}", S['cover_meta']),
        Spacer(1, 8*mm),
        HRFlowable(width='60%', thickness=1, color=BORDER, hAlign='CENTER'),
    ]


def _exec_summary(engagement, findings, targets, S):
    sev_counts = {}
    for f in findings:
        sev_counts[f.severity] = sev_counts.get(f.severity, 0) + 1

    risk = _risk_score(findings)
    risk_color = HexColor('#CC0000') if risk >= 60 else (
        HexColor('#AA7700') if risk >= 30 else HexColor('#227722'))

    elems = [Paragraph('Executive Summary', S['h1']),
             HRFlowable(width='100%', thickness=1, color=BORDER),
             Spacer(1, 3*mm)]

    # Risk score box
    risk_tbl = Table([
        [Paragraph('RISK SCORE', ParagraphStyle('rl', fontName='Helvetica-Bold',
            fontSize=8, textColor=MID_GRAY, alignment=TA_CENTER))],
        [Paragraph(
            f'<font size="32">{risk}</font>'
            f'<font size="10" color="#888888"> / 100</font>',
            ParagraphStyle('rv', fontName='Helvetica-Bold',
                textColor=risk_color, alignment=TA_CENTER, leading=40))],
    ], colWidths=[4*cm])
    risk_tbl.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, BORDER),
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))

    # Severity table
    sev_rows = [[
        Paragraph('Severity', ParagraphStyle('sh', fontName='Helvetica-Bold',
            fontSize=8, textColor=white)),
        Paragraph('Count', ParagraphStyle('sh', fontName='Helvetica-Bold',
            fontSize=8, textColor=white)),
        Paragraph('Risk Weight', ParagraphStyle('sh', fontName='Helvetica-Bold',
            fontSize=8, textColor=white)),
    ]]
    weights = {'critical': 10, 'high': 5, 'medium': 2, 'low': 1, 'info': 0}
    for sev in ('critical', 'high', 'medium', 'low', 'info'):
        cnt = sev_counts.get(sev, 0)
        w = weights[sev]
        sev_rows.append([
            Paragraph(sev.upper(), ParagraphStyle('sv', fontName='Helvetica-Bold',
                fontSize=9, textColor=SEV_COLOR[sev])),
            Paragraph(str(cnt), S['body']),
            Paragraph(f'+{w * cnt}', S['body']),
        ])
    sev_tbl = Table(sev_rows, colWidths=[4*cm, 3*cm, 4*cm])
    sev_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BG_WHITE, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))

    combined = Table([[risk_tbl, sev_tbl]], colWidths=[4.5*cm, 12*cm])
    combined.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
    ]))
    elems.append(combined)
    elems.append(Spacer(1, 5*mm))

    # Scope table
    elems.append(Paragraph('Scope & Coverage', S['h2']))
    scope_data = [
        [Paragraph('Engagement', S['label']),      Paragraph(_esc(engagement.name), S['body'])],
        [Paragraph('Scope Entries', S['label']),   Paragraph(_esc(', '.join(engagement.scope)) or 'N/A', S['body'])],
        [Paragraph('Targets Discovered', S['label']), Paragraph(str(len(targets)), S['body'])],
        [Paragraph('Total Findings', S['label']),  Paragraph(str(len(findings)), S['body'])],
        [Paragraph('Status', S['label']),          Paragraph(engagement.status.upper(), S['body'])],
    ]
    scope_tbl = Table(scope_data, colWidths=[5*cm, 11.5*cm])
    scope_tbl.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [BG_WHITE, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (0, -1), BG_LIGHT),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
    ]))
    elems.append(scope_tbl)
    return elems


def _findings_section(findings, S):
    sev_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4}
    sorted_f = sorted(findings, key=lambda f: sev_order.get(f.severity, 5))

    elems = [PageBreak(), Paragraph('Findings', S['h1']),
             HRFlowable(width='100%', thickness=1, color=BORDER),
             Spacer(1, 2*mm)]

    current_sev = None
    for i, f in enumerate(sorted_f, 1):
        if f.severity != current_sev:
            current_sev = f.severity
            elems.append(Spacer(1, 4*mm))
            elems.append(Paragraph(f.severity.upper(),
                ParagraphStyle('sh', fontName='Helvetica-Bold', fontSize=10,
                    textColor=SEV_COLOR.get(f.severity, MID_GRAY),
                    spaceBefore=2*mm, spaceAfter=2*mm,
                    borderPadding=(2, 6, 2, 6),
                    backColor=SEV_BG.get(f.severity, BG_LIGHT))))

        elems.append(KeepTogether(_finding_block(i, f, S)))
        elems.append(Spacer(1, 3*mm))

    return elems


def _finding_block(idx, f, S):
    sev_col = SEV_COLOR.get(f.severity, MID_GRAY)
    bg_col  = SEV_BG.get(f.severity, BG_WHITE)
    elems   = []

    # Header row: number | title | severity badge
    hdr = Table([[
        Paragraph(f'#{idx}', ParagraphStyle('fn', fontName='Helvetica-Bold',
            fontSize=9, textColor=MID_GRAY)),
        Paragraph(_esc(f.title) or '—', S['finding_title']),
        Paragraph(f.severity.upper(), ParagraphStyle('fs', fontName='Helvetica-Bold',
            fontSize=8, textColor=sev_col, alignment=TA_RIGHT)),
    ]], colWidths=[1*cm, 13.5*cm, 2*cm])
    hdr.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_col),
        ('LINEBELOW', (0, 0), (-1, -1), 1, sev_col),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elems.append(hdr)

    # Meta line (CVE / CVSS / MITRE)
    meta = []
    if f.cve_id:         meta.append(f'CVE: {f.cve_id}')
    if f.cvss_score:     meta.append(f'CVSS: {f.cvss_score:.1f}')
    if f.mitre_technique: meta.append(f'MITRE: {f.mitre_technique}')
    if meta:
        elems.append(Paragraph(_esc('  ·  '.join(meta)),
            ParagraphStyle('mt', fontName='Helvetica', fontSize=8,
                textColor=MID_GRAY, leftIndent=6, spaceBefore=2,
                spaceAfter=2)))

    # Description (skip if same as evidence output)
    ev = f.evidence or {}
    ev_output = str(ev.get('output', '')).strip()
    if f.description and f.description.strip() != ev_output:
        elems.append(Paragraph(_esc(f.description),
            ParagraphStyle('fd', fontName='Helvetica', fontSize=9,
                textColor=DARK_GRAY, leading=13, leftIndent=6,
                spaceAfter=2)))

    # Evidence box
    display_ev = {k: v for k, v in ev.items()
                  if k != 'nvd' and not isinstance(v, (dict, list))}
    if display_ev:
        ev_text = '  |  '.join(f'{k}: {v}' for k, v in list(display_ev.items())[:8])
        ev_para = Paragraph(_esc(ev_text),
            ParagraphStyle('ev', fontName='Courier', fontSize=7.5,
                textColor=DARK_GRAY, leading=11,
                backColor=BG_LIGHT, leftIndent=6,
                borderPadding=(3, 6, 3, 6),
                spaceAfter=1*mm))
        ev_tbl = Table([[ev_para]], colWidths=[16.5*cm])
        ev_tbl.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
            ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elems.append(ev_tbl)

    # Patch URLs
    patches = ev.get('nvd', {}).get('patch_urls', [])
    for url in patches[:3]:
        elems.append(Paragraph(f'Patch: {_esc(url)}',
            ParagraphStyle('pu', fontName='Courier', fontSize=7.5,
                textColor=HexColor('#0044AA'), leftIndent=6, spaceAfter=1)))

    return elems


def _phase_breakdown(findings, S):
    """Phase 2-4 breakdown: exploitation proof, OSINT intel, post-exploitation."""

    PHASE_TOOLS = {
        'exploitation':     {
            'nikto_scanner', 'sqlmap_scanner', 'git_exposure', 'dalfox_scanner', 'wpscan_lite',
        },
        'post_exploitation': {
            'testssl_scanner', 'hydra_brute', 'sensitive_files', 'header_analyzer', 'cors_tester',
        },
        'osint': {
            'crtsh_enum', 'shodan_lookup', 'github_dorking', 'whois_asn',
        },
    }

    def _source(f):
        return (f.evidence or {}).get('source', '')

    phase_findings = {
        'exploitation':     [f for f in findings if _source(f) in PHASE_TOOLS['exploitation'] or
                             (f.evidence or {}).get('poc_url')],
        'post_exploitation': [f for f in findings if _source(f) in PHASE_TOOLS['post_exploitation']],
        'osint':            [f for f in findings if _source(f) in PHASE_TOOLS['osint']],
    }

    if not any(phase_findings.values()):
        return []

    elems = [
        PageBreak(),
        Paragraph('Phase Analysis', S['h1']),
        HRFlowable(width='100%', thickness=1, color=BORDER),
        Spacer(1, 3*mm),
    ]

    # ── Phase 2: Exploitation ───────────────────────────────────────────────
    exp_f = phase_findings['exploitation']
    if exp_f:
        elems += [
            Paragraph('Phase 2 — Active Exploitation', S['h2']),
            Paragraph(
                f'{len(exp_f)} findings confirmed through active exploitation techniques '
                f'(web app scanning, SQLi testing, XSS fuzzing, git exposure, WordPress enumeration).',
                S['body']),
            Spacer(1, 2*mm),
        ]
        for f in exp_f:
            ev = f.evidence or {}
            proof   = ev.get('proof', '')
            poc_url = ev.get('poc_url', '')
            payload = ev.get('payload', '')
            src     = ev.get('source', '')

            block = [
                Paragraph(f'[{_esc(src.upper())}] {_esc(f.title)}',
                    ParagraphStyle('et', fontName='Helvetica-Bold', fontSize=9,
                        textColor=SEV_COLOR.get(f.severity, MID_GRAY), spaceAfter=1*mm)),
            ]
            if f.description:
                block.append(Paragraph(_esc(f.description),
                    ParagraphStyle('ed', fontName='Helvetica', fontSize=8,
                        textColor=DARK_GRAY, leading=12, leftIndent=6, spaceAfter=1*mm)))
            for label, val in [('PoC URL', poc_url), ('Payload', payload), ('Proof', proof[:400] if proof else '')]:
                if val:
                    block.append(Paragraph(f'<b>{_esc(label)}:</b>',
                        ParagraphStyle('el', fontName='Helvetica-Bold', fontSize=7.5,
                            textColor=MID_GRAY, leftIndent=6)))
                    block.append(Paragraph(_esc(val),
                        ParagraphStyle('ev2', fontName='Courier', fontSize=7.5,
                            textColor=HexColor('#AA0044'), leading=11,
                            backColor=HexColor('#FFF5FA'), leftIndent=6,
                            borderPadding=(2, 4, 2, 4), spaceAfter=1*mm)))
            elems.append(KeepTogether(block))
            elems.append(Spacer(1, 2*mm))

    # ── Phase 3: OSINT ──────────────────────────────────────────────────────
    osint_f = phase_findings['osint']
    if osint_f:
        elems += [
            Spacer(1, 4*mm),
            Paragraph('Phase 3 — OSINT & Passive Reconnaissance', S['h2']),
            Paragraph(
                f'{len(osint_f)} intelligence items gathered via passive OSINT techniques '
                f'(certificate transparency, Shodan, GitHub dorking, WHOIS/ASN).',
                S['body']),
            Spacer(1, 2*mm),
        ]
        osint_rows = [[
            Paragraph('Source',  ParagraphStyle('oh', fontName='Helvetica-Bold', fontSize=8, textColor=white)),
            Paragraph('Finding', ParagraphStyle('oh', fontName='Helvetica-Bold', fontSize=8, textColor=white)),
            Paragraph('Sev',     ParagraphStyle('oh', fontName='Helvetica-Bold', fontSize=8, textColor=white)),
        ]]
        for f in osint_f:
            ev  = f.evidence or {}
            src = ev.get('source', '?')
            osint_rows.append([
                Paragraph(_esc(src), ParagraphStyle('os', fontName='Helvetica', fontSize=8, textColor=MID_GRAY)),
                Paragraph(_esc(f.title[:90]), ParagraphStyle('ot', fontName='Helvetica', fontSize=8, textColor=DARK_GRAY)),
                Paragraph(f.severity.upper(), ParagraphStyle('osv', fontName='Helvetica-Bold',
                    fontSize=8, textColor=SEV_COLOR.get(f.severity, MID_GRAY))),
            ])
        osint_tbl = Table(osint_rows, colWidths=[3.5*cm, 11.5*cm, 1.5*cm])
        osint_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), DARK_GRAY),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BG_WHITE, BG_LIGHT]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ]))
        elems.append(osint_tbl)

    # ── Phase 4: Post-Exploitation ──────────────────────────────────────────
    post_f = phase_findings['post_exploitation']
    if post_f:
        elems += [
            Spacer(1, 4*mm),
            Paragraph('Phase 4 — Post-Exploitation Analysis', S['h2']),
            Paragraph(
                f'{len(post_f)} post-exploitation findings across TLS configuration, '
                f'HTTP security headers, CORS policy, sensitive file exposure, and credential attacks.',
                S['body']),
            Spacer(1, 2*mm),
        ]

        # Group by source
        by_source: Dict[str, list] = {}
        for f in post_f:
            src = (f.evidence or {}).get('source', 'unknown')
            by_source.setdefault(src, []).append(f)

        PHASE4_LABELS = {
            'testssl':       'TLS / SSL Configuration',
            'testssl_scanner': 'TLS / SSL Configuration',
            'header_analyzer': 'HTTP Security Headers',
            'cors_tester':   'CORS Policy Violations',
            'sensitive_files': 'Sensitive File Exposure',
            'hydra_brute':   'Credential Brute-Force',
        }
        for src, src_findings in by_source.items():
            src_label = PHASE4_LABELS.get(src, src.replace('_', ' ').title())
            elems.append(Paragraph(_esc(src_label),
                ParagraphStyle('p4h', fontName='Helvetica-Bold', fontSize=10,
                    textColor=HexColor('#9944FF'), spaceBefore=3*mm, spaceAfter=1*mm)))
            for f in src_findings:
                ev = f.evidence or {}
                details = []
                for k in ('url', 'header', 'issue', 'origin', 'path', 'credential', 'protocol'):
                    if ev.get(k):
                        details.append(f'{k}: {ev[k]}')
                detail_str = '  |  '.join(details[:5]) if details else ''
                block = [
                    Paragraph(
                        f'• {_esc(f.severity.upper())}  {_esc(f.title)}',
                        ParagraphStyle('p4t', fontName='Helvetica-Bold', fontSize=9,
                            textColor=SEV_COLOR.get(f.severity, MID_GRAY), spaceAfter=1)),
                ]
                if f.description:
                    block.append(Paragraph(_esc(f.description[:300]),
                        ParagraphStyle('p4d', fontName='Helvetica', fontSize=8,
                            textColor=DARK_GRAY, leading=12, leftIndent=8, spaceAfter=1)))
                if detail_str:
                    block.append(Paragraph(_esc(detail_str),
                        ParagraphStyle('p4e', fontName='Courier', fontSize=7.5,
                            textColor=DARK_GRAY, backColor=BG_LIGHT, leftIndent=8,
                            borderPadding=(2, 4, 2, 4), spaceAfter=1*mm)))
                elems.append(KeepTogether(block))

    return elems


def _mitre_section(findings, S):
    techniques: Dict[str, List] = {}
    for f in findings:
        if f.mitre_technique:
            techniques.setdefault(f.mitre_technique, []).append(f.title)
    if not techniques:
        return []

    elems = [Spacer(1, 6*mm),
             Paragraph('MITRE ATT&CK Summary', S['h1']),
             HRFlowable(width='100%', thickness=1, color=BORDER),
             Spacer(1, 3*mm)]

    rows = [[
        Paragraph('Technique', ParagraphStyle('th', fontName='Helvetica-Bold',
            fontSize=8, textColor=white)),
        Paragraph('Findings', ParagraphStyle('th', fontName='Helvetica-Bold',
            fontSize=8, textColor=white)),
        Paragraph('Count', ParagraphStyle('th', fontName='Helvetica-Bold',
            fontSize=8, textColor=white)),
    ]]
    try:
        from backend.services.mitre import TECHNIQUES
    except Exception:
        TECHNIQUES = {}

    for tech, titles in sorted(techniques.items()):
        preview = ', '.join(titles[:3]) + ('…' if len(titles) > 3 else '')
        meta = TECHNIQUES.get(tech, {})
        tech_cell = f'<b>{_esc(tech)}</b>'
        if meta.get('name'):
            tech_cell += f'<br/><font size="6.5" color="#888888">{_esc(meta["name"])}</font>'
        rows.append([
            Paragraph(tech_cell, ParagraphStyle('tc', fontName='Helvetica',
                fontSize=9, textColor=RED, leading=11)),
            Paragraph(_esc(preview), S['body']),
            Paragraph(str(len(titles)), S['body']),
        ])
    tbl = Table(rows, colWidths=[3*cm, 12*cm, 1.5*cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_GRAY),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BG_WHITE, BG_LIGHT]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elems.append(tbl)
    return elems


def _attack_paths_section(paths: List[Dict], S):
    if not paths:
        return []

    elems = [
        PageBreak(),
        Paragraph('Attack Paths', S['h1']),
        HRFlowable(width='100%', thickness=1, color=BORDER),
        Spacer(1, 3*mm),
        Paragraph(
            'Ranked exploitation routes from external entry points to high-value '
            '("crown jewel") assets, weighted by exploitability. The highest-scoring path '
            'represents the most direct route to critical impact and should be prioritised for '
            'remediation.',
            S['body']),
        Spacer(1, 3*mm),
    ]

    for i, p in enumerate(paths, 1):
        sev = p.get('severity', 'low')
        col = SEV_COLOR.get(sev, MID_GRAY)
        bg  = SEV_BG.get(sev, BG_LIGHT)
        target = p.get('target', {})

        hdr = Table([[
            Paragraph(f'#{i}', ParagraphStyle('apn', fontName='Helvetica-Bold',
                fontSize=9, textColor=MID_GRAY)),
            Paragraph(_esc(target.get('label', '')), ParagraphStyle('apt',
                fontName='Helvetica-Bold', fontSize=10, textColor=BLACK)),
            Paragraph(f'SCORE {p.get("score", 0)}', ParagraphStyle('aps',
                fontName='Helvetica-Bold', fontSize=9, textColor=col, alignment=TA_RIGHT)),
        ]], colWidths=[1*cm, 13.5*cm, 2*cm])
        hdr.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg),
            ('LINEBELOW', (0, 0), (-1, -1), 1, col),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        meta = (f'Target: {_esc(target.get("reason", ""))}  ·  '
                f'Exploitability: {int(p.get("exploitability", 0) * 100)}%  ·  '
                f'{_esc(sev.upper())}')
        block = [
            hdr,
            Paragraph(meta, ParagraphStyle('apm', fontName='Helvetica', fontSize=8,
                textColor=MID_GRAY, leftIndent=6, spaceBefore=2, spaceAfter=2)),
            Paragraph(_esc(p.get('rationale', '')), ParagraphStyle('apr',
                fontName='Courier', fontSize=8, textColor=DARK_GRAY, leading=12,
                backColor=BG_LIGHT, leftIndent=6, borderPadding=(3, 6, 3, 6),
                spaceAfter=1*mm)),
        ]
        elems.append(KeepTogether(block))
        elems.append(Spacer(1, 3*mm))

    return elems


def _narrative_section(nar: Optional[Dict], S):
    if not nar:
        return []

    elems = [
        PageBreak(),
        Paragraph('Attack Narrative', S['h1']),
        HRFlowable(width='100%', thickness=1, color=BORDER),
        Spacer(1, 3*mm),
    ]

    rating = nar.get('risk_rating')
    if rating:
        rc = RATING_HEX.get(str(rating).title(), '#666666')
        elems.append(Paragraph(
            f'Overall Risk Rating: <b><font color="{rc}">{_esc(str(rating).upper())}</font></b>',
            S['body']))
        elems.append(Spacer(1, 2*mm))

    if nar.get('executive_summary'):
        elems.append(Paragraph('Executive Summary', S['h2']))
        elems.append(Paragraph(_esc(nar['executive_summary']), S['body']))

    chain = nar.get('attack_chain') or []
    if chain:
        elems.append(Paragraph('Attack Chain', S['h2']))
        for j, step in enumerate(chain, 1):
            num  = step.get('step', j)
            head = f'Step {num} — <b>{_esc(step.get("title", ""))}</b>'
            if step.get('technique'):
                head += f'  <font color="#CC1111">[{_esc(step["technique"])}]</font>'
            if step.get('asset'):
                head += f'  <font color="#666666">{_esc(step["asset"])}</font>'
            block = [Paragraph(head, ParagraphStyle('ncs', fontName='Helvetica',
                fontSize=9, textColor=BLACK, leading=13, spaceBefore=1*mm, spaceAfter=1))]
            if step.get('detail'):
                block.append(Paragraph(_esc(step['detail']), ParagraphStyle('ncd',
                    fontName='Helvetica', fontSize=8, textColor=DARK_GRAY, leading=12,
                    leftIndent=8, spaceAfter=1*mm)))
            elems.append(KeepTogether(block))

    kf = nar.get('key_findings') or []
    if kf:
        elems.append(Spacer(1, 2*mm))
        elems.append(Paragraph('Key Findings', S['h2']))
        for f in kf:
            sev = str(f.get('severity', 'info')).lower()
            hexc = SEV_HEX.get(sev, '#666666')
            line = (f'• <font color="{hexc}"><b>{_esc(sev.upper())}</b></font>  '
                    f'{_esc(f.get("title", ""))}')
            block = [Paragraph(line, ParagraphStyle('nkf', fontName='Helvetica',
                fontSize=9, textColor=BLACK, leading=13, spaceAfter=1))]
            if f.get('impact'):
                block.append(Paragraph(_esc(f['impact']), ParagraphStyle('nki',
                    fontName='Helvetica', fontSize=8, textColor=DARK_GRAY, leading=12,
                    leftIndent=10, spaceAfter=1*mm)))
            elems.append(KeepTogether(block))

    recs = nar.get('recommendations') or []
    if recs:
        elems.append(Spacer(1, 2*mm))
        elems.append(Paragraph('Recommendations', S['h2']))
        for k, r in enumerate(recs, 1):
            elems.append(Paragraph(f'{k}. {_esc(r)}', ParagraphStyle('nrc',
                fontName='Helvetica', fontSize=9, textColor=DARK_GRAY, leading=13,
                leftIndent=6, spaceAfter=1)))

    if nar.get('narrative'):
        elems.append(Spacer(1, 3*mm))
        elems.append(Paragraph('Engagement Narrative', S['h2']))
        for para in str(nar['narrative']).split('\n'):
            if para.strip():
                elems.append(Paragraph(_esc(para.strip()), S['body']))

    elems.append(Spacer(1, 3*mm))
    elems.append(Paragraph(
        f'Generated by {_esc(nar.get("model", "LLM"))} — AI-assisted analysis; '
        f'verify before client delivery.',
        ParagraphStyle('nnote', fontName='Helvetica-Oblique', fontSize=7.5,
            textColor=LIGHT_GRAY)))

    return elems


def _risk_score(findings) -> int:
    w   = {'critical': 10, 'high': 5, 'medium': 2, 'low': 1, 'info': 0}
    cap = {'critical': 40, 'high': 25, 'medium': 20, 'low': 10, 'info': 0}
    buckets: Dict[str, int] = {}
    for f in findings:
        buckets[f.severity] = buckets.get(f.severity, 0) + w.get(f.severity, 0)
    raw = sum(min(v, cap.get(sev, 0)) for sev, v in buckets.items())
    return min(100, int(raw * 100 / 95))


# ── Public API ────────────────────────────────────────────────────────────────
def generate_pdf(engagement, findings: list, targets: list,
                 attack_paths: Optional[List[Dict]] = None,
                 narrative: Optional[Dict] = None) -> bytes:
    buf = BytesIO()
    S = _styles()

    class ArgusDoc(BaseDocTemplate):
        report_title: str = ''

    doc = ArgusDoc(buf, pagesize=A4,
                   leftMargin=1.5*cm, rightMargin=1.5*cm,
                   topMargin=2*cm, bottomMargin=2*cm)
    doc.report_title = f'{engagement.name} — Security Assessment'

    cover_frame = Frame(0, 1.5*cm, W, H - 4.5*cm,
                        leftPadding=2*cm, rightPadding=2*cm,
                        topPadding=0, bottomPadding=0)
    body_frame  = Frame(1.5*cm, 2*cm, W - 3*cm, H - 4*cm,
                        leftPadding=0, rightPadding=0,
                        topPadding=0, bottomPadding=0)

    cover_tpl = PageTemplate(id='Cover', frames=[cover_frame], onPage=_cover_bg)
    body_tpl  = PageTemplate(id='Body',  frames=[body_frame],  onPage=_body_header)
    doc.addPageTemplates([cover_tpl, body_tpl])

    story = _cover(engagement, S)
    story.append(PageBreak())
    story += _exec_summary(engagement, findings, targets, S)
    story += _narrative_section(narrative, S)
    story += _attack_paths_section(attack_paths or [], S)
    story += _findings_section(findings, S)
    story += _phase_breakdown(findings, S)
    story += _mitre_section(findings, S)

    doc.build(story)
    return buf.getvalue()
