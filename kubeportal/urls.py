from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path, include

from kubeportal import views
from kubeportal.admin import admin_site

urlpatterns = [
    path('config', views.ConfigView.as_view(), name='config'),
    path('subauthreq', views.SubAuthRequestView.as_view(), name='subauthreq'),
    path('config/download', views.ConfigDownloadView.as_view(content_type='text/plain'), name='config_download'),
    path('', LoginView.as_view(template_name='index.html', redirect_authenticated_user=True), name="index"),
    path('welcome', views.WelcomeView.as_view(), name="welcome"),
    path('logout', LogoutView.as_view(), name="logout"),
    path('social/', include('social_django.urls')),				# AD login, if available
    path('admin/', admin_site.urls),
    # Note: The OpenID Connect URL is /oidc/authorize
    path('oidc/', include('oidc_provider.urls', namespace='oidc_provider'))
]
