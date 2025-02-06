from django.contrib.auth.decorators import login_required as auth_login_required
from django.urls import reverse

def login_required(*args, **kwargs):
    return auth_login_required(login_url='/login', *args, **kwargs)
