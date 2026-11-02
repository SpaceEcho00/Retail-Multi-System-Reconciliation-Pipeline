import duckdb
from fastapi import FastAPI

app = FastAPI()
DB = "retail.duckdb"

def q(sql: str):
    con = duckdb.connect(DB, read_only=True)
    try:
        return con.sql(sql).fetchdf().to_dict(orient="records")
    finally:
        con.close()

@app.get("/api/portfolio/abc")
def abc(): return q("SELECT * FROM abc_products ORDER BY revenue DESC")

@app.get("/api/portfolio/margin-volume")
def mv(): return q("SELECT * FROM product_margin_volume")

@app.get("/api/sales/monthly")
def monthly(): return q("SELECT * FROM monthly_sales_margin ORDER BY month")

@app.get("/api/sales/below-cost")
def below_cost(): return q("SELECT * FROM below_cost_sales ORDER BY loss_amount LIMIT 100")

@app.get("/api/stores/scorecard")
def scorecard(): return q("SELECT * FROM store_scorecard ORDER BY revenue_rank")

@app.get("/api/stores/net-revenue")
def net_rev(): return q("SELECT * FROM store_net_revenue ORDER BY net_revenue DESC")

@app.get("/api/trends/seasonal")
def seasonal(): return q("SELECT * FROM seasonal_index ORDER BY month")

@app.get("/api/trends/yoy")
def yoy(): return q("SELECT * FROM yoy_monthly ORDER BY month")