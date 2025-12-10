class CustomerService:
    def __init__(self, sheet_service):
        self.sheet_service = sheet_service

    def get_customers(self):
        return self.sheet_service.get_all("customers")

    def add_customer(self, name, phone="", notes=""):
        row = ["", name, phone, notes]
        self.sheet_service.append_row("customers", row)
        return {"success": True}
