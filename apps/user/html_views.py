from django.shortcuts import render


def home_view(request):
    return render(request, "account/home.html")


def profile_view(request):
    return render(request, "account/profile.html")
