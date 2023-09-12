SPECIFIC_CUSTOMER_IDS = [1977, 1984]  # Replace with your specific customer ids
USERS = [8, 16]  # User IDs for Licia and Laura. Replace with correct ids.
MESSAGE = "La fattura deve essere spedita per posta"
ACCOUNT_MOVE_MODEL_ID = 648


def create_activity_for_invoice(invoice):
    for user_id in USERS:
        env['mail.activity'].create({
            'activity_type_id': 4,  # Replace with your specific activity type id
            # Set to tomorrow
            'date_deadline': datetime.datetime.now().date() + datetime.timedelta(days=1),
            'user_id': user_id,
            'res_id': invoice.id,
            'res_model_id': ACCOUNT_MOVE_MODEL_ID,  # Using the correct ID
            'note': MESSAGE,
        })


# Main script logic
if record.partner_id.id in SPECIFIC_CUSTOMER_IDS:
    create_activity_for_invoice(record)
