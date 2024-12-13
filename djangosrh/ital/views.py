from django.shortcuts import render

from django.http import HttpResponse


def index(request):
    return HttpResponse("<html><head><title>Title</title></head><body>Hello, world. You're at the polls index.</body></html>")
