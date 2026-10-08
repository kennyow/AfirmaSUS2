from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from ..models import Local, Atividade, EscalaTrabalho
from ..forms import LocalForm, AtividadeForm, EscalaForm

@login_required
def cadastrar_local(request):
    if request.method == 'POST':
        form = LocalForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Novo local cadastrado com sucesso no mapa!")
            return redirect('pagina_mapa')
    else:
        form = LocalForm()

    return render(request, 'core/form_local.html', {'form': form})

@login_required
def cadastrar_atividade(request):
    if request.method == 'POST':
        form = AtividadeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Atividade cadastrada com sucesso!")
            return redirect('pagina_escala')
    else:
        form = AtividadeForm()

    return render(request, 'core/form_atividade.html', {'form': form})

@login_required
def deletar_local(request, local_id):
    local = get_object_or_404(Local, pk=local_id)
    local.delete()
    messages.warning(request, "Local removido com sucesso do mapa.")
    return redirect('pagina_mapa')

def pagina_escala(request):
    escalas = EscalaTrabalho.objects.select_related('integrante', 'local').all()
    atividades = Atividade.objects.all().order_by('data')
    
    dias = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']
    escalas_por_dia = {dia: escalas.filter(dia_semana=dia) for dia in dias}

    context = {
        'escalas_por_dia': escalas_por_dia,
        'atividades': atividades,
    }
    return render(request, 'core/escala.html', context)

@login_required
def cadastrar_escala(request):
    if request.method == 'POST':
        form = EscalaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Nova escala cadastrada com sucesso!")
            return redirect('pagina_escala')
    else:
        form = EscalaForm()

    return render(request, 'core/form_escala.html', {'form': form})