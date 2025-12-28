import os
from flask import Flask, request, jsonify, render_template, send_from_directory, Response
from datetime import datetime, timedelta, timezone
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import io
import csv

import psycopg2
import psycopg2.extras

load_dotenv()

# ================== DB (POSTGRESQL ONLY) ==================

def get_db():
    return psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=psycopg2.extras.RealDictCursor,
        sslmode="require"  # REQUIRED for Render
    )

# ================== TIMEZONE ==================

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

TIMEZONE_NAME = "Asia/Kolkata"

def get_tz():
    if ZoneInfo:
        try:
            return ZoneInfo(TIMEZONE_NAME)
        except Exception:
            pass
    return timezone(timedelta(hours=5, minutes=30))

# ================== APP ==================

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ================== HELPERS ==================

def parse_amount(v):
    return float((v or "").replace(",", "").strip())

def normalize(text):
    text = (text or "").strip()
    return text[0].upper() + text[1:] if text else ""

def normalize_or_none(text):
    text = (text or "").strip()
    return text[0].upper() + text[1:] if text else None

def save_payslip(file):
    if not file or not file.filename:
        return ""
    name = secure_filename(file.filename)
    ts = datetime.now(get_tz()).strftime("%Y%m%d%H%M%S")
    final = f"{ts}_{name}"
    path = os.path.join(UPLOAD_FOLDER, final)
    file.save(path)
    return f"{request.host_url.rstrip('/')}/uploads/{final}"

# ================== PAGES ==================

@app.route("/")
def index():
    return render_template("app.html")

@app.route("/records")
def records():
    return render_template("records.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

# ================== DB TEST ==================

@app.route("/_db_test")
def db_test():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS count FROM expenses")
            return {"status": "ok", "expenses": cur.fetchone()["count"]}
    finally:
        conn.close()

# ================== ADD ENTRY ==================

@app.route("/add", methods=["POST"])
def add_entry():
    try:
        entry_type = request.form.get("entryType", "expense")
        if entry_type == "income":
            return add_income()
        entry_mode = request.form.get("entryMode", "single")
        return add_single_expense() if entry_mode == "single" else add_bulk_expenses()
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

# ================== ADD INCOME ==================

def add_income():
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO income (source, amount, income_date, payslip_url, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                normalize(request.form.get("incomeSource")),
                parse_amount(request.form.get("incomeAmount")),
                request.form.get("incomeDate") or datetime.now(get_tz()).date(),
                save_payslip(request.files.get("payslip")),
                datetime.now(get_tz())
            ))
        conn.commit()
        return jsonify(success=True)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# ================== ADD SINGLE EXPENSE ==================

