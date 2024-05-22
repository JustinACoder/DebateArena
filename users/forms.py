from django import forms
from django.contrib.auth import get_user_model


class ViewEditUserForm(forms.ModelForm):
    # Prevent the user from changing their username
    # Note: According to https://docs.djangoproject.com/en/5.0/ref/forms/fields/#disabled,
    #       the disabled attribute will make the form ignore the new value of the field if the user
    #       tampers with the html and edits the field.
    username = forms.CharField(disabled=True)

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'first_name', 'last_name']
