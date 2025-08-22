import os
from decimal import Decimal, InvalidOperation

from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from .payu import PayUClient

from .db import get_setting, set_setting, add_payment_transaction, get_all_transactions
from fastapi import Response, status
from fastapi.responses import RedirectResponse
from fastapi import Cookie
import secrets

def load_settings():
  pos_id = get_setting("PAYU_POS_ID")
  client_secret = get_setting("PAYU_CLIENT_SECRET")
  app_base_url = get_setting("APP_BASE_URL") or "http://localhost:8000"
  return pos_id, client_secret, app_base_url

def save_settings(pos_id, client_secret, app_base_url):
  set_setting("PAYU_POS_ID", pos_id)
  set_setting("PAYU_CLIENT_SECRET", client_secret)
  set_setting("APP_BASE_URL", app_base_url)

POS_ID, CLIENT_SECRET, APP_BASE_URL = load_settings()
payu = None
if POS_ID and CLIENT_SECRET:
  payu = PayUClient(POS_ID, CLIENT_SECRET, APP_BASE_URL)


from fastapi.responses import Response
from fastapi.exception_handlers import RequestValidationError
from fastapi.exceptions import HTTPException as FastAPIHTTPException

app = FastAPI(title="PayU Starter")

# Custom error handler for HTTPException
@app.exception_handler(FastAPIHTTPException)
async def custom_http_exception_handler(request, exc):
    return HTMLResponse(
        f"""
        <html>
          <head>
            <title>Error</title>
            <style>
              body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f7f7f7; margin: 0; padding: 0; }}
               .container {{ max-width: 900px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #0001; padding: 32px; }}
              h2 {{ color: #c0392b; margin-bottom: 16px; }}
              .msg {{ color: #34495e; font-size: 1.1em; margin-bottom: 24px; }}
              a {{ color: #2980b9; text-decoration: none; font-size: 0.95em; }}
              a:hover {{ text-decoration: underline; }}
            </style>
          </head>
          <body>
            <div class="container">
              <h2>Error {exc.status_code}</h2>
              <div class="msg">{exc.detail}</div>
              <a href="/">← Back to Home</a>
            </div>
          </body>
        </html>
        """,
        status_code=exc.status_code
    )

# --- Admin login helpers ---
ADMIN_SESSION_KEY = "admin_session"
ADMIN_PASSWORD_KEY = "ADMIN_PASSWORD"

def is_admin_logged_in(session: str = None):
    admin_session = get_setting(ADMIN_SESSION_KEY)
    return session and admin_session and secrets.compare_digest(session, admin_session)

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page():
    return """
    <html>
      <head>
        <title>Admin Login</title>
        <style>
          body { font-family: 'Segoe UI', Arial, sans-serif; background: #f7f7f7; }
           .container { max-width: 900px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #0001; padding: 32px; }
          h2 { color: #2c3e50; margin-bottom: 24px; }
          label { display: block; margin-bottom: 12px; font-weight: 500; color: #34495e; }
          input[type='password'] { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; margin-top: 4px; margin-bottom: 16px; font-size: 1em; }
          button { background: #2980b9; color: #fff; border: none; padding: 10px 24px; border-radius: 4px; font-size: 1em; cursor: pointer; transition: background 0.2s; }
          button:hover { background: #3498db; }
        </style>
      </head>
      <body>
        <div class="container">
          <h2>Admin Login</h2>
          <form method='post' action='/admin/login'>
            <label>Password:
              <input type='password' name='password' placeholder='Enter admin password'/>
            </label>
            <button type='submit'>Login</button>
          </form>
        </div>
      </body>
    </html>
    """

