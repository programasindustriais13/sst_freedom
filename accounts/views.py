from django.contrib.auth import logout as auth_logout
from django.contrib.auth.views import LogoutView
from django.shortcuts import redirect

class SafeLogoutView(LogoutView):
    http_method_names = ["get", "post", "options"]

    def get(self, request, *args, **kwargs):
        """Allows GET requests for logout."""
        auth_logout(request)
        return redirect(self.get_success_url())

