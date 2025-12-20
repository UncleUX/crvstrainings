from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from courses.models import Category, Course, Module, Lesson, Enrollment
from evaluations.models import EvaluationLevel, EvaluationQuestion, EvaluationChoice

class Command(BaseCommand):
    help = "Seed demo data: users, category, course, modules, lessons, evaluation, enrollment"

    def handle(self, *args, **options):
        User = get_user_model()

        trainer, _ = User.objects.get_or_create(
            username='trainer1', defaults={'email': 'trainer1@example.com', 'role': 'trainer'}
        )
        if not trainer.has_usable_password():
            trainer.set_password('pass1234')
            trainer.save()
        learner, _ = User.objects.get_or_create(
            username='learner1', defaults={'email': 'learner1@example.com', 'role': 'learner'}
        )
        if not learner.has_usable_password():
            learner.set_password('pass1234')
            learner.save()
        admin, _ = User.objects.get_or_create(
            username='admin1', defaults={'email': 'admin1@example.com', 'role': 'admin', 'is_superuser': True, 'is_staff': True}
        )
        if not admin.has_usable_password():
            admin.set_password('pass1234')
            admin.save()

        cat, _ = Category.objects.get_or_create(name='Programmation')

        course, created = Course.objects.get_or_create(
            title='Python Débutant',
            defaults={
                'description': 'Introduction à Python avec modules et leçons.',
                'category': cat,
                'language': 'fr',
                'created_by': trainer,
            }
        )

        if created:
            # Modules et leçons
            mod1 = Module.objects.create(course=course, title='Bases de Python', level='beginner', order=1)
            mod2 = Module.objects.create(course=course, title='Contrôles de flux', level='beginner', order=2)
            Lesson.objects.create(module=mod1, title='Installation', order=1)
            Lesson.objects.create(module=mod1, title='Variables et Types', order=2)
            Lesson.objects.create(module=mod2, title='If/Else', order=1)
            Lesson.objects.create(module=mod2, title='Boucles', order=2)

        # Evaluation niveau beginner
        eval_level, _ = EvaluationLevel.objects.get_or_create(
            course=course, level='beginner', defaults={'title': 'Quiz Débutant', 'threshold': 60, 'is_active': True}
        )
        if not eval_level.questions.exists():
            q1 = EvaluationQuestion.objects.create(evaluation=eval_level, text='Quelle extension pour les fichiers Python ?', order=1, points=1)
            EvaluationChoice.objects.bulk_create([
                EvaluationChoice(question=q1, text='.py', is_correct=True),
                EvaluationChoice(question=q1, text='.pt', is_correct=False),
                EvaluationChoice(question=q1, text='.java', is_correct=False),
            ])
            q2 = EvaluationQuestion.objects.create(evaluation=eval_level, text='Quelle boucle itère sur une séquence ?', order=2, points=1)
            EvaluationChoice.objects.bulk_create([
                EvaluationChoice(question=q2, text='for', is_correct=True),
                EvaluationChoice(question=q2, text='when', is_correct=False),
                EvaluationChoice(question=q2, text='loop', is_correct=False),
            ])

        # Enrôlement du learner
        Enrollment.objects.get_or_create(user=learner, course=course)

        self.stdout.write(self.style.SUCCESS('Seed demo data created.'))