def add_single_expense():
    conn = get_db()
    try:
        payment_mode = normalize(request.form.get("paymentMode"))
        card_type = bank_name = upi_provider = None

        if payment_mode == "Card":
            card_type = normalize_or_none(request.form.get("cardType"))
            bank_name = normalize_or_none(request.form.get("cardBankName"))
        elif payment_mode == "UPI":
            card_type = normalize_or_none(request.form.get("upiCardType"))
            bank_name = normalize_or_none(request.form.get("upiBankName"))
            upi_provider = normalize_or_none(request.form.get("upiProvider"))

        with conn.cursor() as c:
            c.execute("""
                INSERT INTO expenses
                (item, category, amount, payment_mode, card_type, bank_name,
                 upi_provider, purchase_date, remarks, created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                normalize(request.form.get("item")),
                normalize(request.form.get("category")),
                parse_amount(request.form.get("amount")),
                payment_mode,
                card_type,
                bank_name,
                upi_provider,
                request.form.get("purchaseDate") or datetime.now(get_tz()).date(),
                request.form.get("remarks", ""),
                datetime.now(get_tz())
            ))
        conn.commit()
        return jsonify(success=True)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# ================== ADD BULK EXPENSE ==================

def add_bulk_expenses():
    conn = get_db()
    try:
        payment_mode = normalize(request.form.get("bulkPaymentMode"))
        purchase_date = request.form.get("bulkPurchaseDate") or datetime.now(get_tz()).date()

        card_type = bank_name = upi_provider = None
        if payment_mode == "Card":
            card_type = normalize_or_none(request.form.get("bulkCardType"))
            bank_name = normalize_or_none(request.form.get("bulkCardBankName"))
        elif payment_mode == "UPI":
            card_type = normalize_or_none(request.form.get("bulkUpiCardType"))
            bank_name = normalize_or_none(request.form.get("bulkUpiBankName"))
            upi_provider = normalize_or_none(request.form.get("bulkUpiProvider"))

        items = request.form.getlist("bulkItem[]")
        categories = request.form.getlist("bulkCategory[]")
        amounts = request.form.getlist("bulkAmount[]")
        remarks = request.form.getlist("bulkRemarks[]")

        with conn.cursor() as c:
            for i in range(len(items)):
                c.execute("""
                    INSERT INTO expenses
                    (item, category, amount, payment_mode, card_type, bank_name,
                     upi_provider, purchase_date, remarks, created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (
                    normalize(items[i]),
                    normalize(categories[i]),
                    parse_amount(amounts[i]),
                    payment_mode,
                    card_type,
                    bank_name,
                    upi_provider,
                    purchase_date,
                    remarks[i] if i < len(remarks) else "",
                    datetime.now(get_tz())
                ))
        conn.commit()
        return jsonify(success=True)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# ================== READ / UPDATE / DELETE ==================

@app.route("/api/expenses")
def api_expenses():
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT * FROM expenses ORDER BY created_at DESC")
            return jsonify(c.fetchall())
    finally:
        conn.close()

@app.route("/api/income")
def api_income():
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("SELECT * FROM income ORDER BY created_at DESC")
            return jsonify(c.fetchall())
    finally:
        conn.close()

@app.route("/api/expenses/<int:id>", methods=["DELETE"])
def delete_expense(id):
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("DELETE FROM expenses WHERE id=%s", (id,))
        conn.commit()
        return jsonify(success=True)
    finally:
        conn.close()

@app.route("/api/income/<int:id>", methods=["DELETE"])
def delete_income(id):
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("DELETE FROM income WHERE id=%s", (id,))
        conn.commit()
        return jsonify(success=True)
    finally:
        conn.close()

# ================== Download CSV (Expenses) ==================
@app.route("/export/csv/expenses")
def export_csv_expenses():
    month_param = request.args.get("month", "all")
    year_param = request.args.get("year", "all")

    conn = get_db()
    try:
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Build WHERE clause based on filters
        expenses_where = []
        expenses_params = []
        
        if month_param != "all":
            month = int(month_param)
            expenses_where.append("EXTRACT(MONTH FROM purchase_date)=%s")
            expenses_params.append(month)
        
        if year_param != "all":
            year = int(year_param)
            expenses_where.append("EXTRACT(YEAR FROM purchase_date)=%s")
            expenses_params.append(year)
        
        expenses_query = "SELECT purchase_date, item, category, amount, payment_mode, card_type, bank_name, upi_provider, remarks FROM expenses"
        if expenses_where:
            expenses_query += " WHERE " + " AND ".join(expenses_where)
        expenses_query += " ORDER BY purchase_date"
        
        # Write Expenses Headers
        writer.writerow([
            'Date', 'Item', 'Category', 'Amount',
            'Payment Mode', 'Card Type', 'Bank', 'UPI Provider', 'Remarks'
        ])

        with conn.cursor() as c:
            c.execute(expenses_query, expenses_params)
            for r in c.fetchall():
                writer.writerow([
                    r["purchase_date"],
                    r["item"],
                    r["category"],
                    r["amount"],
                    r["payment_mode"],
                    r["card_type"] or "",
                    r["bank_name"] or "",
                    r["upi_provider"] or "",
                    r["remarks"] or ""
                ])

        # Generate filename based on filters
        if month_param != "all" and year_param != "all":
            month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            month_name = month_names[int(month_param)]
            filename = f"Expenses_{year_param}_{month_name}.csv"
        elif month_param != "all":
            month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            month_name = month_names[int(month_param)]
            filename = f"Expenses_AllYears_{month_name}.csv"
        elif year_param != "all":
            filename = f"Expenses_{year_param}_AllMonths.csv"
        else:
            filename = f"Expenses_All_Data.csv"

        # Return CSV
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )

    finally:
        conn.close()


# ================== Download CSV (Income) ==================
@app.route("/export/csv/income")
def export_csv_income():
    month_param = request.args.get("month", "all")
    year_param = request.args.get("year", "all")

    conn = get_db()
    try:
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Build WHERE clause based on filters
        income_where = []
        income_params = []
        
        if month_param != "all":
            month = int(month_param)
            income_where.append("EXTRACT(MONTH FROM income_date)=%s")
            income_params.append(month)
        
        if year_param != "all":
            year = int(year_param)
            income_where.append("EXTRACT(YEAR FROM income_date)=%s")
            income_params.append(year)
        
        income_query = "SELECT income_date, source, amount, payslip_url FROM income"
        if income_where:
            income_query += " WHERE " + " AND ".join(income_where)
        income_query += " ORDER BY income_date"
        
        # Write Income Headers
        writer.writerow(['Date', 'Source', 'Amount', 'Payslip URL'])

        with conn.cursor() as c:
            c.execute(income_query, income_params)
            for r in c.fetchall():
                writer.writerow([
                    r["income_date"],
                    r["source"],
                    r["amount"],
                    r["payslip_url"] or ""
                ])

        # Generate filename based on filters
        if month_param != "all" and year_param != "all":
            month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            month_name = month_names[int(month_param)]
            filename = f"Income_{year_param}_{month_name}.csv"
        elif month_param != "all":
            month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']
            month_name = month_names[int(month_param)]
            filename = f"Income_AllYears_{month_name}.csv"
        elif year_param != "all":
            filename = f"Income_{year_param}_AllMonths.csv"
        else:
            filename = f"Income_All_Data.csv"

        # Return CSV
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )

    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True)