from import_export import resources
from import_export.results import RowResult
from django.core.exceptions import ValidationError
from .models import BankCard
from .validators import (
    validate_card_number,
    validate_expiry_date,
    validate_phone,
    validate_balance
)


class CardResource(resources.ModelResource):
    class Meta:
        model = BankCard
        import_id_fields = ['card_number']
        skip_unchanged = True
        use_bulk = True
        exclude = ('id',)
        fields = ('card_number', 'expiry_date', 'phone', 'balance')

    def import_row(self, row, instance_loader, **kwargs):
        result = RowResult()

        try:

            validate_card_number(row.get("card_number"))
            row["expiry_date"] = validate_expiry_date(row.get("expiry_date"))
            validate_phone(row.get("phone"))
            validate_balance(row.get("balance"))


            return super().import_row(row, instance_loader, **kwargs)

        except ValidationError as e:
            result.import_type = RowResult.IMPORT_TYPE_SKIP
            result.diff = [row.get(f) for f in row.keys()]
            result.messages = [str(e)]
            result.error_message = str(e)
            return result
