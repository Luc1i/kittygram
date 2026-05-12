from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from cats.views import cat_list
from quests.views import LoginTokenView, PromoteSelfStaffView, RegisterView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('cats/', cat_list),
    path('api/', include('quests.urls')),
    path('api/auth/register/', RegisterView.as_view(), name='auth-register'),
    path('api/auth/promote-self/', PromoteSelfStaffView.as_view(), name='auth-promote-self'),
    path('api/auth/token/', LoginTokenView.as_view(), name='auth-token'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/schema/swagger-ui/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path(
        'api/schema/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc',
    ),
]
