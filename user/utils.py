from datetime import timedelta

from sqlalchemy import func

from core.models.base import now as timezone_now


def get_time_based_stats(model):
    now = timezone_now()
    return {
        'today': model.query.filter(
            func.date(model.created_at) == now.date()).count(),
        'this_week': model.query.filter(
            model.created_at >= now-timedelta(days=7)).count(),
        'this_month': model.query.filter(
            func.extract('month', model.created_at) == now.month).count(),
    }
