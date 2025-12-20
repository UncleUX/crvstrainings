from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from .models import Course, Module, Lesson, UserLessonProgress, Enrollment
from django.http import JsonResponse
from .forms import CourseForm, ModuleForm, LessonForm


def is_formateur(user):
    return user.is_authenticated and user.role == 'formateur'


@login_required
def course_list(request):
    courses = Course.objects.all()
    return render(request, 'courses/course_list.html', {'courses': courses})


@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    modules = course.modules.prefetch_related('lessons').all()

    context = {
        'course': course,
        'modules': modules,
        'is_enrolled': is_enrolled,
    }
    return render(request, 'courses/course_detail.html', context)


@login_required
def module_detail(request, course_id, module_id):
    module = get_object_or_404(Module, id=module_id, course__id=course_id)
    lessons = module.lessons.order_by('order')
    return render(request, 'courses/module_detail.html', {'module': module, 'lessons': lessons})


@login_required
def lesson_detail(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    module = lesson.module
    course = module.course

    # Vérifie si l'utilisateur est inscrit au cours
    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()

    # Si pas inscrit, autoriser uniquement l'accès à la première leçon du premier module
    first_module = course.modules.order_by('id').first()
    first_lesson = first_module.lessons.order_by('id').first() if first_module else None

    if not is_enrolled and lesson != first_lesson:
        messages.warning(request, "Veuillez vous inscrire pour accéder à cette leçon.")
        return redirect('courses:course_detail', course_id=course.id)

    context = {
        'lesson': lesson,
        'module': module,
        'course': course,
    }
    return render(request, 'courses/lesson_detail.html', context)


@user_passes_test(is_formateur)
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.created_by = request.user
            course.save()
            return redirect('courses:course_detail', course_id=course.id)
    else:
        form = CourseForm()
    return render(request, 'courses/course_form.html', {'form': form})


@user_passes_test(is_formateur)
def module_create(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        form = ModuleForm(request.POST)
        if form.is_valid():
            module = form.save(commit=False)
            module.course = course
            module.save()
            return redirect('courses:course_detail', course_id=course.id)
    else:
        form = ModuleForm()
    return render(request, 'courses/module_form.html', {'form': form, 'course': course})


@user_passes_test(is_formateur)
def lesson_create(request, course_id, module_id):
    module = get_object_or_404(Module, id=module_id, course__id=course_id)
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.module = module
            lesson.save()
            return redirect('courses:module_detail', course_id=course_id, module_id=module_id)
    else:
        form = LessonForm()
    return render(request, 'courses/lesson_form.html', {'form': form, 'module': module})
  
@login_required
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    enrollment, created = Enrollment.objects.get_or_create(user=request.user, course=course)
    if created:
        messages.success(request, f"Vous êtes bien inscrit au cours {course.title}.")
    else:
        messages.info(request, f"Vous êtes déjà inscrit à ce cours.")
    return redirect('courses:course_detail', course_id=course.id)

@login_required
def module_list(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    # Vérifier que l'utilisateur est inscrit au cours
    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()
    if not is_enrolled:
        # Rediriger ou afficher un message d'erreur
        messages.error(request, "Vous devez être inscrit pour accéder aux modules.")
        return redirect('courses:course_detail', course_id=course.id)

    modules = course.modules.all()
    context = {
        'course': course,
        'modules': modules,
    }
    return render(request, 'courses/module_list.html', context)

@login_required
#@require_POST
def mark_lesson_completed(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    course = lesson.module.course

    is_enrolled = Enrollment.objects.filter(user=request.user, course=course).exists()

    if not is_enrolled:
        return JsonResponse({'status': 'unauthorized'}, status=403)

    progress, created = LessonProgress.objects.get_or_create(user=request.user, lesson=lesson)
    progress.is_completed = True
    progress.save()

    return JsonResponse({'status': 'ok', 'completed': True})
