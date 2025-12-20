from django.shortcuts import render, get_object_or_404
from django.http import HttpRequest, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from .models import Certification
from courses.models import Course


def verify(request: HttpRequest, code: str) -> HttpResponse:
    cert = get_object_or_404(Certification, code=code)
    return render(request, 'certifications/verify.html', {
        'cert': cert,
    })


@login_required
def achievements(request: HttpRequest) -> HttpResponse:
    """Affiche la page des réalisations avec les badges de certification de l'utilisateur."""
    certifications = Certification.objects.filter(
        user=request.user,
        is_valid=True
    ).select_related('course').order_by('-issued_at')
    
    return render(request, 'certifications/achievements.html', {
        'certifications': certifications,
    })
