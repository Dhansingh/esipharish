from django.urls import path
from . import views

app_name = "letters"

urlpatterns = [
    path("<int:pk>/editor/", views.letterpad_editor, name="editor"),
    path("<int:pk>/save-positions/", views.save_positions, name="save_positions"),
    path("<int:pk>/preview-pdf/", views.preview_final_pdf, name="preview_pdf"),
    path("application/<int:application_pk>/generate/",views.generate_for_application, name="generate_for_application"),
    path("application/<int:application_pk>/generate/",views.generate_for_application, name="generate_for_application"),
    path("create/", views.create_letter, name="create_letter"),
    path("create/", views.create_letter, name="create_letter"),
    path("create-notice/", views.create_notice, name="create_notice"),
    path("regenerate/<int:pk>/", views.regenerate_letter, name="regenerate_letter"),
]