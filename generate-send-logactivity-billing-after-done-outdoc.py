SPECIFIC_CUSTOMER_IDS = [834]  # Replace with your actual IDs

# Define constants
ACTIVITY_USER = 8  # Laura user id
STOCK_PICKING_MODEL_ID = 795
ACTIVITY_TYPE_PROMEMORIA = 9

# Define all helper functions first


def validate_and_send_invoices(invoice_ids):
    invoices = env['account.move'].browse(invoice_ids)
    for invoice in invoices:
        try:
            # log(f"Validating invoice {invoice.name}.", level='info')
            invoice.action_post()
            # log(f"Validated invoice {invoice.name}.", level='info')

            send_invoice_by_email(invoice)
        except Exception as e:
            log(
                f"Error while processing invoice {invoice.name}: {str(e)}", level='error')


def send_invoice_by_email(invoice):
    template_id = env.ref(
        'account.email_template_edi_invoice', raise_if_not_found=False)
    if template_id:
        # log(f"Sending invoice {invoice.name} by email.", level='info')
        template_id.send_mail(invoice.id, force_send=True)
        # log(f"Sent invoice {invoice.name} by email.", level='info')

        # _log_activity_for_delivery_order()
        _log_note_for_delivery_order()


def _log_activity_for_delivery_order():
    """Log a reminder activity for the current delivery order."""
    try:
        activity_note = f"Fattura generata per il cliente {record.partner_id.name} con successo."
        summary_msg = f"Fattura generata con successo"

        env['mail.activity'].create({
            'activity_type_id': ACTIVITY_TYPE_PROMEMORIA,
            'res_model_id': STOCK_PICKING_MODEL_ID,
            'res_id': record.id,
            'user_id': ACTIVITY_USER,
            'summary': summary_msg,
            'note': activity_note,
            'date_deadline': datetime.date.today()
        })
        # log(f"Logged activity for delivery order {record.name}.", level='info')
    except Exception as e:
        log(
            f"Error while logging activity for delivery order {record.name}: {str(e)}", level='error')


def _log_note_for_delivery_order():
    """Log a note for the current delivery order."""
    try:
        message_body = f"Fattura generata per il cliente {record.partner_id.name} con successo."
        record.message_post(body=message_body)
        # log(f"Logged note for delivery order {record.name}.", level='info')
    except Exception as e:
        log(
            f"Error while logging note for delivery order {record.name}: {str(e)}", level='error')


# Main script logic

if record.partner_id.id in SPECIFIC_CUSTOMER_IDS and record.state == 'done':
    log(f"Processing delivery order {record.name} for partner ID {record.partner_id.id}.", level='info')
    try:
        sale_order = env['sale.order'].search(
            [('name', '=', record.origin)], limit=1)
        if not sale_order:
            log(
                f"No matching sale order found for delivery order {record.name}.", level='warning')
        else:
            log(
                f"Found matching sale order {sale_order.name} for delivery order {record.name}.", level='info')

            # Create the invoice for the sale order using the _create_invoices method
            invoices = sale_order._create_invoices()
            # log(f"Created invoice(s) for sale order {sale_order.name}.", level='info')

            # Determine the appropriate billing address
            billing_partner = sale_order.partner_invoice_id or sale_order.partner_id.parent_id or sale_order.partner_id
            for invoice in invoices:
                invoice.write({'partner_id': billing_partner.id})
                # log(f"Updated billing partner for invoice {invoice.name}.", level='info')

            # Validate and send invoices
            validate_and_send_invoices(invoices.ids)
    except Exception as e:
        log(
            f"Error while processing delivery order {record.name}: {str(e)}", level='error')
