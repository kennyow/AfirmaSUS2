from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from ..forms import CadastroUsuarioForm  # ✅ Correto (sobe um nível para pegar o forms.py em core/)

def fazer_login(request):
    if request.method == 'POST':
        usuario_input = request.POST.get('username')
        senha_input = request.POST.get('password')
        user = authenticate(request, username=usuario_input, password=senha_input)
        if user is not None:
            login(request, user)
            messages.success(request, f"Bem-vindo(a), {user.first_name or user.username}!")
            return redirect('home')
        else:
            messages.error(request, "Usuário ou senha inválidos.")
    return render(request, 'core/login.html')

def fazer_logout(request):
    logout(request)
    messages.info(request, "Você saiu da sua conta.")
    return redirect('home')

def cadastrar_usuario(request):
    if request.method == 'POST':
        form = CadastroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, "Conta criada com sucesso! Agora você pode fazer login.")
            return redirect('login')
    else:
        form = CadastroUsuarioForm()

    return render(request, 'core/cadastro.html', {'form': form})