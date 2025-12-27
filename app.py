import os
from flask import Flask, request, jsonify, render_template, send_from_directory
from datetime import datetime, timedelta, timezone
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import pymysql

load_dotenv()

# ================== DB ==================

def get_db():
    return pymysql.connect(
        host=os.environ["MYSQL_HOST"],
        port=int(os.environ.get("MYSQL_PORT", 3306)),
        user=os.environ["MYSQL_USER"],
        password=os.environ["MYSQL_PASSWORD"],
        database=os.environ["MYSQL_DB"],
        connect_timeout=5,
        autocommit=False,
        cursorclass=pymysql.cursors.DictCursor
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
    """Returns normalized text or None if empty - for ENUM fields"""
    text = (text or "").strip()
    return (text[0].upper() + text[1:]) if text else None

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

# ================== ADD ENDPOINT ==================

@app.route("/add", methods=["POST"])
def add_entry():
    try:
        entry_type = request.form.get("entryType", "expense")
        
        if entry_type == "income":
            return add_income()
        else:
            entry_mode = request.form.get("entryMode", "single")
            if entry_mode == "single":
                return add_single_expense()
            else:
                return add_bulk_expenses()
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

def add_income():
    conn = get_db()
    try:
        source = normalize(request.form.get("incomeSource", ""))
        amount = parse_amount(request.form.get("incomeAmount", "0"))
        income_date = request.form.get("incomeDate") or datetime.now(get_tz()).strftime("%Y-%m-%d")
        
        payslip_url = ""
        if "payslip" in request.files:
            payslip_url = save_payslip(request.files["payslip"])
        
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO income (source, amount, income_date, payslip_url, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (source, amount, income_date, payslip_url, datetime.now(get_tz())))
        
        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()

def add_single_expense():
    conn = get_db()
    try:
        item = normalize(request.form.get("item", ""))
        category = normalize(request.form.get("category", ""))
        amount = parse_amount(request.form.get("amount", "0"))
        payment_mode = normalize(request.form.get("paymentMode", ""))
        purchase_date = request.form.get("purchaseDate") or datetime.now(get_tz()).strftime("%Y-%m-%d")
        remarks = request.form.get("remarks", "").strip()
        
        bank_name = None
        card_type = None
        provider = None
        
        if payment_mode == "Card":
            card_type = normalize_or_none(request.form.get("cardType", ""))
            bank_name = normalize(request.form.get("cardBankName", "")) or None
        elif payment_mode == "UPI":
            provider = normalize(request.form.get("upiProvider", "")) or None
            bank_name = normalize(request.form.get("upiBankName", "")) or None
            card_type = normalize_or_none(request.form.get("upiCardType", ""))
        
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO expenses 
                (item, category, amount, payment_mode, card_type, bank_name, 
                 upi_provider, purchase_date, remarks, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (item, category, amount, payment_mode, card_type, bank_name,
                  provider, purchase_date, remarks, datetime.now(get_tz())))
        
        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()

def add_bulk_expenses():
    conn = get_db()
    try:
        payment_mode = normalize(request.form.get("bulkPaymentMode", ""))
        purchase_date = request.form.get("bulkPurchaseDate") or datetime.now(get_tz()).strftime("%Y-%m-%d")
        
        bank_name = None
        card_type = None
        provider = None
        
        if payment_mode == "Card":
            card_type = normalize_or_none(request.form.get("bulkCardType", ""))
            bank_name = normalize(request.form.get("bulkCardBankName", "")) or None
        elif payment_mode == "UPI":
            provider = normalize(request.form.get("bulkUpiProvider", "")) or None
            bank_name = normalize(request.form.get("bulkUpiBankName", "")) or None
            card_type = normalize_or_none(request.form.get("bulkUpiCardType", ""))
        
        items = request.form.getlist("bulkItem[]")
        categories = request.form.getlist("bulkCategory[]")
        amounts = request.form.getlist("bulkAmount[]")
        remarks_list = request.form.getlist("bulkRemarks[]")
        
        with conn.cursor() as c:
            for i in range(len(items)):
                item = normalize(items[i])
                category = normalize(categories[i])
                amount = parse_amount(amounts[i])
                remarks = remarks_list[i].strip() if i < len(remarks_list) else ""
                
                c.execute("""
                    INSERT INTO expenses 
                    (item, category, amount, payment_mode, card_type, bank_name,
                     upi_provider, purchase_date, remarks, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (item, category, amount, payment_mode, card_type, bank_name,
                      provider, purchase_date, remarks, datetime.now(get_tz())))
        
        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()

# ================== READ APIs ==================

@app.route("/api/expenses")
def api_expenses():
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT 
                  id,
                  item,
                  amount,
                  purchase_date,
                  payment_mode,
                  bank_name,
                  card_type,
                  upi_provider,
                  remarks
                FROM expenses
                ORDER BY created_at DESC
            """)
            return jsonify(c.fetchall())
    finally:
        conn.close()

@app.route("/api/income")
def api_income():
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("""
                SELECT 
                  id,
                  source,
                  amount,
                  income_date
                FROM income
                ORDER BY created_at DESC
            """)
            return jsonify(c.fetchall())
    finally:
        conn.close()

# ================== DELETE ==================

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

# ================== UPDATE ==================

@app.route("/api/expenses/<int:id>", methods=["PUT"])
def update_expense(id):
    d = request.json
    conn = get_db()
    try:
        payment_mode = d.get("payment_mode", "Cash")
        card_type = normalize_or_none(d.get("card_type"))
        bank_name = d.get("bank_name") or None
        upi_provider = d.get("upi_provider") or None
        
        with conn.cursor() as c:
            c.execute("""
                UPDATE expenses
                SET item=%s, amount=%s, payment_mode=%s, card_type=%s, 
                    bank_name=%s, upi_provider=%s, remarks=%s
                WHERE id=%s
            """, (d["item"], d["amount"], payment_mode, card_type, 
                  bank_name, upi_provider, d.get("remarks", ""), id))
        conn.commit()
        return jsonify(success=True)
    except Exception as e:
        conn.rollback()
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()

@app.route("/api/income/<int:id>", methods=["PUT"])
def update_income(id):
    d = request.json
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute("""
                UPDATE income
                SET source=%s, amount=%s
                WHERE id=%s
            """, (d["item"], d["amount"], id))
        conn.commit()
        return jsonify(success=True)
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True)