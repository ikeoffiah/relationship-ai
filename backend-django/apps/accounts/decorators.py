from functools import wraps
from django.http import JsonResponse
from apps.accounts.models import AgeVerification

def require_age_verified(view_func):
    """
    Decorator that blocks access if age_verification.status != 'verified'.
    Applied to sensitive endpoints per REL-33.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "authentication_required"}, status=401)
        
        verification = getattr(request.user, 'age_verification', None)
        
        if not verification or verification.status != 'verified':
            return JsonResponse({
                "error": "age_verification_required",
                "status": verification.status if verification else "not_started",
                "redirect": "/verify-age"
            }, status=403)
            
        return view_func(request, *args, **kwargs)
    
    return _wrapped_view
