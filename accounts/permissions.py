from rest_framework.permissions import BasePermission


class IsAgent(BasePermission):
    message = "Faqat Uyimiz Agent uchun ruxsat berilgan"

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'agent')


class IsAdminRole(BasePermission):
    """Admin panel: role admin yoki superadmin bo'lishi kerak."""

    message = 'Faqat admin panel foydalanuvchilari uchun ruxsat berilgan'

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('admin', 'superadmin')
        )


class IsSuperAdmin(BasePermission):
    message = 'Faqat superadmin uchun ruxsat berilgan'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'superadmin')
