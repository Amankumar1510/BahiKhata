import gspread
from oauth2client.service_account import ServiceAccountCredentials

class GoogleSheetService:
    def __init__(self, sheet_name):
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "google_credentials.json", scope
        )
        client = gspread.authorize(creds)
        self.sheet = client.open(sheet_name)

    def get_sheet(self, sheet_name):
        return self.sheet.worksheet(sheet_name)

    def append_row(self, sheet_name, values):
        ws = self.get_sheet(sheet_name)
        ws.append_row(values)

    def get_all(self, sheet_name):
        ws = self.get_sheet(sheet_name)
        return ws.get_all_records()
