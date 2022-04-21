from django.utils import timezone


def year(request):
    year = timezone.now().year

    """Добавляет переменную с текущим годом."""
    return {"year": year}
