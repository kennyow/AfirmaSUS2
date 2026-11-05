import warnings
from pathlib import PurePosixPath
from zipfile import BadZipFile, ZipFile

from django import forms
from PIL import Image, UnidentifiedImageError


MIME_TYPES = {
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
    '.webp': 'image/webp', '.pdf': 'application/pdf',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
}
IMAGE_FORMATS = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.webp': 'WEBP'}


class UploadPublicoForm(forms.Form):
    titulo = forms.CharField(label='Título', max_length=200)
    arquivo = forms.FileField(
        label='Arquivo',
        widget=forms.ClearableFileInput(attrs={
            'accept': ','.join(MIME_TYPES),
        }),
        help_text='JPG, PNG ou WebP até 5 MB; PDF, DOCX ou XLSX até 10 MB. O conteúdo será público.',
    )

    def clean_arquivo(self):
        arquivo = self.cleaned_data['arquivo']
        extension = PurePosixPath(arquivo.name).suffix.lower()
        if extension not in MIME_TYPES:
            raise forms.ValidationError('Formato não permitido. Envie uma imagem, PDF, DOCX ou XLSX.')
        limit = (5 if extension in IMAGE_FORMATS else 10) * 1024 * 1024
        if not arquivo.size or arquivo.size > limit:
            raise forms.ValidationError('O arquivo está vazio ou ultrapassa o tamanho permitido.')
        try:
            if extension in IMAGE_FORMATS:
                with warnings.catch_warnings():
                    warnings.simplefilter('error', Image.DecompressionBombWarning)
                    with Image.open(arquivo) as image:
                        if image.format != IMAGE_FORMATS[extension]:
                            raise ValueError('Formato da imagem não corresponde à extensão.')
                        if image.width * image.height > 20_000_000:
                            raise ValueError('A imagem ultrapassa 20 milhões de pixels.')
                        if getattr(image, 'n_frames', 1) != 1:
                            raise ValueError('Envie uma imagem sem animação.')
                        image.verify()
            elif extension == '.pdf':
                if not arquivo.read(5) == b'%PDF-':
                    raise ValueError('Cabeçalho PDF inválido.')
                arquivo.seek(max(0, arquivo.size - 1024))
                if b'%%EOF' not in arquivo.read():
                    raise ValueError('PDF incompleto.')
            else:
                with ZipFile(arquivo) as package:
                    members = package.infolist()
                    if len(members) > 1000 or sum(item.file_size for item in members) > 50 * 1024 * 1024:
                        raise ValueError('Documento compactado grande demais.')
                    expected = 'word/document.xml' if extension == '.docx' else 'xl/workbook.xml'
                    names = package.namelist()
                    if '[Content_Types].xml' not in names or expected not in names:
                        raise ValueError('Estrutura do documento inválida.')
                    if any('vbaproject' in name.lower() for name in names):
                        raise ValueError('Documentos com macros não são permitidos.')
        except (UnidentifiedImageError, OSError, ValueError, BadZipFile,
                Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
            raise forms.ValidationError('Arquivo inválido ou danificado para o formato selecionado.') from error
        finally:
            arquivo.seek(0)
        # Do not trust the MIME type supplied by the browser.
        arquivo.content_type = MIME_TYPES[extension]
        return arquivo
