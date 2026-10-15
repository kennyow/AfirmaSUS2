import io
import re
import textwrap
import unicodedata
import zipfile
from xml.sax.saxutils import escape


FORMAT_EXTENSIONS = {
    'pdf': '.pdf',
    'docx': '.docx',
    'xlsx': '.xlsx',
}


def _clean(value):
    return str(value or '').strip()


def _date(value):
    return value.strftime('%d/%m/%Y') if value else '—'


def _ata_lines(ata):
    content = ata.conteudo
    participantes = content['participantes']
    assuntos = content['assuntos']
    decisoes = content['decisoes']
    pendencias = content['pendencias']
    encerramento = content['encerramento']

    lines = [
        ('Ata de reunião', True),
        (_clean(ata.titulo) or 'Ata sem título', True),
        (f"Data: {_date(ata.data)} · Horário: {ata.horario.strftime('%H:%M') if ata.horario else '—'}", False),
        ('1. Informações Gerais', True),
        (f"Local / Plataforma: {_clean(ata.local) or '—'}", False),
        (f"Coordenador geral: {_clean(ata.coordenador) or '—'}", False),
        (f"Responsável pela ata: {_clean(ata.responsavel) or '—'}", False),
        ('2. Tema da Reunião', True),
        (f"Título principal: {_clean(ata.titulo) or '—'}", False),
        ('3. Participantes', True),
        ('Presentes: ' + (', '.join(participantes['presentes']) or '—'), False),
        ('Ausentes: ' + (', '.join(participantes['ausentes']) or '—'), False),
        ('4. Assuntos Discutidos', True),
    ]
    for index, assunto in enumerate(assuntos['itens'], 1):
        if assunto['titulo'] or assunto['discussao']:
            lines.append((f"Assunto {index}: {assunto['titulo'] or '—'}", False))
            if assunto['discussao']:
                lines.extend((line, False) for line in assunto['discussao'].splitlines())
    lines.append((f"Observações: {assuntos['observacoes'] or '—'}", False))
    lines.extend([
        ('5. Decisões Tomadas', True),
        *[
            (f"Decisão {index}: {decisao}", False)
            for index, decisao in enumerate(decisoes['itens'], 1)
            if decisao
        ],
        (f"Justificativas: {decisoes['justificativas'] or '—'}", False),
        ('6. Ações Definidas', True),
    ])
    for index, acao in enumerate(content['acoes'], 1):
        if any((acao['tarefa'], acao['responsavel'], acao['prazo'])):
            lines.append((f"Ação {index}: {acao['tarefa'] or '—'}", False))
            lines.append((f"Responsável: {acao['responsavel'] or '—'}", False))
            lines.append((f"Prazo: {_date_from_iso(acao['prazo'])} · Status: {acao['status']}", False))
    lines.extend([
        ('7. Pendências', True),
        *[
            (f"Item {index}: {item}", False)
            for index, item in enumerate(pendencias['itens'], 1)
            if item
        ],
        (f"Próximos passos: {pendencias['proximos_passos'] or '—'}", False),
        ('8. Encerramento', True),
        (f"Horário de término: {encerramento['horario_termino'] or '—'}", False),
        (f"Data da próxima reunião: {_date_from_iso(encerramento['proxima_reuniao'])}", False),
    ])
    anotacoes = _clean(content['anotacoes'])
    if anotacoes:
        lines.append(('Anotações da reunião', True))
        lines.extend((line, False) for line in anotacoes.splitlines())
    return lines


def _date_from_iso(value):
    if not value:
        return '—'
    year, month, day = value.split('-')
    return f'{day}/{month}/{year}'


def _plain_text(atas):
    lines = []
    for index, ata in enumerate(atas):
        if index:
            lines.append(('', False))
        lines.extend(_ata_lines(ata))
    return lines


