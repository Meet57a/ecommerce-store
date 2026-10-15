# E-commerce Store

An e-commerce foundation built with Python, Django, Django Templates, Bootstrap 5, and SQLite.

## Planned apps

The project will grow through separate Django apps:

- `core` - homepage and shared pages (implemented)
- `accounts` - customer accounts and profiles
- `catalog` - products and categories
- `cart` - shopping cart and checkout
- `orders` - orders and order items
- `payments` - Razorpay integration
- `coupons` - discounts and coupon management
- `notifications` - idempotent order and payment email notifications

The current implementation includes all planned apps, plus wishlist and product reviews.

## Setup

Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create the local database and verify the project:

```powershell
python manage.py migrate
python manage.py check
python manage.py test
```

Start the development server:

```powershell
python manage.py runserver
```

Open <http://127.0.0.1:8000/> in a browser. The Django admin is available at
<http://127.0.0.1:8000/admin/> after creating a superuser with
`python manage.py createsuperuser`.

## Razorpay test mode

Install dependencies from `requirements.txt`, then copy `.env.example` to `.env`
and fill in Razorpay **test-mode** credentials:

```text
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
```

The project reads these values from the process environment; it does not load
`.env` automatically. In PowerShell, set them for the current session before
starting Django:

```powershell
$env:RAZORPAY_KEY_ID = "rzp_test_..."
$env:RAZORPAY_KEY_SECRET = "..."
$env:RAZORPAY_WEBHOOK_SECRET = "..."
python manage.py runserver
```

Configure the Razorpay Dashboard test-mode webhook URL as:

```text
https://your-public-test-host.example/payments/webhook/
```

For local testing, expose the development server with a secure tunnel and use
the tunnel URL in the Razorpay dashboard. Subscribe to payment captured and
payment failed events. The webhook endpoint verifies the raw request body
signature before processing it.

Checkout creates an order in `pending` status and reserves stock. Only a
successful, signature-verified payment whose gateway order ID, amount, currency,
and gateway state match the database order changes the order to `confirmed`.
Repeated browser callbacks and webhook events are idempotent. No card numbers,
CVVs, or payment credentials are stored.

Pending reservations can be released after the 24-hour payment window with:

```powershell
python manage.py expire_pending_orders
```

Run this command from a scheduler in a deployed environment.

## Coupons and email notifications

Create coupons in Django Admin. Customers apply them during checkout; discounts
are recalculated from database prices and coupon usage is recorded only after
verified payment. Usage limits are protected by database transactions.

Email uses Django's console backend by default, so order, payment, shipping,
and delivery notifications appear in the server console. Configure SMTP with
`EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`,
`EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, and `DEFAULT_FROM_EMAIL` when needed.
Notification logs make repeated payment callbacks safe.

Authenticated customers can manage a wishlist from the navigation bar and can
submit one validated 1-to-5-star review per product.

## Staff dashboard

The staff dashboard is available at:

```text
http://127.0.0.1:8000/dashboard/
```

Create a staff account from the Django shell:

```powershell
python manage.py shell
```

```python
from django.contrib.auth import get_user_model
User = get_user_model()
staff = User.objects.create_user(
    username="manager@example.com",
    email="manager@example.com",
    password="change-this-password",
    is_staff=True,
)
```

For least-privilege access, grant the account the `view_order`, `view_product`,
`add_product`, and `change_product` permissions in Django Admin. A superuser
also has access, but should be reserved for trusted administrators.

The dashboard reports revenue only from payments with `captured` status.
Pending, failed, cancelled, and unverified payments are excluded. Staff cannot
manually mark an order or payment as paid; payment confirmation remains
gateway-controlled. Product and order administrative changes are recorded in
Django's `LogEntry` audit table.
