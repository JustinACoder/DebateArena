from functools import wraps
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import QueryDict, HttpResponse
from django.shortcuts import resolve_url
from django_htmx.http import HttpResponseClientRedirect


def redirect_to_login_htmx(next, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Redirect the user to the login page, passing the given 'next' page.
    """
    resolved_url = resolve_url(login_url or settings.LOGIN_URL)

    login_url_parts = list(urlparse(resolved_url))
    if redirect_field_name:
        querystring = QueryDict(login_url_parts[4], mutable=True)
        querystring[redirect_field_name] = next
        login_url_parts[4] = querystring.urlencode(safe="/")

    return HttpResponseClientRedirect(str(urlunparse(login_url_parts)))


def user_passes_test_htmx(test_func, login_url=None, redirect_url=None, redirect_field_name=REDIRECT_FIELD_NAME,
                          only_on_htmx=False):
    """
    Decorator for views that checks a certain function, redirecting to the login page if necessary using
    a client redirect by using htmx. If the user passes, the view will be called as normal. This decorator
    is a drop-in replacement for the `user_passes_test` decorator from `django.contrib.auth.decorators` when the view
    is expected to be called using htmx (or any type of ajax request) and the application is using htmx.
    For instance, this could be used to redirect the user to the login page when loading a page when the user is not
    authenticated. Otherwise, htmx will swap the content of the page with the login page content without a full page
    reload.

    :param login_url: The URL to redirect to if the user is not authenticated.
    :param redirect_url: The URL to redirect to after the user logs in. If None, the user will be redirected to the
    current URL.
    :param redirect_field_name: The name of the query parameter passed to the login page to specify the redirect URL.
    :param only_on_htmx: If True, the view will only verify the user is authenticated and redirect if the request is from
    htmx and not another type of request.
    :return: The decorator function
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapper_view(request, *args, **kwargs):
            if request.user.is_authenticated or (only_on_htmx and not request.htmx):
                return view_func(request, *args, **kwargs)

            # The user is not authenticated and the request is htmx
            # We will redirect the user to the login page using htmx instead if simply redirecting using 302
            resolved_login_url = resolve_url(login_url or settings.LOGIN_URL)

            # If a redirect_url value isn't provided, we will set it to the value of
            # the HX-CURRENT-URL header if it exists
            # Otherwise, we will use the value of the referer header
            # If neither of these headers exist, we will use the current URL
            resolved_redirect_url = resolve_url(
                redirect_url
                or request.htmx_headers.get('HX-CURRENT-URL')
                or request.headers.get('Referer')
                or request.get_full_path()
            )

            return redirect_to_login_htmx(resolved_redirect_url, resolved_login_url, redirect_field_name)

        return _wrapper_view

    return decorator


def login_required_htmx(function=None, login_url=None, redirect_url=None, redirect_field_name=REDIRECT_FIELD_NAME,
                        only_on_htmx=False):
    """
    Equivalent to `login_required` from `django.contrib.auth.decorators` but uses htmx for the redirect instead of a 302.
    """
    actual_decorator = user_passes_test_htmx(
        lambda u: u.is_authenticated,
        login_url=login_url,
        redirect_url=redirect_url,
        redirect_field_name=redirect_field_name,
        only_on_htmx=only_on_htmx
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
