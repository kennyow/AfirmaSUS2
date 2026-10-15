import re

import re
import unicodedata


MESES = {
    'janeiro': 1,
    'jan': 1,
    'fevereiro': 2,
    'fev': 2,
    'marco': 3,
    'mar': 3,
    'abril': 4,
    'abr': 4,
    'maio': 5,
    'mai': 5,
    'junho': 6,
    'jun': 6,
    'julho': 7,
    'jul': 7,
    'agosto': 8,
    'ago': 8,
    'setembro': 9,
    'set': 9,
    'outubro': 10,
    'out': 10,
    'novembro': 11,
    'nov': 11,
    'dezembro': 12,
    'dez': 12,
}


def converter_link_drive(url):
    """ Converte link de visualização do Google Drive para link direto de imagem """
    if not url:
        return ""
    # Extrai o ID do arquivo no Google Drive
    match = re.search(r'(?:id=|\/d\/)([\w-]+)', url)
    if match:
        file_id = match.group(1)
        return f"https://lh3.googleusercontent.com/d/{file_id}"
    return url


def chave_cronologica_atividade(atividade):
    data = atividade.get('data', '') if isinstance(atividade, dict) else ''
    texto = unicodedata.normalize('NFKD', str(data))
    texto = ''.join(caractere for caractere in texto if not unicodedata.combining(caractere))
    texto = texto.lower()

    data_completa = re.search(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', texto)
    if data_completa:
        dia, mes, ano = (int(parte) for parte in data_completa.groups())
        if 1 <= dia <= 31 and 1 <= mes <= 12:
            return True, ano, mes, dia

    ano_encontrado = re.search(r'\b(\d{4})\b', texto)
    if not ano_encontrado:
        return False, 0, 0, 0
    ano = int(ano_encontrado.group(1))

    mes = 0
    data_numerica = re.search(r'\b(\d{1,2})\s*[/.-]\s*\d{4}\b', texto)
    if data_numerica:
        mes = int(data_numerica.group(1))
    else:
        for palavra in re.findall(r'[a-z]+', texto):
            if palavra in MESES:
                mes = MESES[palavra]
                break

    if not 1 <= mes <= 12:
        return False, 0, 0, 0
    return True, ano, mes, 0


def ordenar_atividades_timeline(atividades):
    return sorted(
        atividades,
        key=chave_cronologica_atividade,
        reverse=True,
    )