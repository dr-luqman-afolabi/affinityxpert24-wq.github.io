"""Conservative module catalogue extraction from UoK curriculum DOCX tables.

Output is a REVIEW DRAFT, not an approved academic catalogue. No guessed credits.
"""
import csv
import re
from pathlib import Path
from docx import Document

CODE = re.compile(r'^[A-Z]{2,6}\s*[-/]?\s*\d{4,8}[A-Z]?$', re.I)

def extract_catalogue(path, programme, version):
    doc = Document(path)
    entries = {}
    for table_no, table in enumerate(doc.tables):
        rows = table.rows
        for i, row in enumerate(rows):
            cells = [c.text.replace('\xa0', ' ').strip() for c in row.cells]
            if len(cells) < 2 or 'module code' not in cells[0].lower() or not any(k in cells[1].lower() for k in ('module title','module name')):
                continue
            year = ''; period = ''
            for next_row in rows[i+1:]:
                v = [re.sub(r'\s+', ' ', c.text.replace('\xa0',' ')).strip() for c in next_row.cells]
                if len(v)<2: continue
                label = v[1].upper()
                year_match = re.search(r'YEAR\s*(\d)', label)
                period_match = re.search(r'(TRIMESTER|SEMESTER)\s*(\d)',label)
                if year_match: year=year_match.group(1)
                if period_match: period=f'{period_match.group(1).title()} {period_match.group(2)}'
                code = re.sub(r'\s+', '',v[0]).upper()
                if CODE.fullmatch(code) and len(v[1])>2 and len(v[1])<200:
                    title = v[1].strip(' .')
                    if code not in entries:
                        entries[code]={'programme':programme,'version':version,'module_code':code,'module_title':title,'year':year,'period':period,'credits':'','source_file':Path(path).name,'source_table':table_no,'review_status':'needs_review'}
    return list(entries.values())

def write_catalogue(path, rows):
    fields=['programme','version','module_code','module_title','year','period','credits','source_file','source_table','review_status']
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
