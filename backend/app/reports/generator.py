import io
import re
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.database import db
from app.rag.openai_client import ai_client
from dateutil import parser
import math

def strip_markdown(text: str) -> str:
    """Remove markdown and LaTeX from LLM response."""
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'\\\[[\s\S]*?\\\]', '', text)
    text = re.sub(r'\\\([\s\S]*?\\\)', '', text)
    text = re.sub(r'\\text\{([^}]*)\}', r'\1', text)
    text = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', r'(\1/\2)', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text)
    text = re.sub(r'\{([^}]*)\}', r'\1', text)
    text = re.sub(r'^[-_]{3,}$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def create_plot(title, timestamps, lines, y_label):
    """Creates a matplotlib plot and returns it as an Image platypus object."""
    fig, ax = plt.subplots(figsize=(7, 3.5))
    
    for line in lines:
        ax.plot(timestamps, line['data'], label=line['name'], color=line['color'], 
                linestyle=line.get('linestyle', '-'), linewidth=1.5)

    ax.set_title(title, fontsize=12, fontweight='bold', color='#1f2937')
    ax.set_ylabel(y_label, fontsize=10, color='#4b5563')
    
    # Format x-axis as time
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.xticks(rotation=45, ha='right', fontsize=8, color='#6b7280')
    plt.yticks(fontsize=8, color='#6b7280')
    
    ax.grid(True, linestyle='--', alpha=0.5, color='#e5e7eb')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#d1d5db')
    ax.spines['bottom'].set_color('#d1d5db')
    
    # Place legend outside below the plot
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=4, frameon=False, fontsize=9)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    
    return Image(buf, width=420, height=210)

