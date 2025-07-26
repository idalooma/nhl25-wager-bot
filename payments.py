def send_paypal_payout(receiver_email, amount_cents, note="NHL25 Wager Withdrawal"):
    """
    Send a PayPal payout to the given email. Returns the payout batch id if successful.
    """
    amount_usd = f"{amount_cents / 100:.2f}"
    payout = paypalrestsdk.Payout({
        "sender_batch_header": {
            "sender_batch_id": os.urandom(8).hex(),
            "email_subject": "You have a payout!",
            "email_message": "You have received a payout from NHL25 Wager Bot."
        },
        "items": [{
            "recipient_type": "EMAIL",
            "amount": {
                "value": amount_usd,
                "currency": "USD"
            },
            "receiver": receiver_email,
            "note": note,
            "sender_item_id": os.urandom(8).hex()
        }]
    })
    # Use async mode as sync_mode is deprecated and forbidden for new integrations
    if payout.create(sync_mode=False):
        return payout.batch_header.payout_batch_id
    else:
        raise Exception(f"PayPal payout failed: {payout.error}")

import os

import paypalrestsdk
from config import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET

paypalrestsdk.configure({
    "mode": "live",  # Change to "sandbox" for production
    "client_id": PAYPAL_CLIENT_ID,
    "client_secret": PAYPAL_CLIENT_SECRET
})


# One-time payment (default)
def create_paypal_payment(discord_id, amount_cents, success_url, cancel_url):
    """
    Create a PayPal payment and return the approval URL for the user to complete the deposit.
    """
    amount_usd = f"{amount_cents / 100:.2f}"
    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": success_url,
            "cancel_url": cancel_url
        },
        "transactions": [{
            "item_list": {
                "items": [{
                    "name": "NHL25 Wager Deposit",
                    "sku": discord_id,
                    "price": amount_usd,
                    "currency": "USD",
                    "quantity": 1
                }]
            },
            "amount": {
                "total": amount_usd,
                "currency": "USD"
            },
            "description": f"Deposit for Discord user {discord_id}"
        }]
    })
    if payment.create():
        for link in payment.links:
            if link.rel == "approval_url":
                return link.href
        raise Exception("No approval_url found in PayPal payment response.")
    else:
        raise Exception(f"PayPal payment creation failed: {payment.error}")

# Billing Agreement (save PayPal info for future use)
def create_billing_agreement_approval_url(discord_id, plan_name, amount_cents, success_url, cancel_url):
    """
    Create a PayPal billing agreement approval URL for the user to save their PayPal info for future payments.
    Returns the approval URL.
    """
    amount_usd = f"{amount_cents / 100:.2f}"
    billing_plan = {
        "name": plan_name,
        "description": f"Agreement for Discord user {discord_id}",
        "type": "INFINITE",
        "payment_definitions": [{
            "name": "Deposit Payment",
            "type": "REGULAR",
            "frequency": "MONTH",
            "frequency_interval": "1",
            "amount": {"value": amount_usd, "currency": "USD"},
            "cycles": "0"
        }],
        "merchant_preferences": {
            "return_url": success_url,
            "cancel_url": cancel_url,
            "auto_bill_amount": "YES",
            "initial_fail_amount_action": "CONTINUE",
            "max_fail_attempts": "0"
        }
    }
    plan = paypalrestsdk.BillingPlan(billing_plan)
    if plan.create():
        if plan.activate():
            agreement = paypalrestsdk.BillingAgreement({
                "name": plan_name,
                "description": f"Agreement for Discord user {discord_id}",
                "start_date": "2099-12-01T00:00:00Z",  # Set to future, will be updated on approval
                "plan": {"id": plan.id},
                "payer": {"payment_method": "paypal"}
            })
            if agreement.create():
                for link in agreement.links:
                    if link.rel == "approval_url":
                        return link.href, plan.id
                raise Exception("No approval_url found in PayPal agreement response.")
            else:
                raise Exception(f"PayPal agreement creation failed: {agreement.error}")
        else:
            raise Exception(f"PayPal plan activation failed: {plan.error}")
    else:
        raise Exception(f"PayPal plan creation failed: {plan.error}")

def execute_billing_agreement(payment_token):
    """
    Execute the billing agreement after user approval. Returns the agreement ID.
    """
    agreement = paypalrestsdk.BillingAgreement.execute(payment_token)
    if agreement and agreement.state == "Active":
        return agreement.id
    else:
        raise Exception(f"PayPal agreement execution failed: {getattr(agreement, 'error', 'Unknown error')}")

def charge_billing_agreement(agreement_id, amount_cents, note="NHL25 Wager Deposit"):
    """
    Charge a user using a saved PayPal billing agreement (reference transaction).
    """
    amount_usd = f"{amount_cents / 100:.2f}"
    ba = paypalrestsdk.BillingAgreement.find(agreement_id)
    if ba and ba.state == "Active":
        result = ba.bill_balance({
            "amount": {
                "value": amount_usd,
                "currency": "USD"
            },
            "note": note
        })
        if result:
            return True
        else:
            raise Exception(f"PayPal billing agreement charge failed: {ba.error}")
    else:
        raise Exception("Billing agreement not found or not active.")