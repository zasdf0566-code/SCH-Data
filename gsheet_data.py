import json
import logging
import os
import gspread

logger = logging.getLogger(__name__)


class GSheetData:

    def __init__(self):
        self.gc = self._authenticate()
        url = os.environ.get(
            "GOOGLE_SPREADSHEET_URL",
            "https://docs.google.com/spreadsheets/d/1Q281_R_MrEhEIg1PpeXbYgXTakNjrkTFVDhuZbmdLJk/edit?usp=drive_link",
        )
        self.spreadsheet = self.gc.open_by_url(url)

        # Sheet အားလုံးကို memory ထဲသို့ load လုပ်ခြင်း
        self.profile_rows = self._load_sheet("Profile")
        self.stock_rows, self.stock_months = self._load_monthly_sheet(
            "Stock", sub_headers=["RDT", "ACT", "CQ", "PQ"]
        )
        self.testing_rows, self.testing_months = self._load_monthly_sheet(
            "Testing",
            sub_headers=["Testing", "Pf", "Pv", "Mix", "NTG", "Refer"],
        )
        logger.info(
            f"Loaded: Profile={len(self.profile_rows)},"
            f" Stock={len(self.stock_rows)}, Testing={len(self.testing_rows)}"
            " rows"
        )

    # ─── AUTH ────────────────────────────────────────────────

    def _authenticate(self):
        creds_str = os.environ.get("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS")
        if creds_str:
            tmp_path = "/tmp/service_account.json"
            with open(tmp_path, "w") as f:
                f.write(creds_str)
            return gspread.service_account(filename=tmp_path)
        else:
            return gspread.service_account()

    # ─── LOAD SHEETS ────────────────────────────────────────

    def _load_sheet(self, sheet_name):
        """Profile Sheet (Header တစ်ကြောင်းပါ) ကို ဖတ်ယူခြင်း"""
        ws = self.spreadsheet.worksheet(sheet_name)
        data = ws.get_all_values()
        if len(data) < 2:
            return []

        # Case-insensitive ဖြစ်စေရန်နှင့် space များကို ရှင်းလင်းထားသော Header keys
        headers = [h.strip() for h in data[0]]
        rows = []
        for row in data[1:]:
            record = {}
            for i, h in enumerate(headers):
                val = row[i].strip() if i < len(row) else ""
                record[h] = val
                # Lowercase key ဖြင့်လည်း သိမ်းဆည်းပေးထားပါသည်
                record[
                    h.lower().replace(" ", "").replace(".", "").replace("_", "")
                ] = val
            rows.append(record)
        return rows

    def _load_monthly_sheet(self, sheet_name, sub_headers):
        """Stock / Testing Sheets (Header နှစ်ကြောင်းပါ) ကို ဖတ်ယူခြင်း"""
        ws = self.spreadsheet.worksheet(sheet_name)
        data = ws.get_all_values()
        if len(data) < 3:
            return [], {}

        header1 = data[0]
        header2 = data[1]

        month_map = {}
        current_month = ""
        months_list = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
            "Yearly Total",
        ]

        for col_idx in range(4, len(header1)):
            h1 = header1[col_idx].strip()
            h2 = header2[col_idx].strip() if col_idx < len(header2) else ""

            if h1 and h1 in months_list:
                current_month = h1
            if current_month and h2:
                month_map[(current_month, h2)] = col_idx

        rows = []
        for row in data[2:]:
            record = {
                "Township": row[0].strip() if len(row) > 0 else "",
                "RHC": row[1].strip() if len(row) > 1 else "",
                "Sub-center": row[2].strip() if len(row) > 2 else "",
                "Village Name": row[3].strip() if len(row) > 3 else "",
                "_raw": row,
            }
            rows.append(record)

        return rows, month_map

    # ─── GETTERS ─────────────────────────────────────────────

    def get_sheet_names(self):
        return ["Profile", "Stock", "Testing"]

    def _get_rows(self, sheet_name):
        if sheet_name == "Profile":
            return self.profile_rows
        elif sheet_name == "Stock":
            return self.stock_rows
        elif sheet_name == "Testing":
            return self.testing_rows
        return []

    def get_townships(self, sheet_name):
        rows = self._get_rows(sheet_name)
        seen = set()
        result = []
        for r in rows:
            t = (
                r.get("Township")
                or r.get("township")
                or r.get("Township Name")
                or r.get("TownshipName")
                or ""
            )
            if t and t not in seen:
                seen.add(t)
                result.append(t)
        return sorted(result)

    def get_rhcs(self, sheet_name, township):
        rows = self._get_rows(sheet_name)
        seen = set()
        result = []
        for r in rows:
            twp = (
                r.get("Township")
                or r.get("township")
                or r.get("Township Name")
                or r.get("TownshipName")
                or ""
            )
            if twp == township:
                v = (
                    r.get("RHC")
                    or r.get("rhc")
                    or r.get("RHC Name")
                    or r.get("RHCName")
                    or ""
                )
                if v and v not in seen:
                    seen.add(v)
                    result.append(v)
        return sorted(result)

    def get_subcenters(self, sheet_name, township, rhc):
        rows = self._get_rows(sheet_name)
        seen = set()
        result = []
        for r in rows:
            twp = (
                r.get("Township")
                or r.get("township")
                or r.get("Township Name")
                or r.get("TownshipName")
                or ""
            )
            cur_rhc = (
                r.get("RHC")
                or r.get("rhc")
                or r.get("RHC Name")
                or r.get("RHCName")
                or ""
            )
            if twp == township and cur_rhc == rhc:
                v = (
                    r.get("Sub-center")
                    or r.get("subcenter")
                    or r.get("Sub Center")
                    or r.get("Sub-Center")
                    or ""
                )
                if v and v not in seen:
                    seen.add(v)
                    result.append(v)
        return sorted(result)

    def get_villages(self, sheet_name, township, rhc, subcenter):
        rows = self._get_rows(sheet_name)
        seen = set()
        result = []
        for r in rows:
            twp = (
                r.get("Township")
                or r.get("township")
                or r.get("Township Name")
                or r.get("TownshipName")
                or ""
            )
            cur_rhc = (
                r.get("RHC")
                or r.get("rhc")
                or r.get("RHC Name")
                or r.get("RHCName")
                or ""
            )
            cur_sub = (
                r.get("Sub-center")
                or r.get("subcenter")
                or r.get("Sub Center")
                or r.get("Sub-Center")
                or ""
            )
            if twp == township and cur_rhc == rhc and cur_sub == subcenter:
                v = (
                    r.get("Village Name")
                    or r.get("villagename")
                    or r.get("Village")
                    or r.get("village")
                    or ""
                )
                if v and v not in seen:
                    seen.add(v)
                    result.append(v)
        return sorted(result)

    def _find_row(self, rows, township, rhc, subcenter, village):
        for r in rows:
            twp = (
                r.get("Township")
                or r.get("township")
                or r.get("Township Name")
                or r.get("TownshipName")
                or ""
            )
            cur_rhc = (
                r.get("RHC")
                or r.get("rhc")
                or r.get("RHC Name")
                or r.get("RHCName")
                or ""
            )
            cur_sub = (
                r.get("Sub-center")
                or r.get("subcenter")
                or r.get("Sub Center")
                or r.get("Sub-Center")
                or ""
            )
            v = (
                r.get("Village Name")
                or r.get("villagename")
                or r.get("Village")
                or r.get("village")
                or ""
            )
            if (
                twp == township
                and cur_rhc == rhc
                and cur_sub == subcenter
                and v == village
            ):
                return r
        return None

    # ─── PROFILE DATA ───────────────────────────────────────

    def get_profile_data(self, township, rhc, subcenter, village):
        row = self._find_row(
            self.profile_rows, township, rhc, subcenter, village
        )
        if not row:
            return {}

        # Provider Name
        provider_name = (
            row.get("Provider Name")
            or row.get("providername")
            or row.get("Provider")
            or row.get("Name")
            or "N/A"
        )

        # Phone Contact
        phone = (
            row.get("Phone Contact")
            or row.get("phonecontact")
            or row.get("Phone Contant")
            or row.get("Phone")
            or row.get("Contact")
            or "N/A"
        )

        # HH (Household)
        hh = row.get("HH") or row.get("hh") or row.get("House Hold") or "N/A"

        # Population
        pop = (
            row.get("Pop")
            or row.get("pop")
            or row.get("Population")
            or row.get("population")
            or "N/A"
        )

        # Provider Type
        prov_type = (
            row.get("Provider Type")
            or row.get("providertype")
            or row.get("Volunteer Type")
            or row.get("volunteertype")
            or row.get("Type")
            or "N/A"
        )

        # Provider Code
        prov_code = (
            row.get("Provider Code")
            or row.get("providercode")
            or row.get("Code No.")
            or row.get("codeno")
            or row.get("Code No")
            or row.get("Code")
            or "N/A"
        )

        return {
            "Provider Name": provider_name if provider_name else "N/A",
            "Phone Contact": phone if phone else "N/A",
            "HH": hh if hh else "N/A",
            "Pop": pop if pop else "N/A",
            "Provider Type": prov_type if prov_type else "N/A",
            "Provider Code": prov_code if prov_code else "N/A",
        }

    # ─── STOCK DATA ──────────────────────────────────────────

    def get_stock_data(self, township, rhc, subcenter, village, month):
        row = self._find_row(
            self.stock_rows, township, rhc, subcenter, village
        )
        if not row:
            return {}

        raw = row["_raw"]
        result = {}
        for sub in ["RDT", "ACT", "CQ", "PQ"]:
            col_idx = self.stock_months.get((month, sub))
            if col_idx is not None and col_idx < len(raw):
                val = raw[col_idx].strip()
                result[sub] = val if val else "-"
            else:
                result[sub] = "-"
        return result

    # ─── TESTING DATA ────────────────────────────────────────

    def get_testing_data(self, township, rhc, subcenter, village, month):
        row = self._find_row(
            self.testing_rows, township, rhc, subcenter, village
        )
        if not row:
            return {}

        raw = row["_raw"]
        result = {}
        for sub in ["Testing", "Pf", "Pv", "Mix", "NTG", "Refer"]:
            col_idx = self.testing_months.get((month, sub))
            if col_idx is not None and col_idx < len(raw):
                val = raw[col_idx].strip()
                result[sub] = val if val else "-"
            else:
                result[sub] = "-"
        return result

    def get_testing_yearly_total(self, township, rhc, subcenter, village):
        row = self._find_row(
            self.testing_rows, township, rhc, subcenter, village
        )
        if not row:
            return {}

        raw = row["_raw"]
        result = {}
        for sub in ["Testing", "Pf", "Pv", "Mix", "NTG", "Refer"]:
            col_idx = self.testing_months.get(("Yearly Total", sub))
            if col_idx is not None and col_idx < len(raw):
                val = raw[col_idx].strip()
                result[sub] = val if val else "-"
            else:
                result[sub] = "-"
        return result
