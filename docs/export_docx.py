"""Gộp các tài liệu lý thuyết (.md) thành một file Word (.docx).

- Render các sơ đồ Mermaid ra PNG bằng mermaid-cli (mmdc) nếu có; nếu không,
  nhúng mã Mermaid dưới dạng khối văn bản.
- Hỗ trợ: tiêu đề, đoạn, danh sách, trích dẫn, bảng, khối mã, định dạng inline
  (**đậm**, `mã`, [chữ](link)).

Chạy:
    python docs/export_docx.py                       # xuất docs/Bao_cao_Attack_Defense.docx
    python docs/export_docx.py --no-mermaid          # không render ảnh, nhúng mã Mermaid
    python docs/export_docx.py --out duong_dan.docx
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

DOCS = Path(__file__).resolve().parent
ORDER = [
    'README.md',
    '01-the-le-luat-choi.md',
    '02-mo-hinh-cuoc-thi.md',
    '03-kich-ban-idor.md',
    '04-mo-phong-hai-doi.md',
    '05-so-do.md',
    '06-vai-tro-he-thong.md',
]

INLINE = re.compile(r'(\*\*.+?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))')


def add_inline(paragraph, text):
    """Thêm văn bản có định dạng inline vào một đoạn."""
    for part in INLINE.split(text):
        if not part:
            continue
        if part.startswith('**') and part.endswith('**'):
            paragraph.add_run(part[2:-2]).bold = True
        elif part.startswith('`') and part.endswith('`'):
            run = paragraph.add_run(part[1:-1])
            run.font.name = 'Consolas'
        elif part.startswith('[') and '](' in part:
            label = part[1:part.index(']')]
            paragraph.add_run(label)
        else:
            paragraph.add_run(part)


def find_mmdc():
    for name in ('mmdc', 'mmdc.cmd'):
        if shutil.which(name):
            return [shutil.which(name)]
    if shutil.which('npx'):
        return ['npx', '-y', '@mermaid-js/mermaid-cli']
    return None


def render_mermaid(code, out_png, mmdc):
    with tempfile.NamedTemporaryFile('w', suffix='.mmd', delete=False, encoding='utf-8') as f:
        f.write(code)
        src = f.name
    try:
        subprocess.run(mmdc + ['-i', src, '-o', str(out_png), '-b', 'white', '-s', '2'],
                       check=True, capture_output=True, timeout=300)
        return out_png.exists()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        sys.stderr.write(f'  [cảnh báo] không render được 1 sơ đồ: {exc}\n')
        return False
    finally:
        Path(src).unlink(missing_ok=True)


def add_table(doc, rows):
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    cells = [r for r in cells if not all(set(c) <= set('-: ') for c in r)]
    if not cells:
        return
    ncol = max(len(r) for r in cells)
    table = doc.add_table(rows=0, cols=ncol)
    table.style = 'Light Grid Accent 1'
    for i, row in enumerate(cells):
        tr = table.add_row().cells
        for j in range(ncol):
            tr[j].text = ''
            p = tr[j].paragraphs[0]
            add_inline(p, row[j] if j < len(row) else '')
            if i == 0:
                for run in p.runs:
                    run.bold = True


def convert(doc, md_text, mmdc, img_dir, counter):
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Khối mã / mermaid
        if line.strip().startswith('```'):
            lang = line.strip()[3:].strip()
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                block.append(lines[i])
                i += 1
            i += 1
            code = '\n'.join(block)
            if lang == 'mermaid' and mmdc:
                counter[0] += 1
                png = img_dir / f'diagram_{counter[0]}.png'
                if render_mermaid(code, png, mmdc):
                    doc.add_picture(str(png), width=Inches(6.2))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                    continue
            cap = doc.add_paragraph()
            if lang == 'mermaid':
                cap.add_run('[Sơ đồ Mermaid]').italic = True
            for cl in block:
                run = doc.add_paragraph(cl).runs[0] if cl else doc.add_paragraph().add_run('')
                run.font.name = 'Consolas'
                run.font.size = Pt(9)
            continue
        # Bảng
        if line.strip().startswith('|') and i + 1 < len(lines) and set(lines[i + 1].strip()) <= set('|-: '):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append(lines[i])
                i += 1
            add_table(doc, rows)
            continue
        # Tiêu đề
        m = re.match(r'(#{1,6})\s+(.*)', line)
        if m:
            level = len(m.group(1))
            doc.add_heading(re.sub(r'[*`]', '', m.group(2)), level=min(level, 4))
            i += 1
            continue
        # Trích dẫn
        if line.strip().startswith('>'):
            p = doc.add_paragraph()
            run_text = line.strip()[1:].strip()
            add_inline(p, run_text)
            for r in p.runs:
                r.italic = True
            i += 1
            continue
        # Danh sách
        mb = re.match(r'\s*[-*]\s+(.*)', line)
        mo = re.match(r'\s*\d+\.\s+(.*)', line)
        if mb:
            add_inline(doc.add_paragraph(style='List Bullet'), mb.group(1))
            i += 1
            continue
        if mo:
            add_inline(doc.add_paragraph(style='List Number'), mo.group(1))
            i += 1
            continue
        # Đoạn thường / dòng trống
        if line.strip():
            add_inline(doc.add_paragraph(), line)
        i += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(DOCS / 'Bao_cao_Attack_Defense.docx'))
    ap.add_argument('--no-mermaid', action='store_true', help='không render ảnh, nhúng mã Mermaid')
    args = ap.parse_args()

    mmdc = None if args.no_mermaid else find_mmdc()
    if not args.no_mermaid and not mmdc:
        sys.stderr.write('[cảnh báo] không tìm thấy mmdc/npx — nhúng mã Mermaid dạng văn bản.\n')

    doc = Document()
    doc.styles['Normal'].font.name = 'Calibri'
    doc.styles['Normal'].font.size = Pt(11)

    title = doc.add_heading('Thiết kế cuộc thi Attack–Defense', level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph('Challenge ServiceDesk – IDOR · Tài liệu lý thuyết')
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in sub.runs:
        r.italic = True
        r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    counter = [0]
    with tempfile.TemporaryDirectory() as tmp:
        img_dir = Path(tmp)
        for idx, name in enumerate(ORDER):
            path = DOCS / name
            if not path.exists():
                continue
            if idx:
                doc.add_page_break()
            convert(doc, path.read_text(encoding='utf-8'), mmdc, img_dir, counter)

    out = Path(args.out)
    doc.save(out)
    print(f'Đã xuất: {out}  ({counter[0]} sơ đồ render thành ảnh)')


if __name__ == '__main__':
    main()
