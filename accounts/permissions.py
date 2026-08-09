from rest_framework.permissions import BasePermission


class IsAgent(BasePermission):
    """CRM'ga faqat ADMIN TASDIQLAGAN agent kira oladi.

    Agent o'zi ariza topshirganda `role='agent'` bo'ladi, lekin
    `certification='Kutilmoqda'` holatida turadi — bu bosqichda CRM yopiq.
    Admin "Tasdiqlangan" qilgach ochiladi.
    """

    message = "Faqat Uyimiz Agent uchun ruxsat berilgan"

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.role == 'agent'):
            return False
        if user.certification != 'Tasdiqlangan':
            self.message = (
                "Arizangiz ko'rib chiqilmoqda. Admin tasdiqlagach CRM ochiladi."
                if user.certification == 'Kutilmoqda'
                else f'Agent maqomi: {user.certification}. CRM yopiq.'
            )
            return False
        if not user.is_active:
            self.message = "Hisobingiz bloklangan"
            return False
        return True


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
