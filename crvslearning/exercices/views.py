from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Exercise, Choice, UserExerciseAttempt
from courses.models import Lesson

class ExerciseCreateView(LoginRequiredMixin, CreateView):
    model = Exercise
    fields = ['question', 'order']
    template_name = 'exercices/exercise_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['lesson'] = get_object_or_404(Lesson, id=self.kwargs['lesson_id'])
        return context

    def form_valid(self, form):
        form.instance.lesson = get_object_or_404(Lesson, id=self.kwargs['lesson_id'])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('courses:lesson_detail', kwargs={'pk': self.object.lesson.id})

@login_required
@require_POST
def submit_attempt(request, exercise_id):
    exercise = get_object_or_404(Exercise, id=exercise_id)
    choice_id = request.POST.get('choice_id')
    
    if not choice_id:
        return JsonResponse({'error': 'Veuillez sélectionner une réponse'}, status=400)
    
    try:
        selected_choice = exercise.choices.get(id=choice_id)
    except Choice.DoesNotExist:
        return JsonResponse({'error': 'Choix invalide'}, status=400)
    
    # Créer ou mettre à jour la tentative
    attempt, created = UserExerciseAttempt.objects.update_or_create(
        user=request.user,
        exercise=exercise,
        defaults={
            'selected_choice': selected_choice,
            'is_correct': selected_choice.is_correct
        }
    )
    
    return JsonResponse({
        'correct': selected_choice.is_correct,
        'explanation': selected_choice.explanation or ''
    })