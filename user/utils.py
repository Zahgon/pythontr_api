"""Reporting helper.

Dead code under a public name, kept as it was: nothing in the request path calls it.
"""

from datetime import timedelta

from sqlalchemy import func, select

from core.models import utcnow


def get_time_based_stats(session, model):
    now = utcnow()
    return {
        'today': session.scalar(select(func.count()).select_from(model).where(
            func.date(model.created_at) == now.date())),
        'this_week': session.scalar(select(func.count()).select_from(model).where(
            model.created_at >= now - timedelta(days=7))),
        'this_month': session.scalar(select(func.count()).select_from(model).where(
            func.extract('month', model.created_at) == now.month)),
    }