async def generate_pdf_report(machine_id: str, start_time: str, end_time: str) -> io.BytesIO:
    # 1. Fetch data
    # Parse dates safely
    try:
        if start_time.endswith('Z'):
            dt_start = parser.parse(start_time)
        else:
            dt_start = parser.parse(start_time + 'Z')
        if end_time.endswith('Z'):
            dt_end = parser.parse(end_time)
        else:
            dt_end = parser.parse(end_time + 'Z')
    except Exception:
        # fallback
        dt_start = datetime.utcnow()
        dt_end = datetime.utcnow()
        
    start_str = dt_start.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_str = dt_end.strftime("%Y-%m-%dT%H:%M:%S.000Z")
    
    # total duration in hours
    total_hours = (dt_end - dt_start).total_seconds() / 3600.0
    if total_hours < 0:
        total_hours = 0
        
    features = db.get_features(machine_id, minutes=10080, start_time=start_str, end_time=end_str)
    motor_config = db.get_motor_config(machine_id) or {}
    
    # 2. Process data & calculate stats
    timestamps = []
    i1, i2, i3, i_avg = [], [], [], []
    kw1, kw2, kw3, p_total = [], [], [], []
    
    run_ms = 0
    avg_v, avg_i, avg_pf, avg_p, max_p, min_pf = 0, 0, 0, 0, 0, 1.0
    energy_kwh = 0
    
    if features:
        # Sort ascending by time
        features.sort(key=lambda x: parser.parse(x['timestamp'].replace('Z', '+00:00')))
        
        sum_v, sum_i, sum_pf, sum_p = 0, 0, 0, 0
        count = len(features)
        
        operational_blocks = []
        current_block_start = None
        current_block_end = None
        
        for i, f in enumerate(features):
            fd = f.get('feature_data', {})
            el = fd.get('electrical', {})
            
            ts = parser.parse(f['timestamp'].replace('Z', '+00:00'))
            timestamps.append(ts)
            
            i1.append(el.get('i1', 0))
            i2.append(el.get('i2', 0))
            i3.append(el.get('i3', 0))
            i_avg.append(el.get('i_avg', el.get('current', 0)))
            
            kw1.append(el.get('kw1', 0))
            kw2.append(el.get('kw2', 0))
            kw3.append(el.get('kw3', 0))
            p_val = el.get('t_kw', el.get('active_power', 0))
            p_total.append(p_val)
            
            v = (el.get('v12', 0) + el.get('v23', 0) + el.get('v31', 0)) / 3
            if v == 0: v = el.get('voltage', 0)
            
            pf_val = el.get('pf_avg', el.get('power_factor', 0))
            
            sum_v += v
            sum_i += i_avg[-1]
            sum_pf += pf_val
            sum_p += p_val
            
            if p_val > max_p: max_p = p_val
            if pf_val > 0 and pf_val < min_pf: min_pf = pf_val
            
            # Run time calculation: motor is running if power > 0.5 kW
            if i > 0:
                prev_p = p_total[-2]
                curr_p = p_val
                if prev_p > 0.5 or curr_p > 0.5:
                    dt = (ts - timestamps[-2]).total_seconds()
                    if 0 < dt < 86400: # max 1 day gap
                        run_ms += dt * 1000
                        energy_kwh += (curr_p * dt) / 3600.0
                        
            # Track operational blocks
            if p_val > 0.5:
                if current_block_start is None:
                    current_block_start = ts
                current_block_end = ts
            else:
                if current_block_start is not None:
                    duration = (current_block_end - current_block_start).total_seconds() / 3600.0
                    if duration > 0.05: # ignore micro bursts < 3 minutes
                        operational_blocks.append((current_block_start, current_block_end, duration))
                    current_block_start = None
        
        if current_block_start is not None:
            duration = (current_block_end - current_block_start).total_seconds() / 3600.0
            if duration > 0.05:
                operational_blocks.append((current_block_start, current_block_end, duration))
        
        if count > 0:
            avg_v = sum_v / count
            avg_i = sum_i / count
            avg_pf = sum_pf / count
            avg_p = sum_p / count
            
    run_hours = run_ms / 3600000.0
    uptime_pct = (run_hours / total_hours * 100) if total_hours > 0 else 0
    
    # 3. Request LLM Summary
    motor_info = "\n".join([f"{k}: {v}" for k,v in motor_config.items()]) if motor_config else "No config available."
    
    blocks_str = "No significant operational blocks detected."
    if 'operational_blocks' in locals() and operational_blocks:
        lines = []
        for start, end, dur in operational_blocks[-30:]: # Last 30 shifts
            lines.append(f"- {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%H:%M')} ({dur:.2f} hours)")
        if len(operational_blocks) > 30:
            lines.insert(0, f"(Showing last 30 out of {len(operational_blocks)} shifts)")
        blocks_str = "\n".join(lines)
    
    data_summary = f"""
ACTUAL MEASURED DATA FOR THIS REPORT:
Time Range: {start_str} to {end_str}
Duration: {total_hours:.1f} hours
Samples: {len(features)}

Motor Configuration:
{motor_info}

Operational Schedule (Recent Shifts):
{blocks_str}

Period Statistics:
- Average Voltage (L-L): {avg_v:.1f} V
- Average Current: {avg_i:.2f} A
- Average Active Power: {avg_p:.2f} kW
- Maximum Active Power: {max_p:.2f} kW
- Average Power Factor: {avg_pf:.3f}
- Minimum Power Factor: {min_pf:.3f}
- Total Energy Consumed: {energy_kwh:.1f} kWh
- Run Time: {run_hours:.2f} hours out of {total_hours:.2f} hours total
- Uptime Percentage: {uptime_pct:.1f}%

CRITICAL INSTRUCTIONS FOR FORMATTING:
- DO NOT use any markdown formatting (no #, ##, **, *, `, etc.)
- DO NOT use LaTeX formulas or math notation
- Use PLAIN TEXT ONLY with clear section headings in plain English
- Use simple bullet points with a dash (-) character
- Structure the report with these sections:
  1. Loading Conditions and Duty Cycle Analysis
  2. Power Factor and Voltage Analysis
  3. Efficiency Analysis
  4. Key Findings and Recommendations
- Use the ACTUAL DATA provided above. DO NOT say data is unavailable. The run time is {run_hours:.2f} hours, so if it is >0, the motor HAS been operational.
- When analyzing Duty Cycle, evaluate it on a daily/shift basis. For example, if a motor runs for a block of hours (e.g. 6 hours out of 24), this likely indicates an S1 duty cycle (continuous operation) during scheduled shifts, rather than a "low duty cycle" or "frequent disengagement". Interpret the uptime percentage through the lens of daily operational shifts.
"""
    
    try:
        # Use our ai_client's chat method
        # Mocking the request/state handling normally done in routes
        ai_response = await ai_client.chat(
            user_message=data_summary,
            machine_id=machine_id,
            history=[]
        )
    except Exception as e:
        ai_response = f"Failed to generate AI summary: {e}"
        
    cleaned_summary = strip_markdown(ai_response)
    
    # 4. Assemble PDF
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#0891b2'),
        spaceAfter=12
    )
    subtitle_style = ParagraphStyle(
        'SubTitleStyle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#4b5563'),
        spaceAfter=20
    )
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#0891b2'),
        spaceBefore=15,
        spaceAfter=10
    )
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=6,
        leading=14
    )
    
    elements = []
    
    # Header
    elements.append(Paragraph(f"Motor Diagnostics Report: {machine_id}", title_style))
    elements.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC", subtitle_style))
    elements.append(Paragraph(f"Period: {dt_start.strftime('%Y-%m-%d %H:%M')} to {dt_end.strftime('%Y-%m-%d %H:%M')}", subtitle_style))
    
    # Motor Details & Period Summary Tables
    elements.append(Paragraph("Asset Configuration & Period Summary", section_style))
    
    table_data = [
        ['Motor Type', motor_config.get('motorType', 'N/A'), 'Run Time', f"{run_hours:.1f} / {total_hours:.1f} hrs"],
        ['Rated Power', f"{motor_config.get('ratedPower', 'N/A')} kW", 'Energy', f"{energy_kwh:.1f} kWh"],
        ['Rated η', f"{motor_config.get('ratedEfficiency', 'N/A')}%", 'Avg Power', f"{avg_p:.2f} kW"],
        ['Rated Current', f"{motor_config.get('ratedCurrent', 'N/A')} A", 'Max Power', f"{max_p:.2f} kW"],
        ['Location', motor_config.get('location', 'N/A'), 'Avg PF', f"{avg_pf:.3f}"],
    ]
    
    t = Table(table_data, colWidths=[100, 130, 100, 130])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.white),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#6b7280')),
        ('TEXTCOLOR', (2,0), (2,-1), colors.HexColor('#6b7280')),
        ('TEXTCOLOR', (1,0), (1,-1), colors.HexColor('#111827')),
        ('TEXTCOLOR', (3,0), (3,-1), colors.HexColor('#111827')),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica-Bold'),
        ('FONTNAME', (3,0), (3,-1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#f3f4f6')),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    
    # Plots
    if len(timestamps) > 0:
        elements.append(Paragraph("Performance Charts", section_style))
        
        current_lines = [
            {'name': 'L1', 'data': i1, 'color': '#ef4444', 'linestyle': '--'},
            {'name': 'L2', 'data': i2, 'color': '#f59e0b', 'linestyle': '--'},
            {'name': 'L3', 'data': i3, 'color': '#3b82f6', 'linestyle': '--'},
            {'name': 'Avg', 'data': i_avg, 'color': '#0891b2', 'linestyle': '-'}
        ]
        img_current = create_plot("Current Profile", timestamps, current_lines, "Current (A)")
        elements.append(img_current)
        elements.append(Spacer(1, 10))
        
        power_lines = [
            {'name': 'L1', 'data': kw1, 'color': '#ef4444', 'linestyle': '--'},
            {'name': 'L2', 'data': kw2, 'color': '#f59e0b', 'linestyle': '--'},
            {'name': 'L3', 'data': kw3, 'color': '#3b82f6', 'linestyle': '--'},
            {'name': 'Total', 'data': p_total, 'color': '#10b981', 'linestyle': '-'}
        ]
        img_power = create_plot("Active Power Profile", timestamps, power_lines, "Power (kW)")
        elements.append(img_power)
        elements.append(Spacer(1, 20))
    
    # AI Summary
    elements.append(Paragraph("AI Diagnostic Analysis", section_style))
    for paragraph in cleaned_summary.split('\n'):
        if paragraph.strip():
            # Check for section headers
            if re.match(r'^[A-Z0-9].*:$', paragraph.strip()) or re.match(r'^\d+\.\s+[A-Z]', paragraph.strip()):
                elements.append(Spacer(1, 10))
                elements.append(Paragraph(paragraph.strip(), ParagraphStyle(
                    'Header', parent=styles['Heading3'], fontSize=11, textColor=colors.HexColor('#0891b2')
                )))
            else:
                elements.append(Paragraph(paragraph.strip(), body_style))
    
    doc.build(elements)
    buf.seek(0)
    
    return buf
