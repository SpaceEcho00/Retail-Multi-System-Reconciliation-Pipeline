from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
import duckdb

app = FastAPI(title="Retail Reconciliation & Analytics API")

# --- MySQL (reconciliation state) ---
DB = dict(host="localhost", user="root", password="root", database="retail")

def get_conn():
    return mysql.connector.connect(**DB)

def q(sql, params=None):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    cur.close(); conn.close()
    return rows

def execute(sql, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    conn.commit()
    affected = cur.rowcount
    cur.close(); conn.close()
    return affected

# --- DuckDB (analysis tables) ---
DUCK_PATH = "retail.duckdb"   # use full path if not in the same folder as api.py

def dq(sql):
    con = duckdb.connect(DUCK_PATH, read_only=True)
    try:
        return con.sql(sql).fetchdf().to_dict(orient="records")
    finally:
        con.close()

# ================= RECONCILIATION ENDPOINTS =================

@app.get("/api/overview")
def overview():
    return q("""
        SELECT
          COUNT(*) AS total_exceptions,
          SUM(status = 'open') AS open_exceptions,
          SUM(status = 'resolved') AS resolved_exceptions,
          ROUND(COALESCE(SUM(amount_at_risk), 0), 2) AS total_at_risk,
          ROUND(COALESCE(SUM(CASE WHEN status='open' THEN amount_at_risk END), 0), 2) AS open_at_risk
        FROM reconciliation_exception
    """)[0]

@app.get("/api/exceptions")
def exceptions(rule_code: str = None, status: str = None, limit: int = 200):
    where, params = [], []
    if rule_code: where.append("rule_code = %s"); params.append(rule_code)
    if status:    where.append("status = %s");    params.append(status)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)
    return q(f"""
        SELECT exception_id, rule_code, entity_id, transaction_id, store_id,
               amount_at_risk, severity, status, detected_at
        FROM reconciliation_exception
        {clause}
        ORDER BY detected_at DESC, amount_at_risk DESC
        LIMIT %s
    """, params)

@app.get("/api/exceptions/by-rule")
def by_rule():
    return q("""
        SELECT rule_code, COUNT(*) AS count,
               ROUND(SUM(amount_at_risk), 2) AS total_at_risk
        FROM reconciliation_exception
        GROUP BY rule_code ORDER BY total_at_risk DESC
    """)

@app.get("/api/runs")
def runs(limit: int = 50):
    return q("""
        SELECT a.audit_id, t.task_code, a.status, a.run_started_at,
               a.run_finished_at, a.exceptions_found, a.total_at_risk
        FROM reconciliation_audit a
        JOIN reconciliation_task t ON a.task_id = t.task_id
        ORDER BY a.run_started_at DESC LIMIT %s
    """, [limit])

class ResolvePayload(BaseModel):
    resolved_by: str
    resolution_note: str = ""

@app.post("/api/exceptions/{exception_id}/resolve")
def resolve(exception_id: int, payload: ResolvePayload):
    affected = execute("""
        UPDATE reconciliation_exception
        SET status='resolved', resolved_at=NOW(), resolved_by=%s, resolution_note=%s
        WHERE exception_id=%s AND status='open'
    """, (payload.resolved_by, payload.resolution_note, exception_id))
    if affected == 0:
        raise HTTPException(404, "Exception not found or already resolved")
    return {"ok": True, "exception_id": exception_id}

# ================= ANALYTICS ENDPOINTS =================

@app.get("/api/analytics/abc")
def abc():
    return dq("SELECT * FROM abc_products ORDER BY revenue DESC")

@app.get("/api/analytics/margin-volume")
def margin_volume():
    return dq("SELECT * FROM product_margin_volume")

@app.get("/api/analytics/monthly")
def monthly():
    return dq("SELECT * FROM monthly_sales_margin ORDER BY month")

@app.get("/api/analytics/stores")
def stores():
    return dq("SELECT * FROM store_scorecard ORDER BY revenue_rank")

@app.get("/api/analytics/net-revenue")
def net_revenue():
    return dq("SELECT * FROM store_net_revenue ORDER BY net_revenue DESC")

@app.get("/api/analytics/seasonal")
def seasonal():
    return dq("SELECT * FROM seasonal_index ORDER BY month")

@app.get("/api/analytics/yoy")
def yoy():
    return dq("SELECT * FROM yoy_monthly ORDER BY month")

@app.get("/api/analytics/below-cost")
def below_cost():
    return dq("SELECT * FROM below_cost_sales ORDER BY loss_amount LIMIT 200")