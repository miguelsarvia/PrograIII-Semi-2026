from django.shortcuts import render
from django.http import HttpResponse,JsonResponse 
import json
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from .models import productos

# Create your views here.

def vistas(request, form):
    return render(request, f"{form}.html")

def busqueda_productos(request):
    buscar = request.GET.get("buscar")
    datos = productos.objects.filter(Q(codigo__icontains=buscar) | Q(nombre__icontains=buscar)).values()
    return JsonResponse({'datos': list(datos)})

@csrf_exempt
def guardar_producto(request):
    if request.method=="POST":
        datos = json.loads(request.body)  
        if( datos.get("accion")=="nuevo" ):
                
            editProducto = productos.objects.create(
                codigo=datos.get("codigo"),
                nombre=datos.get("nombre"),
                marca=datos.get("marca"),
                precio=datos.get("precio")
            )
        elif( datos.get("accion")=="modificar" ):
            editProducto = productos.objects.get(id=datos.get("id"))
            editProducto.codigo=datos.get("codigo")
            editProducto.nombre=datos.get("nombre")
            editProducto.marca=datos.get("marca")
            editProducto.precio=datos.get("precio")
            editProducto.save()
        elif( datos.get("accion")=="eliminar" ):
            editProducto = productos.objects.get(id=datos.get("id"))
            editProducto.delete()
        return JsonResponse({'msg':'ok', 'id': editProducto.id})
    else:
        return JsonResponse({'msg':'Metodo no permitido'})