from axes.handlers.database import AxesDatabaseHandler


class AdminOnlyAxesHandler(AxesDatabaseHandler):
    """Count only Django admin login failures.

    AXES_ONLY_ADMIN_SITE stops lockouts outside the admin, but failures are
    still recorded. API logins have their own throttles; recording them here
    would let mistyped API logins lock a teacher out of /admin/.
    """

    def user_login_failed(self, sender, credentials: dict, request=None, **kwargs):
        if request is None or not self.is_admin_request(request):
            return
        super().user_login_failed(sender, credentials, request, **kwargs)
