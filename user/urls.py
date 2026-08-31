from flask import Blueprint

from app.api.routers import HTTP_METHODS

from user import views
from user.admin.urls import blueprint as admin_blueprint


app_name = 'user'

blueprint = Blueprint(app_name, __name__)

password_reset_confirm = views.PasswordResetConfirmView.as_view()

rules = [
     ('/create/', views.CreateUserView.as_view(), 'create'),
     ('/token/', views.CreateTokenView.as_view(), 'token'),
     ('/me/', views.ManageUserView.as_view(), 'me'),
     ('/activate/<uuid:code>/', views.ActivateUserView.as_view(),
      'activate'),
     ('/resend-activation/', views.ResendActivationView.as_view(),
      'resend-activation'),
     ('/reset-password/', views.PasswordResetView.as_view(),
      'reset-password'),
     ('/reset-password/confirm/', password_reset_confirm,
      'reset-password-confirm'),
     ('/reset-password/confirm/<string:uidb64>/<string:token>/',
      password_reset_confirm,
      'reset-password-confirm'),
]

for rule, view, name in rules:
    blueprint.add_url_rule(
        rule,
        endpoint=name,
        view_func=view,
        methods=HTTP_METHODS,
    )

blueprint.register_blueprint(admin_blueprint, url_prefix='/admin')
