import json
from datetime import datetime, timedelta

from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from shop.models import CustomerEvent


def reports(request):
    date_range = request.GET.get("date_range", "7")  # Default 7 days
    event_type_filter = request.GET.get("event_type", "")
    customer_filter = request.GET.get("customer", "")

    end_date = timezone.now()
    start_date = end_date - timedelta(days=int(date_range))

    events_qs = CustomerEvent.objects.filter(
        created_at__range=[start_date, end_date]
    ).exclude(event_type="heartbeat")

    if event_type_filter:
        events_qs = events_qs.distinct().filter(event_type=event_type_filter)
    if customer_filter:
        events_qs = events_qs.distinct().filter(customer__id=customer_filter)

    events_by_type = (
        events_qs.values("event_type").annotate(count=Count("id")).order_by("-count")
    )

    events_by_day = []
    for i in range(int(date_range)):
        day = end_date - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        count = events_qs.filter(created_at__range=[day_start, day_end]).count()
        events_by_day.append({"date": day_start.strftime("%Y-%m-%d"), "count": count})

    events_by_day.reverse()

    top_customers = (
        events_qs.exclude(customer=None)
        .values("customer__email", "customer__id")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    recent_events = events_qs.select_related("customer").order_by("-created_at")

    paginator = Paginator(recent_events, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    event_types = CustomerEvent.objects.values_list("event_type", flat=True).distinct()

    customers = (
        CustomerEvent.objects.exclude(customer=None)
        .values("customer__id", "customer__email")
        .distinct()[:100]
    )

    context = {
        "events_by_type": list(events_by_type),
        "events_by_day": events_by_day,
        "top_customers": list(top_customers),
        "page_obj": page_obj,
        "event_types": event_types,
        "customers": customers,
        "total_events": events_qs.count(),
        "unique_customers": events_qs.exclude(customer=None)
        .values("customer")
        .distinct()
        .count(),
        "filters": {
            "date_range": date_range,
            "event_type": event_type_filter,
            "customer": customer_filter,
        },
    }

    return render(request, "backoffice/reports/reports.html", context)


def reports_api(request):
    """API endpoint for dynamic chart updates"""
    date_range = request.GET.get("date_range", "7")
    event_type_filter = request.GET.get("event_type", "")

    end_date = timezone.now()
    start_date = end_date - timedelta(days=int(date_range))

    events_qs = CustomerEvent.objects.filter(created_at__range=[start_date, end_date])

    if event_type_filter:
        events_qs = events_qs.filter(event_type=event_type_filter)

    events_by_type = list(
        events_qs.values("event_type").annotate(count=Count("id")).order_by("-count")
    )

    today = timezone.now().date()
    events_by_hour = []
    for hour in range(24):
        hour_start = timezone.make_aware(
            datetime.combine(today, datetime.min.time().replace(hour=hour))
        )
        hour_end = hour_start + timedelta(hours=1)

        count = events_qs.filter(created_at__range=[hour_start, hour_end]).count()
        events_by_hour.append({"hour": f"{hour:02d}:00", "count": count})

    return JsonResponse(
        {
            "events_by_type": events_by_type,
            "events_by_hour": events_by_hour,
        }
    )
