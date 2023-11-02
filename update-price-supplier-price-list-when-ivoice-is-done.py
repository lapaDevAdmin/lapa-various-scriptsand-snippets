# Available variables:
#  - env: Odoo Environment on which the action is triggered
#  - model: Odoo Model of the record on which the action is triggered; is a void recordset
#  - record: record on which the action is triggered; may be void
#  - records: recordset of all records on which the action is triggered in multi-mode; may be void
#  - time, datetime, dateutil, timezone: useful Python libraries
#  - float_compare: Odoo function to compare floats based on specific precisions
#  - log: log(message, level='info'): logging function to record debug information in ir.logging table
#  - UserError: Warning Exception to use with raise
#  - Command: x2Many commands namespace
# To return an action, assign: action = {...}

# Trigger only when the invoice is posted and not a refund
if record.state == 'posted' and record.move_type != 'in_refund' and record.move_type == 'in_invoice':
    # Identify the supplier from the invoice
    invoice_supplier = record.partner_id

    # Find the most recent invoice for the same supplier
    latest_invoice = env['account.move'].search([
        ('partner_id', '=', invoice_supplier.id),
        ('state', '=', 'posted'),
        ('move_type', '=', 'in_invoice'),
        ('id', '!=', record.id),
    ], order='invoice_date desc', limit=1)

    latest_invoice_date = latest_invoice.invoice_date
    current_invoice_date = record.invoice_date

    # Only proceed with price update if the current invoice is newer
    if not latest_invoice or record.invoice_date > latest_invoice.invoice_date:

        # Identify the supplier from the invoice
        invoice_supplier = record.partner_id
        price_updated = False  # Flag to track if the price was updated

        # Iterate through all the lines of the invoice
        for line in record.invoice_line_ids:

            # Check if the product is storable
            if line.product_id.type == 'product':

                # Get the current price
                current_price = line.price_unit

                # Filter the supplier information based on current supplier and product template
                product_template_id = line.product_id.product_tmpl_id.id
                supplier_lines = env['product.supplierinfo'].search([
                    ('partner_id', '=', invoice_supplier.id),
                    ('product_tmpl_id', '=', product_template_id)
                ])

                # Check if there is more than one supplier line
                if len(supplier_lines) >= 1:
                    # Handle the sequence field
                    supplier_lines = supplier_lines.sorted(
                        key=lambda r: r.sequence)
                    most_recent_supplier = supplier_lines[0]
                    oldest_supplier = supplier_lines[-1] if len(
                        supplier_lines) > 1 else supplier_lines[0]

                    # Define old_price as the price of the oldest supplier
                    old_price = oldest_supplier.price
                else:
                    # Log a message or handle the case where no supplier lines exist
                    # log(f"No supplier lines found for product template ID {product_template_id}", level='warning')
                    continue  # Continue the main loop

                # Handle date and sequence fields
                current_date = dateutil.parser.parse(
                    time.strftime('%Y-%m-%d')).strftime('%Y-%m-%d')
                day_before = (dateutil.parser.parse(time.strftime(
                    '%Y-%m-%d')) - dateutil.relativedelta.relativedelta(days=1)).strftime('%Y-%m-%d')

                # If the current price is the same as the most recent price, just continue to the next line item
                most_recent_price = most_recent_supplier.price
                if float_compare(most_recent_price, current_price, precision_digits=2) == 0:
                    continue
                # Case: only one supplierinfo line and the price is different
                if len(supplier_lines) == 1:
                    oldest_supplier.write({
                        'date_end': day_before,
                        'sequence': 2,
                    })
                    env['product.supplierinfo'].create({
                        'partner_id': invoice_supplier.id,
                        'product_tmpl_id': product_template_id,
                        'price': current_price,
                        'currency_id': oldest_supplier.currency_id.id,
                        'date_start': current_date,
                        'sequence': 1,
                        'product_name': oldest_supplier.product_name,
                        'product_code': oldest_supplier.product_code,
                    })
                    price_updated = True  # Set the flag to True because the price was updated

                # Case: both supplier lines are there
                elif len(supplier_lines) == 2:
                    oldest_supplier.write({
                        'date_end': day_before,
                        'sequence': 2,
                        'price': most_recent_supplier.price
                    })
                    most_recent_supplier.write({
                        'date_start': current_date,
                        'sequence': 1,
                        'price': current_price
                    })
                    price_updated = True  # Set the flag to True because the price was updated

                # Create an activity only if the price was updated
                if price_updated and line.product_id.product_tmpl_id.id:
                    price_difference = current_price - old_price
                    activity_summary = f'Price changed in invoice: {record.name}'
                    activity_vals = {
                        'res_id': line.product_id.product_tmpl_id.id,
                        'res_model_id': env['ir.model'].search([('model', '=', 'product.template')], limit=1).id,
                        'activity_type_id': 4,  # To Do
                        'user_id': env.user.id,  # Current user ID
                        'summary': activity_summary,
                        'note': f'Price updated. Old: {old_price}, New: {current_price}, Difference: {price_difference}',
                    }
                    env['mail.activity'].create(activity_vals)
