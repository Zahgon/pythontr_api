"""Object-level rules.

They are declared, and the detail routes never reach them: every ``get_object`` returns
its row directly. The rules are kept because they are part of the project's vocabulary.
"""

SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS')


class IsAuthenticatedAndOwner:
    message = 'You must be the owner of this object.'

    def has_permission(self, request, user):
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, user, obj):
        if request.method in SAFE_METHODS:
            return True
        if getattr(obj, 'user_id', None) is not None:
            return obj.user_id == user.id
        return False


class IsAuthenticatedAndOwnerOrAdmin:
    def has_object_permission(self, request, user, obj):
        return bool(user and user.is_authenticated
                    and (user.is_staff or obj.user_id == user.id))
