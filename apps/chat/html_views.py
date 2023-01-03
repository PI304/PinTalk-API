from django.shortcuts import render


def chatroom_view(request):
    return render(request, "chat/chatroom.html")
