# adminapp/utils.py
from django.shortcuts import redirect
from django.contrib import messages

def superuser_required(view_func):
    """Decorator to ensure that only superusers can access"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login first")
            return redirect('adminapp:login')
            
        if not request.user.is_superuser:
            messages.error(request, "Access denied. You need superuser privileges.")
            return redirect('adminapp:login')
            
        return view_func(request, *args, **kwargs)
    return wrapper