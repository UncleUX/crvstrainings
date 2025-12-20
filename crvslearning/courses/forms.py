from django import forms
from .models import Course, Module, Lesson


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['title', 'description', 'category', 'language']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
        }


class ModuleForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ['title', 'description', 'level', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'level': forms.Select(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ['title', 'description', 'content_file', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'required': 'required'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'content_file': forms.ClearableFileInput(attrs={'class': 'form-control', 'required': False}),
            # 'video_file': forms.ClearableFileInput(attrs={'class': 'form-control', 'required': False}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'required': 'required'}),
        }
