from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Avg
from django.utils import timezone
from datetime import timedelta


@staff_member_required
def clinical_dashboard(request):
    """
    Read-only clinical pilot dashboard.
    Shows aggregated metrics only — no user content.
    """
    from apps.safety.models import SafetyIncident
    from apps.sessions.models import LangGraphSession, SessionFeedback

    now = timezone.now()
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    # Sessions this week by type
    sessions_week = LangGraphSession.objects.filter(created_at__gte=week_ago)
    sessions_individual = sessions_week.filter(session_type='individual').count()
    sessions_joint = sessions_week.filter(session_type='joint').count()
    sessions_total = sessions_week.count()

    # Safety incidents this week
    incidents_week = SafetyIncident.objects.filter(created_at__gte=week_ago)
    incidents_by_severity = {
        'critical': incidents_week.filter(severity='critical').count(),
        'high': incidents_week.filter(severity='high').count(),
        'medium': incidents_week.filter(severity='medium').count(),
        'low': incidents_week.filter(severity='low').count(),
    }
    unreviewed_incidents = incidents_week.filter(status='unreviewed').count()

    # Layer breakdown for last 2 weeks
    incidents_two_weeks = SafetyIncident.objects.filter(created_at__gte=two_weeks_ago)
    total_incidents = incidents_two_weeks.count() or 1
    layer_breakdown = {
        'layer1': round(incidents_two_weeks.filter(layer_detected=1).count() / total_incidents * 100),
        'layer2': round(incidents_two_weeks.filter(layer_detected=2).count() / total_incidents * 100),
        'layer3': round(incidents_two_weeks.filter(layer_detected=3).count() / total_incidents * 100),
    }

    # Helpfulness rating
    avg_rating = SessionFeedback.objects.filter(
        created_at__gte=week_ago
    ).aggregate(avg=Avg('rating'))['avg']
    avg_rating = round(avg_rating, 2) if avg_rating else 'N/A'

    context = {
        'sessions_total': sessions_total,
        'sessions_individual': sessions_individual,
        'sessions_joint': sessions_joint,
        'incidents_by_severity': incidents_by_severity,
        'unreviewed_incidents': unreviewed_incidents,
        'layer_breakdown': layer_breakdown,
        'avg_rating': avg_rating,
        'generated_at': now,
    }
    return render(request, 'config/clinical_dashboard.html', context)
