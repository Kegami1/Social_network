from datetime import date

date_time = date.today()


def year(request):
    """Добавляет переменную с текущим годом."""
    return {
        'year': date_time.year
    }
