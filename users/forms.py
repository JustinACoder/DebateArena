from crispy_bootstrap5.bootstrap5 import Switch
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Fieldset, Div, Submit
from django import forms
from django.contrib.auth import get_user_model
from allauth.account.forms import SignupForm, ResetPasswordKeyForm

from users.models import Profile


class ViewEditUserForm(forms.ModelForm):
    # Prevent the user from changing their username
    # Note: According to https://docs.djangoproject.com/en/5.0/ref/forms/fields/#disabled,
    #       the disabled attribute will make the form ignore the new value of the field if the user
    #       tampers with the html and edits the field.
    username = forms.CharField(disabled=True)

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'first_name', 'last_name']


class CustomSignupForm(SignupForm):
    # For now, it's exactly the same as the default SignupForm except that we do not include help_text
    # for the password field.
    def __init__(self, *args, **kwargs):
        super(CustomSignupForm, self).__init__(*args, **kwargs)
        self.fields['password1'].help_text = None


class CustomResetPasswordKeyForm(ResetPasswordKeyForm):
    # For now, it's exactly the same as the default ResetPasswordForm except that we do not include help_text
    # for the password field.
    def __init__(self, *args, **kwargs):
        super(CustomResetPasswordKeyForm, self).__init__(*args, **kwargs)
        self.fields['password1'].help_text = None


class ProfileForm(forms.ModelForm):
    bio = forms.CharField(label='About Description', required=False, max_length=2048, strip=True, widget=forms.Textarea(
        attrs={'rows': 5, 'placeholder': 'Tell others about yourself...', 'style': 'resize: none;'}))
    show_recent_stances = forms.BooleanField(label='Show recent stances', required=False)

    class Meta:
        model = Profile
        exclude = ['user']

    def __init__(self, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                Div(
                    Field('bio', template='user/forms/field_settings.html'),
                    css_class='py-3 list-group-item'
                ),
                Div(
                    Field('show_recent_stances', template='user/forms/switch_settings.html'),
                    css_class='py-3 list-group-item'
                ),
                css_class='list-group'
            )
        )
        self.helper.form_tag = False
