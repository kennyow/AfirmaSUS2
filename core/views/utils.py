import re

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