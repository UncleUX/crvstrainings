from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse

from courses.models import Lesson
from .models import Exercise, UserExerciseAttempt

class QuizView(LoginRequiredMixin, View):
    template_name = 'exercices/quiz.html'
    
    def get(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, id=lesson_id)
        exercises = lesson.exercises.all().prefetch_related('choices')
        
        # Vérifier si l'utilisateur est inscrit au cours
        if not request.user.enrollments.filter(course=lesson.module.course).exists():
            messages.warning(request, "Vous devez être inscrit au cours pour accéder aux exercices.")
            return redirect('courses:course_detail', course_id=lesson.module.course.id)
        
        # Récupérer les tentatives de l'utilisateur
        user_attempts = {
            attempt.exercise_id: attempt.selected_choice_id 
            for attempt in UserExerciseAttempt.objects.filter(
                user=request.user, 
                exercise__in=exercises
            )
        }
        
        context = {
            'lesson': lesson,
            'exercises': exercises,
            'user_attempts': user_attempts,
            'course': lesson.module.course,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, id=lesson_id)
        exercises = {ex.id: ex for ex in lesson.exercises.all()}
        
        # Traiter les réponses
        results = []
        correct_answers = 0
        
        for exercise_id, choice_id in request.POST.items():
            if not exercise_id.startswith('exercise_'):
                continue
                
            exercise_id = int(exercise_id.replace('exercise_', ''))
            exercise = exercises.get(exercise_id)
            
            if not exercise:
                continue
                
            selected_choice = exercise.choices.filter(id=choice_id).first()
            
            if selected_choice:
                # Enregistrer la tentative
                attempt, created = UserExerciseAttempt.objects.update_or_create(
                    user=request.user,
                    exercise=exercise,
                    defaults={
                        'selected_choice': selected_choice,
                        'is_correct': selected_choice.is_correct
                    }
                )
                
                results.append({
                    'exercise': exercise,
                    'selected_choice': selected_choice,
                    'is_correct': selected_choice.is_correct,
                    'explanation': selected_choice.explanation or ""
                })
                
                if selected_choice.is_correct:
                    correct_answers += 1
        
        # Calculer le score
        score = int((correct_answers / len(exercises)) * 100) if exercises else 0
        
        context = {
            'lesson': lesson,
            'results': results,
            'score': score,
            'total_questions': len(exercises),
            'correct_answers': correct_answers,
            'course': lesson.module.course,
        }
        return render(request, 'exercices/quiz_results.html', context)
