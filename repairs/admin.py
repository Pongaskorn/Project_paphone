from django.contrib import admin

from .models import RepairTicket


@admin.register(RepairTicket)
class RepairTicketAdmin(admin.ModelAdmin):
    list_display = ("ticket_code", "customer_name", "customer_phone", "device_model", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("ticket_code", "customer_name", "customer_phone", "device_model")
