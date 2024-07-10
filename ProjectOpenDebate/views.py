from django.shortcuts import render


def main(request):
    return render(request, 'ProjectOpenDebate/main.html', {'include_footer': True})
