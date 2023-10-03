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

# Initialize logs for tracking changes
client_price_changes_log = []
product_difference_log = []

# Trigger only when the invoice is posted and not a refund
if record.state == 'posted' and record.move_type != 'in_refund':

    # Identify the supplier from the invoice
    invoice_supplier = record.partner_id

    # Iterate through all the lines of the invoice
    for line in record.invoice_line_ids:

        # Check if the product is storable
        if line.product_id.type == 'product':

            # Filter the supplier information based on the current supplier and product template
            product_template_id = line.product_id.product_tmpl_id.id
            supplier_lines = env['product.supplierinfo'].search([
                ('partner_id', '=', invoice_supplier.id),
                ('product_tmpl_id', '=', product_template_id)
            ]).sorted(key=lambda r: r.sequence)

            # Calculate price difference based on the two most recent supplier lines
            if len(supplier_lines) >= 2:
                most_recent_price = supplier_lines[0].price
                older_price = supplier_lines[1].price
                price_difference = most_recent_price - older_price

                # Collect the price difference
                product_difference_log.append(
                    f"{line.product_id.name} - {price_difference}")

            # Update the customer pricelists
            pricelist_item_lines = env['product.pricelist.item'].search([
                ('product_tmpl_id', '=', product_template_id),
                ('compute_price', '=', 'fixed')
            ])

            for item in pricelist_item_lines:
                old_price = item.fixed_price
                # Update based on the price difference
                new_price = old_price + price_difference
                item.write({'fixed_price': new_price})

                # Collect the client price changes
                pricelist_name = item.pricelist_id.name
                client_price_changes_log.append(
                    f"{pricelist_name} - {old_price} -> {new_price}")

# Prepare the final log strings
final_client_price_changes_log = "\n".join(client_price_changes_log)
final_product_difference_log = "\n".join(product_difference_log)

# Log all the changes as a single entry for each type
log(f"Client Price Changes:\n{final_client_price_changes_log}", level='info')
log(f"Product Price Differences:\n{final_product_difference_log}", level='info')
