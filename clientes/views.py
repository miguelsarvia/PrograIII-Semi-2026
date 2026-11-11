from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponse,JsonResponse 
import json
from django.views.decorators.csrf import csrf_exempt
from .models import clientes

def hola_mundo(request):
    return HttpResponse('hola mundo, bienvenidos a progra lll')


def saludoNombre(request, nombre, edad):
    return HttpResponse(f'hola {nombre}, tienes {edad} años, bienvenidos a progra lll')

def index(request):
    return render(request, 'index.html')

def vistas(request, form):
    return render(request, f"{form}.html")

def busqueda_clientes(request):
    buscar = request.GET.get("buscar")
    datos = clientes.objects.filter(nombre__icontains=buscar).values()
    return JsonResponse({'datos': list(datos)})

@csrf_exempt
def guardar_cliente(request):
    if request.method=="POST":
        datos = json.loads(request.body)  
        if( datos.get("accion")=="nuevo" ):
                
            editCliente = clientes.objects.create(
                codigo=datos.get("codigo"),
                nombre=datos.get("nombre"),
                direccion=datos.get("direccion"),
                telefono=datos.get("telefono"),
                email=datos.get("email"),
                tipo=datos.get("tipo")
            )
        elif( datos.get("accion")=="modificar" ):
            editCliente = clientes.objects.get(id=datos.get("id"))
            editCliente.codigo=datos.get("codigo")
            editCliente.nombre=datos.get("nombre")
            editCliente.direccion=datos.get("direccion")
            editCliente.telefono=datos.get("telefono")
            editCliente.email=datos.get("email")
            editCliente.tipo=datos.get("tipo")
            editCliente.save()
        elif( datos.get("accion")=="eliminar" ):
            editCliente = clientes.objects.get(id=datos.get("id"))
            editCliente.delete()
        return JsonResponse({'msg':'ok', 'id': editCliente.id})
    else:
        return JsonResponse({'msg':'Metodo no permitido'})