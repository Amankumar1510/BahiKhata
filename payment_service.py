from datetime import datetime

class PaymentService:
    def __init__(self, sheet_service):
        self.sheet_service = sheet_service

    def add_payment(self, customer_id, amount, payment_mode, date=None):
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        row = ["", customer_id, amount, payment_mode, date]
        self.sheet_service.append_row("payments_received", row)

        return {"success": True}