@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    form = await request.form()
    password = form.get("password", "")
    admin_password = get_setting(ADMIN_PASSWORD_KEY)
    if not admin_password:
        # First login sets the password
        set_setting(ADMIN_PASSWORD_KEY, password)
        admin_password = password
    if secrets.compare_digest(password, admin_password):
        session_token = secrets.token_urlsafe(32)
        set_setting(ADMIN_SESSION_KEY, session_token)
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(key="admin_session", value=session_token, httponly=True, max_age=3600)
        return response
    return HTMLResponse(
        """
        <html>
          <head>
            <title>Admin Login - PayU Starter</title>
            <style>
              body { font-family: 'Segoe UI', Arial, sans-serif; background: #f7f7f7; margin: 0; padding: 0; }
              .container { max-width: 900px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #0001; padding: 32px; }
              h2 { color: #c0392b; margin-bottom: 24px; }
              p { color: #34495e; font-size: 1.1em; margin-bottom: 24px; }
              a { color: #2980b9; text-decoration: none; font-size: 1.1em; font-weight: 500; }
              a:hover { text-decoration: underline; }
            </style>
          </head>
          <body>
            <div class="container">
              <h2>Login failed</h2>
              <p>Incorrect password.</p>
              <a href='/admin/login'>Try again</a>
            </div>
          </body>
        </html>
        """,
        status_code=401
    )

@app.get("/admin/logout", response_class=HTMLResponse)
async def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("admin_session")
    return response

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request, admin_session: str = Cookie(None)):
    if not is_admin_logged_in(admin_session):
        return RedirectResponse(url="/admin/login", status_code=303)
    pos_id, client_secret, app_base_url = load_settings()
    return f"""
    <html>
      <head>
        <title>Admin Settings</title>
        <style>
          body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f7f7f7; margin: 0; padding: 0; }}
           .container {{ max-width: 900px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #0001; padding: 32px; }}
          h2 {{ color: #2c3e50; margin-bottom: 24px; }}
          label {{ display: block; margin-bottom: 12px; font-weight: 500; color: #34495e; }}
          input[type='text'] {{ width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; margin-top: 4px; margin-bottom: 16px; font-size: 1em; }}
          button {{ background: #2980b9; color: #fff; border: none; padding: 10px 24px; border-radius: 4px; font-size: 1em; cursor: pointer; transition: background 0.2s; }}
          button:hover {{ background: #3498db; }}
          .back {{ display: inline-block; margin-top: 24px; color: #2980b9; text-decoration: none; font-size: 0.95em; }}
          .back:hover {{ text-decoration: underline; }}
          .tab {{ display: inline-block; margin-right: 16px; color: #2980b9; text-decoration: none; font-size: 1em; font-weight: 500; }}
          .tab:hover {{ text-decoration: underline; }}
          .logout {{ float: right; color: #c0392b; text-decoration: none; font-size: 0.95em; font-weight: 500; margin-top: 8px; }}
          .logout:hover {{ text-decoration: underline; }}
        </style>
      </head>
      <body>
        <div class="container">
          <h2>PayU Settings (Admin)
            <a class="logout" href="/admin/logout">Logout</a>
          </h2>
          <div style="margin-bottom: 24px;">
            <a class="tab" href="/admin">Settings</a>
            <a class="tab" href="/admin/transactions">Transactions</a>
          </div>
          <form method='post' action='/admin'>
            <label>PAYU_POS_ID:
              <input type='text' name='pos_id' value='{pos_id}' placeholder='Enter POS ID'/>
            </label>
            <label>PAYU_CLIENT_SECRET:
              <input type='text' name='client_secret' value='{client_secret}' placeholder='Enter Client Secret'/>
            </label>
            <label>APP_BASE_URL:
              <input type='text' name='app_base_url' value='{app_base_url}' placeholder='http://localhost:8000'/>
            </label>
            <button type='submit'>Save Settings</button>
          </form>
          <a class='back' href='/'>← Back to Home</a>
        </div>
      </body>
    </html>
    """

@app.post("/admin", response_class=HTMLResponse)
async def admin_save(request: Request, admin_session: str = Cookie(None)):
  if not is_admin_logged_in(admin_session):
    return RedirectResponse(url="/admin/login", status_code=303)
  form = await request.form()
  pos_id = form.get("pos_id", "")
  client_secret = form.get("client_secret", "")
  app_base_url = form.get("app_base_url", "http://localhost:8000")
  save_settings(pos_id, client_secret, app_base_url)
  # Reload settings and PayUClient
  global POS_ID, CLIENT_SECRET, APP_BASE_URL, payu
  POS_ID, CLIENT_SECRET, APP_BASE_URL = load_settings()
  payu = None
  if POS_ID and CLIENT_SECRET:
    payu = PayUClient(POS_ID, CLIENT_SECRET, APP_BASE_URL)
  return RedirectResponse(url="/admin", status_code=303)



