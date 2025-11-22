import os
from flask import Flask, request, jsonify, render_template, send_from_directory
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timedelta, timezone
from werkzeug.utils import secure_filename

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    ZoneInfo = None

# ================== CONFIG ==================

SERVICE_ACCOUNT_FILE = "service_account.json"  # your JSON key
SPREADSHEET_ID = "1KVjWa9t0PreTec_EiF6-XXf1nxJ5CLYmGJ7QDGz844Q"  # your sheet id

EXPENSES_SHEET_NAME = "Expenses"
INCOME_SHEET_NAME = "Income"

TIMEZONE_NAME = "Asia/Kolkata"  # will fallback to +5:30 if not found

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
client = gspread.authorize(creds)

expenses_sheet = client.open_by_key(SPREADSHEET_ID).worksheet(EXPENSES_SHEET_NAME)
income_sheet = client.open_by_key(SPREADSHEET_ID).worksheet(INCOME_SHEET_NAME)

app = Flask(__name__)

# File uploads (for payslips)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_PDF_EXTENSIONS = {"pdf"}

# ================== TIME / FORMAT HELPERS ==================

def get_tz():
    if ZoneInfo is not None:
        try:
            return ZoneInfo(TIMEZONE_NAME)
        except Exception:
            pass
    # fallback fixed offset +5:30
    return timezone(timedelta(hours=5, minutes=30))

def format_timestamp(now: datetime) -> str:
    """Return timestamp like 8/22/2020 14:56:26"""
    return f"{now.month}/{now.day}/{now.year} {now.strftime('%H:%M:%S')}"

def format_pretty_date(d: date) -> str:
    """Return date like 1, Jan, 2026"""
    return f"{d.day}, {d.strftime('%b')}, {d.year}"

def parse_amount(amount_str: str) -> float:
    """Remove commas and return numeric value (float)."""
    raw = (amount_str or "").replace(",", "").strip()
    if not raw:
        raise ValueError("Amount is required")
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"Invalid amount: {amount_str!r}")

def normalize_item(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    return text[0].upper() + text[1:]

# ================== FILE HELPER ==================

def allowed_pdf(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PDF_EXTENSIONS

def save_payslip_file(file_storage):
    """
    Save uploaded payslip PDF and return a URL path (/uploads/filename.pdf).
    Returns empty string if no file or invalid file.
    """
    if not file_storage:
        return ""

    filename = file_storage.filename
    if not filename:
        return ""
    if not allowed_pdf(filename):
        raise ValueError("Payslip must be a PDF file")

    safe_name = secure_filename(filename)
    # to avoid collisions, prefix with timestamp
    tz = get_tz()
    now = datetime.now(tz)
    prefix = now.strftime("%Y%m%d%H%M%S")
    final_name = f"{prefix}_{safe_name}"

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], final_name)
    file_storage.save(file_path)

    # Build URL that can be clicked from the sheet
    # request.host_url like "http://192.168.0.105:5000/"
    base = request.host_url.rstrip("/")
    url = f"{base}/uploads/{final_name}"
    return url

# ================== APPEND LOGIC: EXPENSES ==================

