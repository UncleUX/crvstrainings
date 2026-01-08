import os
import django

# Configuration de l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crvslearning.settings')
django.setup()

from courses.models import Course, Category, Module, Lesson

print("=== Catégories existantes ===")
for category in Category.objects.all():
    print(f"- {category.name} (ID: {category.id})")

print("\n=== Cours existants ===")
for course in Course.objects.all():
    category_name = course.category.name if course.category else "Aucune"
    print(f"\nID: {course.id}")
    print(f"Titre: {course.title}")
    print(f"Catégorie: {category_name}")
    print(f"Description: {course.description[:100]}..." if course.description else "Pas de description")
    print(f"Publié: {'Oui' if course.is_published else 'Non'}")
    print(f"Créé par: {course.created_by.username if course.created_by else 'Inconnu'}")
    print(f"Modules: {course.modules.count()}")
    
    # Compter le nombre total de leçons dans tous les modules du cours
    total_lessons = 0
    for module in course.modules.all():
        total_lessons += module.lessons.count()
    print(f"Leçons totales: {total_lessons}")
