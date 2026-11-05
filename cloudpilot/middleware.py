from django.http import HttpResponse


class UploadSizeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            length = int(request.META.get('CONTENT_LENGTH') or 0)
        except (TypeError, ValueError):
            return HttpResponse('Tamanho da requisição inválido.', status=400)
        if length < 0 or length > 12 * 1024 * 1024:
            return HttpResponse('Envie um arquivo de até 10 MB por vez.', status=413)
        return self.get_response(request)
