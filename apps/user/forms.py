from allauth.account.forms import SignupForm, LoginForm
from django import forms

from apps.user.models import User
from apps.user.services import UserService


class CustomSignupForm(SignupForm):
    service_name = forms.CharField(label="서비스 이름")
    service_expl = forms.CharField(label="어떤 서비스인가요?", widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "이메일"
        self.fields["password1"].label = "비밀번호"
        self.fields["password2"].label = "비밀번호 재입력"

    def save(self, request) -> User:

        # Ensure you call the parent class's save method
        # .save() returns a User object.
        user = super(CustomSignupForm, self).save(request)
        user.service_name = self.cleaned_data["service_name"]
        user.service_expl = self.cleaned_data["service_expl"]

        # Add your own processing here.
        user.access_key = UserService.generate_access_key()
        user.secret_key = UserService.generate_secret_key()

        user.save()

        # You must return the original result.
        return user

    class Meta:
        model = User


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["login"].label = "이메일"
        self.fields["password"].label = "비밀번호"
