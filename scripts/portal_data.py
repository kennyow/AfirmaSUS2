"""Stage a read-only snapshot; never include identities, credentials or databases."""
import json
import re
from pathlib import Path

DOCUMENTS = (
    'linhadotempodinamica.json', 'timeline.json', 'integrantes.json',
    'indicadores.json', 'formacoes.json', 'slides_apresentacoes.json',
    'videos.json', 'calendario_notas.json',
)
GOOGLE_MEDIA = re.compile(r'https?://(?:drive\.google\.com|(?:[\w-]+\.)?googleusercontent\.com)[^\s<>"\']*')


def clean_media(value):
    if isinstance(value, str):
        return GOOGLE_MEDIA.sub('/static/core/media-pendente.svg', value)
    if isinstance(value, list):
        return [clean_media(item) for item in value]
    if isinstance(value, dict):
        return {key: clean_media(item) for key, item in value.items()}
    return value


def stage_documents(source, destination):
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for name in DOCUMENTS:
        document = json.loads((source / name).read_text(encoding='utf-8'))
        if name == 'integrantes.json':
            document = [{key: item.get(key, '') for key in ('nome', 'curso', 'situacao', 'foto')} for item in document]
        (destination / name).write_text(json.dumps(clean_media(document), ensure_ascii=False), encoding='utf-8')
