import frappe
from frappe.utils import now_datetime, get_url
from erpnext_ai.settings import get_settings
from erpnext_ai.rag_client import rag_health, rag_chat
import json


@frappe.whitelist(methods=["POST"])
def chat(message: str):
    """
    Widget entrypoint.
    Passes the current site's URL and the logged-in user's identity
    so the AI Agent can:
      1. Look up the correct API credentials (via erp_url)
      2. Keep each user's conversation history separate (via session_id)
    """
    # erp_url  → identifies which credentials to use on the agent side
    erp_url = get_url().rstrip("/")

    # session_id → unique per user per site, so 20 concurrent users never mix history
    session_id = f"{erp_url}::{frappe.session.user}"

    try:
        out = rag_chat(
            message=message,
            erp_url=erp_url,
            session_id=session_id,
            timeout=120,
        )
        answer_text = out.get("response") or out.get("answer") or str(out)

    except Exception as e:
        frappe.log_error(f"AI Agent Error: {e}")
        return {
            "reply": f"Error connecting to AI Agent: {e}",
            "raw": str(e),
        }

    return {
        "reply": answer_text,
        "raw": out,
        "meta": {
            "site":       frappe.local.site,
            "user":       frappe.session.user,
            "session_id": session_id,
            "ts":         now_datetime().isoformat(),
        },
    }


@frappe.whitelist(methods=["GET"])
def get_ai_settings():
    s = get_settings()
    return {
        "enabled":         s.enabled,
        "ollama_url":      s.ollama_url,
        "model":           s.model,
        "timeout_seconds": s.timeout_seconds,
    }


@frappe.whitelist(methods=["GET"])
def ai_health():
    return rag_health(timeout=5)


# ── ERPNext-side report/data methods (called by AI Agent via HTTP) ────────────

@frappe.whitelist()
def get_profit_and_loss(company=None, from_date=None, to_date=None, periodicity="Monthly"):
    if not company:
        company = frappe.defaults.get_user_default("Company") or frappe.get_all("Company", limit=1)[0].name
    if not from_date:
        from_date = frappe.utils.get_first_day(frappe.utils.today())
    if not to_date:
        to_date = frappe.utils.today()
    try:
        income = frappe.db.sql("""
            SELECT account, SUM(debit - credit) as balance
            FROM `tabGL Entry`
            WHERE company=%(company)s AND posting_date BETWEEN %(from_date)s AND %(to_date)s
              AND account IN (SELECT name FROM `tabAccount` WHERE root_type='Income' AND company=%(company)s)
            GROUP BY account ORDER BY balance DESC LIMIT 10
        """, {"company": company, "from_date": from_date, "to_date": to_date}, as_dict=1)

        expenses = frappe.db.sql("""
            SELECT account, SUM(debit - credit) as balance
            FROM `tabGL Entry`
            WHERE company=%(company)s AND posting_date BETWEEN %(from_date)s AND %(to_date)s
              AND account IN (SELECT name FROM `tabAccount` WHERE root_type='Expense' AND company=%(company)s)
            GROUP BY account ORDER BY balance DESC LIMIT 10
        """, {"company": company, "from_date": from_date, "to_date": to_date}, as_dict=1)

        total_income  = sum(abs(i.get("balance", 0)) for i in income)
        total_expense = sum(abs(e.get("balance", 0)) for e in expenses)

        return {"report": "Profit and Loss", "period": f"{from_date} to {to_date}", "company": company,
                "summary": {"total_income": total_income, "total_expenses": total_expense,
                            "net_profit": total_income - total_expense},
                "income_accounts": income, "expense_accounts": expenses}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "P&L Error")
        return {"error": str(e)}


@frappe.whitelist()
def get_balance_sheet(company=None, as_of_date=None):
    if not company:
        company = frappe.defaults.get_user_default("Company") or frappe.get_all("Company", limit=1)[0].name
    if not as_of_date:
        as_of_date = frappe.utils.today()
    try:
        def _query(root_type, sign="debit - credit"):
            return frappe.db.sql(f"""
                SELECT account, SUM({sign}) as balance FROM `tabGL Entry`
                WHERE company=%(company)s AND posting_date<=%(d)s
                  AND account IN (SELECT name FROM `tabAccount` WHERE root_type=%(rt)s AND company=%(company)s)
                GROUP BY account HAVING balance!=0 ORDER BY balance DESC LIMIT 10
            """, {"company": company, "d": as_of_date, "rt": root_type}, as_dict=1)

        assets      = _query("Asset")
        liabilities = _query("Liability", "credit - debit")
        equity      = _query("Equity",    "credit - debit")

        return {"report": "Balance Sheet", "as_of": as_of_date, "company": company,
                "summary": {"total_assets": sum(abs(a["balance"]) for a in assets),
                            "total_liabilities": sum(abs(l["balance"]) for l in liabilities),
                            "total_equity": sum(abs(e["balance"]) for e in equity)},
                "assets": assets, "liabilities": liabilities, "equity": equity}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Balance Sheet Error")
        return {"error": str(e)}


@frappe.whitelist()
def get_accounts_receivable(company=None):
    if not company:
        company = frappe.defaults.get_user_default("Company") or frappe.get_all("Company", limit=1)[0].name
    try:
        receivables = frappe.db.sql("""
            SELECT gle.party as customer_id, c.customer_name,
                   SUM(gle.debit - gle.credit) as outstanding_amount,
                   MAX(gle.posting_date) as last_transaction_date
            FROM `tabGL Entry` gle
            LEFT JOIN `tabCustomer` c ON gle.party = c.name
            WHERE gle.company=%(company)s AND gle.party_type='Customer' AND gle.is_cancelled=0
            GROUP BY gle.party, c.customer_name HAVING outstanding_amount > 0
            ORDER BY outstanding_amount DESC LIMIT 20
        """, {"company": company}, as_dict=1)
        return {"report": "Accounts Receivable", "as_of": frappe.utils.today(), "company": company,
                "total_outstanding": sum(r["outstanding_amount"] for r in receivables),
                "customer_count": len(receivables), "customers": receivables}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "AR Error")
        return {"error": str(e)}


@frappe.whitelist()
def get_top_selling_items(company=None, from_date=None, to_date=None, limit=10):
    if not company:
        company = frappe.defaults.get_user_default("Company") or frappe.get_all("Company", limit=1)[0].name
    if not from_date:
        from_date = frappe.utils.get_first_day(frappe.utils.today())
    if not to_date:
        to_date = frappe.utils.today()
    try:
        items = frappe.db.sql("""
            SELECT soi.item_code, soi.item_name,
                   SUM(soi.qty) as total_qty, SUM(soi.amount) as total_amount,
                   COUNT(DISTINCT so.name) as order_count
            FROM `tabSales Order Item` soi
            JOIN `tabSales Order` so ON soi.parent = so.name
            WHERE so.company=%(company)s AND so.docstatus=1
              AND so.transaction_date BETWEEN %(from_date)s AND %(to_date)s
            GROUP BY soi.item_code, soi.item_name
            ORDER BY total_amount DESC LIMIT %(limit)s
        """, {"company": company, "from_date": from_date, "to_date": to_date, "limit": limit}, as_dict=1)
        return {"report": "Top Selling Items", "period": f"{from_date} to {to_date}",
                "company": company, "items": items}
    except Exception as e:
        return {"error": str(e)}