def append_expense_row(
    item: str,
    category: str,
    amount_str: str,
    payment_mode: str,
    card_type: str = "",
    bank_name: str = "",
    upi_provider: str = "",
    purchase_date_str: str | None = None,
    remarks: str = "",
):
    tz = get_tz()
    now = datetime.now(tz)

    timestamp_str = format_timestamp(now)

    # default purchase date = same day as timestamp
    if purchase_date_str:
        try:
            d = datetime.strptime(purchase_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(
                f"Invalid purchase date: {purchase_date_str!r}. Expected YYYY-MM-DD."
            )
    else:
        d = now.date()

    purchase_date_formatted = format_pretty_date(d)
    amount_val = parse_amount(amount_str)

    item_norm = normalize_item(item)
    category = (category or "").strip()
    remarks = (remarks or "").strip()

    if not item_norm:
        raise ValueError("Item is required")
    if not category:
        raise ValueError("Category is required")
    if not payment_mode:
        raise ValueError("Payment mode is required")

    row = [
        timestamp_str,
        item_norm,
        category,
        amount_val,
        payment_mode,
        card_type,
        bank_name,
        upi_provider,
        purchase_date_formatted,
        remarks,
    ]

    expenses_sheet.append_row(row)

# ================== APPEND LOGIC: INCOME ==================

def append_income_row(
    income_source: str,
    amount_str: str,
    income_date_str: str | None = None,
    payslip_url: str = "",
):
    tz = get_tz()
    now = datetime.now(tz)

    timestamp_str = format_timestamp(now)

    # default income date = same day as timestamp
    if income_date_str:
        try:
            d = datetime.strptime(income_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError(
                f"Invalid income date: {income_date_str!r}. Expected YYYY-MM-DD."
            )
    else:
        d = now.date()

    date_formatted = format_pretty_date(d)
    amount_val = parse_amount(amount_str)

    source_norm = normalize_item(income_source)

    if not source_norm:
        raise ValueError("Income source is required")

    row = [
        timestamp_str,
        date_formatted,
        source_norm,
        amount_val,
        payslip_url,
    ]

    income_sheet.append_row(row)

# ================== VALIDATION HELPERS ==================

def validate_single_expense(form: dict) -> list[str]:
    missing = []

    item = (form.get("item") or "").strip()
    category = (form.get("category") or "").strip()
    amount = (form.get("amount") or "").strip()
    payment_mode = (form.get("paymentMode") or "").strip()

    if not item:
        missing.append("Item")
    if not category:
        missing.append("Category")
    if not amount:
        missing.append("Amount")
    if not payment_mode:
        missing.append("Payment Mode")

    if payment_mode == "Card":
        card_type = (form.get("cardType") or "").strip()
        card_bank = (form.get("cardBankName") or "").strip()
        if not card_type:
            missing.append("Card Type (Card)")
        if not card_bank:
            missing.append("Bank (Card)")
    elif payment_mode == "UPI":
        upi_provider = (form.get("upiProvider") or "").strip()
        upi_bank = (form.get("upiBankName") or "").strip()
        upi_card_type = (form.get("upiCardType") or "").strip()
        if not upi_provider:
            missing.append("UPI Provider")
        if not upi_bank:
            missing.append("Bank (UPI)")
        if not upi_card_type:
            missing.append("Card Type (UPI)")

    return missing

def validate_bulk_common(form: dict) -> list[str]:
    missing = []
    payment_mode = (form.get("bulkPaymentMode") or "").strip()

    if not payment_mode:
        missing.append("Bulk Payment Mode")

    if payment_mode == "Card":
        card_type = (form.get("bulkCardType") or "").strip()
        card_bank = (form.get("bulkCardBankName") or "").strip()
        if not card_type:
            missing.append("Bulk Card Type (Card)")
        if not card_bank:
            missing.append("Bulk Bank (Card)")
    elif payment_mode == "UPI":
        upi_provider = (form.get("bulkUpiProvider") or "").strip()
        upi_bank = (form.get("bulkUpiBankName") or "").strip()
        upi_card_type = (form.get("bulkUpiCardType") or "").strip()
        if not upi_provider:
            missing.append("Bulk UPI Provider")
        if not upi_bank:
            missing.append("Bulk Bank (UPI)")
        if not upi_card_type:
            missing.append("Bulk Card Type (UPI)")

    return missing

def validate_income(form: dict) -> list[str]:
    missing = []
    source = (form.get("incomeSource") or "").strip()
    amount = (form.get("incomeAmount") or "").strip()

    if not source:
        missing.append("Income Source")
    if not amount:
        missing.append("Income Amount")

    return missing

# ================== ROUTES ==================

@app.route("/", methods=["GET"])
def index():
    return render_template("app.html")

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    # or explicitly:
    # return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=False)


@app.route("/add", methods=["POST"])
def add():
    try:
        entry_type = request.form.get("entryType", "expense")  # "expense" or "income"

        # ---------- INCOME FLOW ----------
        if entry_type == "income":
            missing = validate_income(request.form)
            if missing:
                msg = "Missing fields: " + ", ".join(missing)
                return jsonify(success=False, error=msg, type="validation"), 400

            income_source = request.form.get("incomeSource", "")
            income_amount_str = request.form.get("incomeAmount", "")
            income_date_str = request.form.get("incomeDate") or None

            payslip_file = request.files.get("payslip")
            payslip_url = ""
            if payslip_file and payslip_file.filename:
                payslip_url = save_payslip_file(payslip_file)

            append_income_row(
                income_source=income_source,
                amount_str=income_amount_str,
                income_date_str=income_date_str,
                payslip_url=payslip_url,
            )

            return jsonify(success=True)

        # ---------- EXPENSE FLOW ----------
        entry_mode = request.form.get("entryMode", "single")

        # ------- SINGLE MODE --------
        if entry_mode == "single":
            missing = validate_single_expense(request.form)
            if missing:
                msg = "Missing fields: " + ", ".join(missing)
                return jsonify(success=False, error=msg, type="validation"), 400

            item = request.form.get("item", "")
            category = request.form.get("category", "")
            amount_str = request.form.get("amount", "")
            payment_mode = request.form.get("paymentMode", "")
            card_type = request.form.get("cardType", "")
            card_bank_name = request.form.get("cardBankName", "")
            upi_bank_name = request.form.get("upiBankName", "")
            upi_provider = request.form.get("upiProvider", "")
            upi_card_type = request.form.get("upiCardType", "")
            purchase_date_str = request.form.get("purchaseDate") or None
            remarks = request.form.get("remarks", "")

            # choose card_type and bank based on mode
            if payment_mode == "Card":
                final_card_type = card_type
                bank_name = card_bank_name
            elif payment_mode == "UPI":
                final_card_type = upi_card_type
                bank_name = upi_bank_name
            else:
                final_card_type = ""
                bank_name = ""

            append_expense_row(
                item=item,
                category=category,
                amount_str=amount_str,
                payment_mode=payment_mode,
                card_type=final_card_type,
                bank_name=bank_name,
                upi_provider=upi_provider,
                purchase_date_str=purchase_date_str,
                remarks=remarks,
            )

        # ------- BULK MODE (row-based) --------
        else:
            missing_common = validate_bulk_common(request.form)
            if missing_common:
                msg = "Missing fields: " + ", ".join(missing_common)
                return jsonify(success=False, error=msg, type="validation"), 400

            # Common fields
            payment_mode = (request.form.get("bulkPaymentMode") or "").strip()
            bulk_card_type = (request.form.get("bulkCardType") or "").strip()
            bulk_card_bank = (request.form.get("bulkCardBankName") or "").strip()
            bulk_upi_provider = (request.form.get("bulkUpiProvider") or "").strip()
            bulk_upi_bank = (request.form.get("bulkUpiBankName") or "").strip()
            bulk_upi_card_type = (request.form.get("bulkUpiCardType") or "").strip()
            bulk_purchase_date = request.form.get("bulkPurchaseDate") or None

            if payment_mode == "Card":
                final_card_type = bulk_card_type
                bank_name = bulk_card_bank
                upi_provider = ""
            elif payment_mode == "UPI":
                final_card_type = bulk_upi_card_type
                bank_name = bulk_upi_bank
                upi_provider = bulk_upi_provider
            else:
                final_card_type = ""
                bank_name = ""
                upi_provider = ""

            # Row-based fields
            items = request.form.getlist("bulkItem[]")
            categories = request.form.getlist("bulkCategory[]")
            amounts = request.form.getlist("bulkAmount[]")
            remarks_list = request.form.getlist("bulkRemarks[]")

            total_rows = max(len(items), len(categories), len(amounts), len(remarks_list))
            if total_rows == 0:
                return jsonify(
                    success=False,
                    error="No bulk rows found. Please add at least one expense row.",
                    type="validation",
                ), 400

            any_row_saved = False

            for i in range(total_rows):
                item = items[i].strip() if i < len(items) else ""
                category = categories[i].strip() if i < len(categories) else ""
                amount_str = amounts[i].strip() if i < len(amounts) else ""
                remarks = remarks_list[i].strip() if i < len(remarks_list) else ""

                # Skip fully empty rows
                if not item and not category and not amount_str and not remarks:
                    continue

                row_missing = []
                if not item:
                    row_missing.append("Item")
                if not category:
                    row_missing.append("Category")
                if not amount_str:
                    row_missing.append("Amount")

                if row_missing:
                    raise ValueError(
                        f"Bulk row {i+1}: missing fields: {', '.join(row_missing)}"
                    )

                append_expense_row(
                    item=item,
                    category=category,
                    amount_str=amount_str,
                    payment_mode=payment_mode,
                    card_type=final_card_type,
                    bank_name=bank_name,
                    upi_provider=upi_provider,
                    purchase_date_str=bulk_purchase_date,
                    remarks=remarks,
                )
                any_row_saved = True

            if not any_row_saved:
                return jsonify(
                    success=False,
                    error="All bulk rows are empty. Please fill at least one row.",
                    type="validation",
                ), 400

        return jsonify(success=True)

    except Exception as e:
        return jsonify(success=False, error=str(e), type="server"), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
