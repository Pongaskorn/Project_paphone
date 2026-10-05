from django.contrib import admin

from .models import Part, StockMovement, TicketPart


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "quantity", "min_quantity", "sell_price", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("sku", "name", "compatible_models")
    # ยอดคงเหลือแก้ผ่านระบบเท่านั้น เพื่อให้มีประวัติเสมอ
    readonly_fields = ("quantity",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "part", "movement_type", "change", "balance_after", "created_by")
    list_filter = ("movement_type",)
    search_fields = ("part__sku", "part__name", "note")


admin.site.register(TicketPart)