def _wrap_lines(lines, width=92):
    wrapped = []
    for text, heading in lines:
        parts = textwrap.wrap(
            text,
            width=width,
            break_long_words=True,
            break_on_hyphens=False,
        ) if text else ['']
        wrapped.extend((part, heading) for part in parts)
    return wrapped


def build_pdf(atas):
    lines = _wrap_lines(_plain_text(atas))
    pages = [lines[index:index + 52] for index in range(0, len(lines), 52)] or [[]]

    def literal(text):
        encoded = text.encode('cp1252', errors='replace')
        out = bytearray(b'(')
        for value in encoded:
            if value in (ord('('), ord(')'), ord('\\')):
                out.append(ord('\\'))
                out.append(value)
            elif value < 32 or value > 126:
                out.extend(f'\\{value:03o}'.encode('ascii'))
            else:
                out.append(value)
        out.append(ord(')'))
        return bytes(out)

    objects = {
        1: b'<< /Type /Catalog /Pages 2 0 R >>',
        3: b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
    }
    page_references = []
    for index, page_lines in enumerate(pages):
        page_id = 4 + index * 2
        content_id = page_id + 1
        page_references.append(f'{page_id} 0 R'.encode('ascii'))
        commands = []
        y = 790
        for line, heading in page_lines:
            font_size = 12 if heading else 9
            commands.append(
                b'BT /F1 ' + str(font_size).encode('ascii') + b' Tf 48 '
                + str(y).encode('ascii') + b' Td ' + literal(line) + b' Tj ET'
            )
            y -= 14 if heading else 12
        stream = b'\n'.join(commands)
        objects[page_id] = (
            b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
            b'/Resources << /Font << /F1 3 0 R >> >> /Contents '
            + str(content_id).encode('ascii') + b' 0 R >>'
        )
        objects[content_id] = (
            b'<< /Length ' + str(len(stream)).encode('ascii') + b' >>\nstream\n'
            + stream + b'\nendstream'
        )
    objects[2] = (
        b'<< /Type /Pages /Kids [' + b' '.join(page_references)
        + b'] /Count ' + str(len(pages)).encode('ascii') + b' >>'
    )

    output = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]
    for object_id in range(1, max(objects) + 1):
        offsets.append(len(output))
        output.extend(
            str(object_id).encode('ascii') + b' 0 obj\n'
            + objects[object_id] + b'\nendobj\n'
        )
    xref = len(output)
    output.extend(f'xref\n0 {len(offsets)}\n'.encode('ascii'))
    output.extend(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        output.extend(f'{offset:010d} 00000 n \n'.encode('ascii'))
    output.extend(
        f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n'
        f'startxref\n{xref}\n%%EOF\n'.encode('ascii')
    )
    return bytes(output)


def build_docx(atas):
    paragraphs = []
    for line, heading in _plain_text(atas):
        style = '<w:pPr><w:pStyle w:val="Heading1"/></w:pPr>' if heading else ''
        text = escape(line).replace('\n', '</w:t><w:br/><w:t>')
        paragraphs.append(
            f'<w:p>{style}<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'
        )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:body>' + ''.join(paragraphs)
        + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>'
        '</w:sectPr></w:body></w:document>'
    )
    styles = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
        '<w:name w:val="Normal"/></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>'
        '<w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>'
        '</w:styles>'
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            '[Content_Types].xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
            '</Types>',
        )
        archive.writestr(
            '_rels/.rels',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>',
        )
        archive.writestr('word/document.xml', document)
        archive.writestr('word/styles.xml', styles)
    return output.getvalue()


