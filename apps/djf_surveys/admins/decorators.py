from django.shortcuts import redirect
from organizations.models import OrganizationUser


def is_admin_or_org_admin(view_func):
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:
            orguser = OrganizationUser.objects.filter(user=request.user, is_admin=True)
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            elif orguser.exists():
                return view_func(request, *args, **kwargs)
            else:
                return redirect("login")
        else:
            return redirect("login")

    return wrapper_func
