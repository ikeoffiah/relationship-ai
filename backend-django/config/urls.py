"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include

from apps.relationships.invite_landing import invite_landing


def health(_request):
    """Liveness only — deliberately does not touch the database.

    A health check that fails when Postgres blips gets the whole service
    restarted by the platform, which fixes nothing and drops every in-flight
    request. This answers "is the process up and serving", which is the only
    question a restart can act on.
    """
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health, name="health"),
    # Public: the https link an invite email carries, because mail
    # clients do not linkify custom schemes.
    path("i/<str:token>", invite_landing, name="invite-landing"),
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/users/", include("apps.consent.urls")),
    path("api/v1/users/", include("apps.memory.urls")),
    path("api/v1/users/", include("apps.accounts.profile.urls")),
    path("api/v1/relationships/", include("apps.relationships.urls")),
    path("api/v1/sessions/", include("apps.sessions.urls")),
    path("api/v1/audit/", include("apps.audit.urls")),
    path("api/counseling/", include("apps.counseling.urls")),
    path("api/v1/therapist/", include("apps.therapist.urls")),
    path("api/v1/personalization/", include("apps.personalization.urls")),
    path("api/v1/insights/", include("apps.insights.urls")),
    path("api/v1/engagement/", include("apps.engagement.urls")),
    path("api/v1/chat/", include("apps.chat.urls")),
    # notification_urls declares absolute paths (api/v1/users/... and
    # api/v1/notifications/...), so it mounts at the root rather than under a
    # prefix.
    path("", include("apps.notifications.notification_urls")),
]
