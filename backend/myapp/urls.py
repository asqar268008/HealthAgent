from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name="home"),

    # AUTH
    path('login/', views.api_login, name="login"),
    path('signup/', views.api_signup, name="signup"),
    path('logout/', views.logout_view, name="logout"),

    # main page (profile + dashboard)
    path('health/', views.health, name="health"),

    # HEALTH APIs
    path("api/health/profile/save/", views.save_health_profile),
    path("api/health/profile/get/", views.get_health_profile),
    path("api/health/stress/", views.stress_prediction_agent),
    path("api/health/chat/", views.health_decision_agent),
]