def _column_name(number):
    result = ''
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def build_xlsx(atas):
    rows = []
    for index, ata in enumerate(atas):
        if index:
            rows.append([''])
        rows.extend([
            ['Ata de reunião', _clean(ata.titulo) or 'Ata sem título'],
            ['Data', _date(ata.data)],
            ['Horário', ata.horario.strftime('%H:%M') if ata.horario else '—'],
            ['Local / Plataforma', _clean(ata.local) or '—'],
            ['Coordenador geral', _clean(ata.coordenador) or '—'],
            ['Responsável pela ata', _clean(ata.responsavel) or '—'],
            ['Seção', 'Campo', 'Conteúdo'],
        ])
        for section, label, value in _sheet_rows(ata):
            rows.append([section, label, value])
    sheet_rows = []
    for row_number, row in enumerate(rows, 1):
        cells = []
        for column_number, value in enumerate(row, 1):
            ref = f'{_column_name(column_number)}{row_number}'
            cells.append(
                f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">'
                f'{escape(str(value or ""))}</t></is></c>'
            )
        sheet_rows.append(f'<row r="{row_number}">{"".join(cells)}</row>')
    worksheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetData>' + ''.join(sheet_rows) + '</sheetData></worksheet>'
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            '[Content_Types].xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>',
        )
        archive.writestr(
            '_rels/.rels',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>',
        )
        archive.writestr(
            'xl/workbook.xml',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="Atas" sheetId="1" r:id="rId1"/></sheets></workbook>',
        )
        archive.writestr(
            'xl/_rels/workbook.xml.rels',
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>',
        )
        archive.writestr('xl/worksheets/sheet1.xml', worksheet)
    return output.getvalue()


def _sheet_rows(ata):
    content = ata.conteudo
    for key, value in (
        ('Participantes', 'Presentes: ' + ', '.join(content['participantes']['presentes'])),
        ('Participantes', 'Ausentes: ' + ', '.join(content['participantes']['ausentes'])),
    ):
        yield key, '', value
    for index, item in enumerate(content['assuntos']['itens'], 1):
        yield 'Assuntos discutidos', f'Assunto {index}', item['titulo']
        yield 'Assuntos discutidos', 'Discussão', item['discussao']
    yield 'Assuntos discutidos', 'Observações', content['assuntos']['observacoes']
    for index, decision in enumerate(content['decisoes']['itens'], 1):
        yield 'Decisões tomadas', f'Decisão {index}', decision
    yield 'Decisões tomadas', 'Justificativas', content['decisoes']['justificativas']
    for index, action in enumerate(content['acoes'], 1):
        yield 'Ações definidas', f'Ação {index}', action['tarefa']
        yield 'Ações definidas', 'Responsável', action['responsavel']
        yield 'Ações definidas', 'Prazo', _date_from_iso(action['prazo'])
        yield 'Ações definidas', 'Status', action['status']
    for index, pending in enumerate(content['pendencias']['itens'], 1):
        yield 'Pendências', f'Item {index}', pending
    yield 'Pendências', 'Próximos passos', content['pendencias']['proximos_passos']
    yield 'Encerramento', 'Horário de término', content['encerramento']['horario_termino']
    yield 'Encerramento', 'Próxima reunião', _date_from_iso(content['encerramento']['proxima_reuniao'])
    yield 'Anotações', '', content['anotacoes']


def safe_stem(ata):
    title = unicodedata.normalize('NFKD', ata.titulo or '')
    title = ''.join(char for char in title if not unicodedata.combining(char))
    title = re.sub(r'[^A-Za-z0-9]+', '-', title).strip('-')[:50]
    return f"Ata_{ata.data.isoformat()}_{title or ata.pk}"


def build_export_files(atas, formats, mode):
    builders = {'pdf': build_pdf, 'docx': build_docx, 'xlsx': build_xlsx}
    output_files = []
    if mode == 'juntos':
        for format_name in formats:
            output_files.append((
                f"Atas_Reuniao{FORMAT_EXTENSIONS[format_name]}",
                builders[format_name](atas),
            ))
        return output_files

    used_names = set()
    for ata in atas:
        stem = safe_stem(ata)
        if stem in used_names:
            stem = f'{stem}_{ata.pk}'
        used_names.add(stem)
        for format_name in formats:
            output_files.append((
                f'{stem}{FORMAT_EXTENSIONS[format_name]}',
                builders[format_name]([ata]),
            ))
    return output_files
