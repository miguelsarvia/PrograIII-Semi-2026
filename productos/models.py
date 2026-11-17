from django.db import models

# Create your models here.
class productos(models.Model):
    codigo = models.CharField(max_length=10)
    nombre = models.CharField(max_length=100)
    marca = models.CharField(max_length=100)
    precio = models.CharField(max_length=10)