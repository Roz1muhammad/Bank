from django.contrib import admin
from import_export.admin import ImportExportMixin
from django.http import HttpResponse
import openpyxl
from .Resurs import CardResource
from .models import BankCard,Transfer

from django.contrib import admin
from .models import Transfer


from django.contrib import admin
from .models import Transfer


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'sending_amount', 'currency', 'state', 'created_at')
    list_filter = ('state', 'currency')
    search_fields = ('sender__card_number', 'receiver__card_number', 'ext_id')

    # 🔹 faqat tasdiqlangan transferlarni ko‘rsatish
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(state='confirmed')  # Faqat tasdiqlanganlar chiqadi

    # 🔹 yangi yozuvni admin orqali qo‘shish imkonini o‘chirib qo‘yamiz
    def has_add_permission(self, request):
        return False


    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.action(description="Export to Excel")
def export_to_excel(modeladmin, request, queryset):
    # Excel fayl yaratamiz
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "BankCards"


    headers = ['card_number', 'expiry_date', 'phone', 'status', 'balance']
    ws.append(headers)


    for obj in queryset:
        ws.append([
            obj.card_number,
            obj.expiry_date.strftime("%Y-%m-%d"),
            obj.phone,
            obj.status,
            obj.balance
        ])


    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename=bankcards.xlsx'
    wb.save(response)
    return response


@admin.register(BankCard)
class BankCardAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = CardResource
    list_display = ('card_number', 'expiry_date', 'phone', 'status', 'balance')
    search_fields = ('card_number', 'phone', 'status')
    list_filter = ('status',)
    actions = [export_to_excel]  # ✅ yangi action qo‘shildi

    def get_import_result_class(self):
        class CustomImportResult:
            def __init__(self, result):
                self.result = result

            def __iter__(self):
                for row in self.result:
                    yield {
                        'data': row.diff,
                        'import_type': row.import_type,
                        'error_message': row.messages[0] if row.messages else ''  # messages dan foydalanamiz
                    }

        return CustomImportResult

