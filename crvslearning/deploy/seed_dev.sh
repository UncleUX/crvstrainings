#!/usr/bin/env bash
# Seed development data for CRVS
# - Creates a superuser if it doesn't exist
# - Creates a default Category and a sample Classroom

set -euo pipefail

cd "$(dirname "$0")/.."

python manage.py shell <<'PY'
from django.contrib.auth import get_user_model
from django.utils import timezone
from courses.models import Category
from classrooms.models import Classroom, ClassroomMembership

User = get_user_model()
# Superuser
email = 'admin@example.com'
if not User.objects.filter(email=email).exists():
    u = User.objects.create_superuser(email=email, password='adminadmin', first_name='Admin', last_name='Dev')
    print('Created superuser:', email, 'password=adminadmin')
else:
    u = User.objects.get(email=email)
    print('Superuser exists:', email)

# Default Category
cat, _ = Category.objects.get_or_create(name='Général', defaults={'description': 'Catégorie par défaut'})
print('Category ready:', cat.name)

# Sample Classroom
cls, created = Classroom.objects.get_or_create(
    name='Classe Démo',
    defaults={
        'subject': 'Découverte',
        'description': 'Classe de démonstration',
        'category': cat,
        'created_by': u,
        'schedule': 'Chaque mardi 10h'
    }
)
if created:
    ClassroomMembership.objects.get_or_create(classroom=cls, user=u, role='teacher')
    print('Created classroom demo with teacher admin@example.com')
else:
    print('Classroom demo exists')
PY

echo "Seed completed."
