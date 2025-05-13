import razorpay

# Razorpay credentials
RAZORPAY_KEY_ID = 'rzp_test_YkCy6jA2GFlk5F'
RAZORPAY_KEY_SECRET = 'daOhxZJLVM1ShIlgGtZdLHYt'

# Initialize Razorpay client
client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

# Payment ID for which refund was issued
payment_id = "pay_QTxql1JJdABzXc"

# Fetch the payment details
payment = client.payment.fetch(payment_id)

# Check if the payment has been refunded
if payment.get('refund_status') is None:
    print("❌ No refund has been issued for this payment.")
else:
    # Now fetch all refunds (filtering by payment_id)
    refunds = client.refund.all({'payment_id': payment_id})
    
    for refund in refunds['items']:
        print(f"Refund ID: {refund['id']}")
        print(f"Amount Refunded: ₹{int(refund['amount']) / 100}")
        print(f"Status: {refund['status']}")
        print(f"Created At (UNIX Timestamp): {refund['created_at']}")
        print("---")
