from rest_framework import permissions


class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_staff)


class IsOwnerOrStaff(permissions.BasePermission):
    # свой объект или staff; у прогресса смотрим participation.user

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_staff:
            return True
        owner = getattr(obj, 'user', None)
        if owner is not None and owner.pk == user.pk:
            return True
        participation = getattr(obj, 'participation', None)
        if participation is not None and participation.user_id == user.pk:
            return True
        return False