@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <html>
      <head>
        <title>PayU Starter</title>
        <style>
          body { font-family: 'Segoe UI', Arial, sans-serif; background: #f7f7f7; margin: 0; padding: 0; }
          .container { max-width: 900px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #0001; padding: 32px; }
          h1 { color: #2c3e50; margin-bottom: 24px; }
          p { color: #34495e; font-size: 1.1em; margin-bottom: 24px; }
          .links { margin-top: 32px; }
          a { display: inline-block; margin-right: 24px; color: #2980b9; text-decoration: none; font-size: 1.1em; font-weight: 500; }
          a:hover { text-decoration: underline; }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>PayU Starter</h1>
          <p>
            Welcome to PayU Starter, a FastAPI MVP for integrating PayU payments.<br>
            <b>Note:</b> You must first <a href='https://secure.snd.payu.com/'>register for a PayU account</a> and obtain sandbox credentials before using this app.<br>
            Use the links below to create a payment or manage settings and review transactions in the admin panel.
          </p>
          <div class="links">
            <a href="/pay">Create Payment</a>
            <a href="/admin">Admin Panel</a>
          </div>
        </div>
      </body>
    </html>
    """

@app.get("/pay", response_class=HTMLResponse)
async def pay_page():
    if not POS_ID or not CLIENT_SECRET:
        return """
        <html>
          <head>
            <title>PayU Starter - Setup Required</title>
            <style>
              body { font-family: 'Segoe UI', Arial, sans-serif; background: #f7f7f7; margin: 0; padding: 0; }
               .container { max-width: 900px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #0001; padding: 32px; }
              h2 { color: #c0392b; margin-bottom: 24px; }
              p { color: #34495e; font-size: 1.1em; }
              a { color: #2980b9; text-decoration: none; }
              a:hover { text-decoration: underline; }
            </style>
          </head>
          <body>
            <div class="container">
              <h2>PayU Starter - Setup Required</h2>
              <p>PayU credentials are not set.</p>
              <p>Please go to <a href='/admin'>Admin Settings</a> to configure PAYU_POS_ID and PAYU_CLIENT_SECRET.</p>
            </div>
          </body>
        </html>
        """
    return """
    <html>
      <head>
        <title>PayU Starter - Create Payment</title>
        <style>
          body { font-family: 'Segoe UI', Arial, sans-serif; background: #f7f7f7; margin: 0; padding: 0; }
          .container { max-width: 900px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #0001; padding: 32px; }
          h2 { color: #2c3e50; margin-bottom: 24px; }
          label { display: block; margin-bottom: 12px; font-weight: 500; color: #34495e; }
          input[type='text'] { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; margin-top: 4px; margin-bottom: 16px; font-size: 1em; }
          button { background: #27ae60; color: #fff; border: none; padding: 10px 24px; border-radius: 4px; font-size: 1em; cursor: pointer; transition: background 0.2s; }
          button:hover { background: #2ecc71; }
          .info { color: #7f8c8d; font-size: 0.95em; margin-top: 16px; }
          .admin-link { display: inline-block; margin-top: 24px; color: #2980b9; text-decoration: none; font-size: 0.95em; }
          .admin-link:hover { text-decoration: underline; }
        </style>
      </head>
      <body>
        <div class="container">
          <h2>Create PayU Payment (Sandbox)</h2>
          <form method="post" action="/pay">
            <label>Amount (PLN):
              <input type="text" name="amount_pln" value="12.34" placeholder="e.g. 12.34" />
            </label>
            <label>Description:
              <input type="text" name="description" value="Test payment" size="40" placeholder="e.g. Test payment"/>
            </label>
            <button type="submit">Pay with PayU</button>
          </form>
          <div class="info">After payment, you will be redirected back to <b>/return</b>.</div>
          <a class="admin-link" href="/admin">Admin Settings</a>
        </div>
      </body>
    </html>
    """


def pln_to_grosze(amount_pln_str: str) -> int:
  try:
    dec = Decimal(amount_pln_str).quantize(Decimal("0.01"))
    return int(dec * 100)
  except (InvalidOperation, ValueError):
    raise HTTPException(status_code=400, detail="Invalid amount")


@app.post("/pay")
async def create_payment(amount_pln: str = Form(...), description: str = Form("Order")):
  if not payu:
    raise HTTPException(status_code=503, detail="PayU credentials not set. Please configure in /admin.")
  total_amount_grosze = pln_to_grosze(amount_pln)
  try:
    res = payu.create_order(
      total_amount_grosze=total_amount_grosze,
      description=description or "Order",
      product_name=description or "Order",
    )
  except Exception as e:
    add_payment_transaction(order_id=None, amount=total_amount_grosze, description=description, status=f"ERROR: {e}")
    raise HTTPException(status_code=502, detail=f"PayU error: {e}")

  status = res.get("status", {}).get("statusCode")
  order_id = res.get("orderId")
  if status != "SUCCESS":
    add_payment_transaction(order_id=order_id, amount=total_amount_grosze, description=description, status=f"PayU status: {status}")
    raise HTTPException(status_code=502, detail=f"PayU status: {status}")

  redirect_uri = res.get("redirectUri")
  if not redirect_uri:
    add_payment_transaction(order_id=order_id, amount=total_amount_grosze, description=description, status="Missing redirectUri")
    raise HTTPException(status_code=502, detail="Missing redirectUri from PayU")

  add_payment_transaction(order_id=order_id, amount=total_amount_grosze, description=description, status="SUCCESS")
  response = RedirectResponse(url=redirect_uri, status_code=303)
  response.set_cookie("payu_order_id", order_id or "", max_age=3600, httponly=True)
  return response
# --- Admin login helpers ---
@app.get("/admin/transactions", response_class=HTMLResponse)
async def admin_transactions(admin_session: str = Cookie(None)):
    if not is_admin_logged_in(admin_session):
        return RedirectResponse(url="/admin/login", status_code=303)
    txs = get_all_transactions()
    rows = "".join([
        f"<tr><td>{tx.id}</td><td>{tx.order_id or ''}</td><td>{tx.amount/100:.2f} PLN</td><td>{tx.description}</td><td>{tx.status}</td><td>{tx.created_at.strftime('%Y-%m-%d %H:%M:%S')}</td></tr>"
        for tx in txs
    ])
    return f"""
    <html>
      <head>
        <title>Payment Transactions</title>
        <style>
          body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f7f7f7; }}
          .container {{ max-width: 900px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #0001; padding: 32px; }}
          h2 {{ color: #2c3e50; margin-bottom: 24px; }}
          table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
          th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
          th {{ background: #2980b9; color: #fff; }}
          tr:nth-child(even) {{ background: #f2f2f2; }}
          .back {{ display: inline-block; margin-top: 24px; color: #2980b9; text-decoration: none; font-size: 0.95em; }}
          .back:hover {{ text-decoration: underline; }}
        </style>
      </head>
      <body>
        <div class="container">
          <h2>Payment Transactions</h2>
          <table>
            <tr><th>ID</th><th>Order ID</th><th>Amount</th><th>Description</th><th>Status</th><th>Created At</th></tr>
            {rows}
          </table>
          <a class='back' href='/admin'>← Back to Admin</a>
        </div>
      </body>
    </html>
    """


@app.post("/payu/notify")
async def payu_notify(request: Request):
    body = await request.body()
    signature = request.headers.get("OpenPayU-Signature", "")
    return PlainTextResponse("OK")


@app.get("/return", response_class=HTMLResponse)
async def return_page(request: Request):
    order_id = request.cookies.get("payu_order_id", "")
    return f"""
    <html>
      <body style=\"font-family: sans-serif;\">
        <h2>Payment flow finished (sandbox)</h2>
        <p>Order ID (if known): {order_id}</p>
        <p>Check your PayU sandbox panel for final status.</p>
        <p><a href=\"/\">Back</a></p>
      </body>
    </html>
    """
