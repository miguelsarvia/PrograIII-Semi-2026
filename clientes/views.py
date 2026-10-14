from django.http import HttpResponse
from django.shortcuts import render


def hola_mundo(request):
    return HttpResponse('hola mundo, bienvenidos a progra lll')


def saludoNombre(request, nombre, edad):
    return HttpResponse(f'hola {nombre}, tienes {edad} años, bienvenidos a progra lll')

def index(request):
    return render(request, 'index.html')