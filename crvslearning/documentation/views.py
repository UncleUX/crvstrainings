from django.views.generic import TemplateView

class DocumentationView(TemplateView):
    template_name = 'documentation/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Ajoutez ici tout contexte supplémentaire si nécessaire
        return context
