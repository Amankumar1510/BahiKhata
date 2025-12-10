from datetime import datetime

class GoodsService:
    def __init__(self, sheet_service):
        self.sheet_service = sheet_service

    def add_goods_sold(self, customer_id, units, weight, price_per_kg, date=None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        amount_due = weight * price_per_kg

        row = [
            "",  # id auto-filled later
            customer_id,
            units,
            weight,
            price_per_kg,
            date,
            amount_due
        ]

        self.sheet_service.append_row("goods_sold", row)
        return {"success": True, "amount_due": amount_due}