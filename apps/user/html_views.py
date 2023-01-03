from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def home_view(request):
    return render(request, "account/home.html")


@login_required(login_url="account:login")
def profile_view(request):
    return render(request, "account/profile.html", context={"user_info": request.user})


@login_required(login_url="account:login")
def update_password(request):
    return render(request, "account")
