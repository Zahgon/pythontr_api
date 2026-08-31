from flask import redirect, request, url_for
from flask_admin import AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user, login_user, logout_user
from flask_babel import gettext as _
from flask_babel import lazy_gettext
from wtforms import Form, PasswordField, StringField, validators

from app.extensions import admin_site, db
from core import models
from core.auth import authenticate

LOGIN_VIEWS = ('login_view', 'logout_view')


def is_staff(user):
    return bool(user.is_authenticated and user.is_active and user.is_staff)


def return_path():
    """Where the sign-in page sends the visitor back to, as a bare path.

    The parameter has always been path and query with no scheme or host, and
    with no question mark when there is no query; werkzeug's ``full_path``
    appends one either way.
    """
    if request.query_string:
        return '{}?{}'.format(
            request.path, request.query_string.decode('utf-8')
        )
    return request.path


class LoginForm(Form):
    email = StringField(lazy_gettext('email'), [validators.InputRequired()])
    password = PasswordField(
        lazy_gettext('password'), [validators.InputRequired()]
    )


class AdminSiteIndexView(AdminIndexView):

    def is_accessible(self):
        return is_staff(current_user)

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('.login_view', next=return_path()))

    def _handle_view(self, name, **kwargs):
        # The sign-in pages stay reachable while signed out, otherwise the
        # redirect the gate performs would point back at itself.
        if name in LOGIN_VIEWS:
            return None
        return super()._handle_view(name, **kwargs)

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        form = LoginForm(request.form)
        error = None
        if request.method == 'POST' and form.validate():
            user = authenticate(
                request=request,
                username=form.email.data,
                password=form.password.data,
            )
            if user is not None and user.is_staff:
                login_user(user)
                return redirect(request.args.get('next') or url_for('.index'))
            error = _('please_enter_the_correct_email_and_password')
        return self.render('admin/login.html', form=form, error=error)

    @expose('/logout/')
    def logout_view(self):
        logout_user()
        return redirect(url_for('.login_view'))


class AdminModelView(ModelView):
    """Staff-only model view, matching who could reach the admin before."""

    def is_accessible(self):
        return is_staff(current_user)

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin.login_view', next=return_path()))


class UserAdmin(AdminModelView):
    column_default_sort = 'id'
    form_excluded_columns = ('created_at', 'slug')
    column_list = ('email', 'username', 'name', 'surname',
                   'created_at', 'updated_at',  'last_login')
    column_filters = ('email',)
    form_columns = (
        'email', 'password',
        # _('personel_info')
        'username', 'name', 'surname', 'about_me', 'image',
        # _('permissions')
        'is_notification_email', 'is_staff', 'is_superuser',
        'is_active', 'is_ban', 'is_delete',
        # _('important_dates')
        'last_login',
    )
    column_labels = {
        'username': _('personel_info'),
        'is_notification_email': _('permissions'),
        'last_login': _('important_dates'),
    }


class ArticleAdmin(AdminModelView):
    column_list = ('id', 'created_at', 'title', 'title_h1', 'is_active',
                   'is_delete')
    column_filters = ('id', 'title', 'title_h1')
    column_searchable_list = ('title', 'title_h1')


class CommentAdmin(AdminModelView):
    column_list = ('id', 'created_at', 'content', 'content_object',
                   'is_active', 'is_delete',)
    column_filters = ('id', 'content')
    column_searchable_list = ('content',)


class PageVisitAdmin(AdminModelView):
    can_create = False  # Close add record
    column_list = ('id', 'user', 'path', 'timestamp', 'ip_address',
                   'user_agent', 'referrer', 'method', 'device_type',
                   'language', 'ga_client_id', 'ga_session_id', 'gads_id',
                   'gpi_uid')
    column_filters = ('id', 'path', 'device_type', 'method', 'timestamp')
    column_searchable_list = ('path',)
    form_excluded_columns = ('timestamp',)


def register(app):
    """Attach every registered model view to the application."""
    # The index view is swapped in here rather than at construction time: it
    # carries the sign-in route, and the extension singleton is built before
    # this module can be imported.
    admin_site._set_admin_index_view(AdminSiteIndexView())
    # Endpoints and URLs keep the ``core_<model>`` / ``/admin/core/<model>/``
    # shape the admin had before, so bookmarks and links still resolve.
    registry = (
        (UserAdmin, models.User, 'user'),
        (AdminModelView, models.Category, 'category'),
        (ArticleAdmin, models.Article, 'article'),
        (CommentAdmin, models.Comment, 'comment'),
        (AdminModelView, models.Message, 'message'),
        (PageVisitAdmin, models.PageVisit, 'pagevisit'),
    )
    for view_class, model, name in registry:
        admin_site.add_view(view_class(
            model,
            db.session,
            endpoint='core_{}'.format(name),
            url='core/{}'.format(name),
        ))
    admin_site.init_app(app)
