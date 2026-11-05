"""Stage a read-only snapshot; never include identities, credentials or databases."""
import json
import sys
from pathlib import Path

DOCUMENTS = (
    'linhadotempodinamica.json', 'timeline.json', 'integrantes.json',
    'indicadores.json', 'formacoes.json', 'slides_apresentacoes.json',
    'videos.json', 'calendario_notas.json',
)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.legacy_media import replace_legacy_media


def clean_media(value, media_url):
    if isinstance(value, str):
        return replace_legacy_media(value, media_url, '/static/core/media-pendente.svg')
    if isinstance(value, list):
        return [clean_media(item, media_url) for item in value]
    if isinstance(value, dict):
        return {key: clean_media(item, media_url) for key, item in value.items()}
    return value


def stage_documents(source, destination):
    source, destination = Path(source), Path(destination)
    media_url = json.loads((Path(__file__).resolve().parent.parent / 'wrangler.jsonc').read_text(encoding='utf-8'))['vars']['MEDIA_PUBLIC_URL']
    destination.mkdir(parents=True, exist_ok=True)
    for name in DOCUMENTS:
        document = json.loads((source / name).read_text(encoding='utf-8'))
        if name == 'integrantes.json':
            document = [{key: item.get(key, '') for key in ('nome', 'curso', 'situacao', 'foto')} for item in document]
        (destination / name).write_text(json.dumps(clean_media(document, media_url), ensure_ascii=False), encoding='utf-8')
