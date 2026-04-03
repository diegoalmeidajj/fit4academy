"""Fit4Academy — Stripe Billing Module
Handles card/bank charging, recurring memberships, and platform fees.

To activate:
1. pip install stripe
2. Set STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY in environment variables
3. All functions gracefully return None/False if Stripe is not configured
"""

import os

PLATFORM_FEE = 0.30  # $0.30 per transaction for Fit4Academy

try:
    import stripe
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
    STRIPE_ENABLED = bool(stripe.api_key)
    STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
except ImportError:
    STRIPE_ENABLED = False
    STRIPE_PUBLISHABLE_KEY = ''
    stripe = None


def is_enabled():
    return STRIPE_ENABLED


def get_publishable_key():
    return STRIPE_PUBLISHABLE_KEY


# ═══════════════════════════════════════════════════════════════
#  CUSTOMERS
# ═══════════════════════════════════════════════════════════════

def create_customer(email, name, member_id=None):
    """Create a Stripe customer for a member."""
    if not STRIPE_ENABLED:
        return None
    try:
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={'member_id': str(member_id)} if member_id else {},
        )
        return customer.id
    except Exception as e:
        print(f"[Stripe] Create customer error: {e}")
        return None


def get_customer(customer_id):
    """Get Stripe customer details."""
    if not STRIPE_ENABLED or not customer_id:
        return None
    try:
        return stripe.Customer.retrieve(customer_id)
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
#  PAYMENT METHODS (Cards / Bank Accounts)
# ═══════════════════════════════════════════════════════════════

def create_setup_intent(customer_id):
    """Create a SetupIntent to save a card/bank for future charges."""
    if not STRIPE_ENABLED:
        return None
    try:
        intent = stripe.SetupIntent.create(
            customer=customer_id,
            payment_method_types=['card', 'us_bank_account'],
        )
        return {'client_secret': intent.client_secret, 'id': intent.id}
    except Exception as e:
        print(f"[Stripe] SetupIntent error: {e}")
        return None


def list_payment_methods(customer_id):
    """List saved payment methods for a customer."""
    if not STRIPE_ENABLED or not customer_id:
        return []
    try:
        methods = stripe.PaymentMethod.list(customer=customer_id, type='card')
        result = []
        for pm in methods.data:
            result.append({
                'id': pm.id,
                'type': 'card',
                'brand': pm.card.brand if pm.card else '',
                'last4': pm.card.last4 if pm.card else '',
                'exp_month': pm.card.exp_month if pm.card else '',
                'exp_year': pm.card.exp_year if pm.card else '',
            })
        # Also check bank accounts
        bank_methods = stripe.PaymentMethod.list(customer=customer_id, type='us_bank_account')
        for pm in bank_methods.data:
            result.append({
                'id': pm.id,
                'type': 'bank',
                'brand': pm.us_bank_account.bank_name if pm.us_bank_account else '',
                'last4': pm.us_bank_account.last4 if pm.us_bank_account else '',
            })
        return result
    except Exception as e:
        print(f"[Stripe] List methods error: {e}")
        return []


def detach_payment_method(payment_method_id):
    """Remove a saved payment method."""
    if not STRIPE_ENABLED:
        return False
    try:
        stripe.PaymentMethod.detach(payment_method_id)
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
#  CHARGES
# ═══════════════════════════════════════════════════════════════

def charge(customer_id, payment_method_id, amount, description='', metadata=None):
    """Charge a customer's saved card/bank.
    Amount is in dollars (e.g. 99.99).
    Platform fee of $0.30 is added automatically.
    """
    if not STRIPE_ENABLED:
        return None
    try:
        total_cents = int((amount + PLATFORM_FEE) * 100)
        intent = stripe.PaymentIntent.create(
            amount=total_cents,
            currency='usd',
            customer=customer_id,
            payment_method=payment_method_id,
            off_session=True,
            confirm=True,
            description=description,
            metadata=metadata or {},
        )
        return {
            'success': True,
            'charge_id': intent.id,
            'amount': amount,
            'platform_fee': PLATFORM_FEE,
            'total_charged': amount + PLATFORM_FEE,
            'status': intent.status,
        }
    except stripe.error.CardError as e:
        return {'success': False, 'error': str(e.user_message)}
    except Exception as e:
        print(f"[Stripe] Charge error: {e}")
        return {'success': False, 'error': str(e)}


def charge_one_time(amount, token_or_source, description='', metadata=None):
    """One-time charge without saved payment method (e.g. walk-in)."""
    if not STRIPE_ENABLED:
        return None
    try:
        total_cents = int((amount + PLATFORM_FEE) * 100)
        intent = stripe.PaymentIntent.create(
            amount=total_cents,
            currency='usd',
            payment_method=token_or_source,
            confirm=True,
            description=description,
            metadata=metadata or {},
        )
        return {
            'success': True,
            'charge_id': intent.id,
            'amount': amount,
            'platform_fee': PLATFORM_FEE,
            'total_charged': amount + PLATFORM_FEE,
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ═══════════════════════════════════════════════════════════════
#  SUBSCRIPTIONS (Recurring Memberships)
# ═══════════════════════════════════════════════════════════════

def create_price(amount, interval='month', product_name='Membership'):
    """Create a Stripe Price for recurring billing."""
    if not STRIPE_ENABLED:
        return None
    try:
        price = stripe.Price.create(
            unit_amount=int((amount + PLATFORM_FEE) * 100),
            currency='usd',
            recurring={'interval': interval},
            product_data={'name': product_name},
        )
        return price.id
    except Exception as e:
        print(f"[Stripe] Create price error: {e}")
        return None


def create_subscription(customer_id, price_id, payment_method_id=None):
    """Subscribe a customer to a recurring plan."""
    if not STRIPE_ENABLED:
        return None
    try:
        params = {
            'customer': customer_id,
            'items': [{'price': price_id}],
            'expand': ['latest_invoice.payment_intent'],
        }
        if payment_method_id:
            params['default_payment_method'] = payment_method_id
        sub = stripe.Subscription.create(**params)
        return {
            'subscription_id': sub.id,
            'status': sub.status,
            'current_period_end': sub.current_period_end,
        }
    except Exception as e:
        print(f"[Stripe] Subscription error: {e}")
        return None


def cancel_subscription(subscription_id):
    """Cancel a subscription."""
    if not STRIPE_ENABLED or not subscription_id:
        return False
    try:
        stripe.Subscription.delete(subscription_id)
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
#  REFUNDS
# ═══════════════════════════════════════════════════════════════

def refund(charge_id, amount=None):
    """Refund a charge. If amount is None, full refund."""
    if not STRIPE_ENABLED:
        return False
    try:
        params = {'payment_intent': charge_id}
        if amount:
            params['amount'] = int(amount * 100)
        stripe.Refund.create(**params)
        return True
    except Exception as e:
        print(f"[Stripe] Refund error: {e}")
        return False
