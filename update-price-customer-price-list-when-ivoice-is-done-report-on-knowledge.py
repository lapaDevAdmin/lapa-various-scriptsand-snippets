# Initialize logs for tracking changes
client_price_changes_log = []
price_issues = []

# Trigger only when the invoice is posted and not a refund
if record.state == 'posted' and record.move_type != 'in_refund' and record.move_type == 'in_invoice':

    # Identify the supplier from the invoice
    invoice_supplier = record.partner_id
    # Use the invoice date or today's date
    invoice_date = record.invoice_date or datetime.now().date()
    invoice_name = record.name  # Invoice document name

    # Calcola il titolo dell'articolo basato sul mese corrente
    current_month_name = time.strftime('%B')
    article_title = f"STORICO PREZZI PRODOTTO E CAMBIO LISTINI | {current_month_name.upper()}"
    existing_article = env['knowledge.article'].search(
        [('name', '=', article_title)], limit=1)

    # If the article doesn't exist, create it
    if not existing_article:
        # Altrimenti, crea l'articolo e associato immediatamente all'utente con ID 6
        existing_article = env['knowledge.article'].create({
            'name': article_title,
            'body': '',
            'is_published': False,
            'internal_permission': 'none',
            'article_member_ids': [
                (0, 0, {
                    'partner_id': 10,
                    'permission': 'write'
                }),
                (0, 0, {
                    'partner_id': 11,
                    'permission': 'write'
                }),
                (0, 0, {
                    'partner_id': 12,
                    'permission': 'write'
                }),
            ],
        })

    # Iterate through all the lines of the invoice
    for line in record.invoice_line_ids:

        # Check if the product is storable
        if line.product_id.type == 'product':

            # Filter the supplier information based on the current supplier and product template
            product_template_id = line.product_id.product_tmpl_id.id
            supplier_lines = env['product.supplierinfo'].search([
                ('partner_id', '=', invoice_supplier.id),
                ('product_tmpl_id', '=', product_template_id),
                ('date_start', '!=', False)
            ]).sorted(key=lambda r: r.date_start, reverse=True)  # Order by date_start to get the most recent first

            if supplier_lines:
                # Prendi la date_start del prezzo più recente
                most_recent_date_start = supplier_lines[0].date_start

                # Calcola la data che è un giorno prima di questa date_start
                previous_date_end = most_recent_date_start - \
                    datetime.timedelta(days=1)

                # Cerca il record del fornitore che ha questa date_end
                previous_supplier_line = env['product.supplierinfo'].search([
                    ('partner_id', '=', invoice_supplier.id),
                    ('product_tmpl_id', '=', product_template_id),
                    ('date_end', '=', previous_date_end)
                ], limit=1)

                # Se trovato, usa il prezzo di questo record come most_recent_price
                if previous_supplier_line:
                    most_recent_price = previous_supplier_line.price
                else:
                    # fallback al prezzo più recente se non trovato
                    most_recent_price = supplier_lines[0].price

                current_invoice_price = line.price_unit
                price_difference = round(
                    current_invoice_price - most_recent_price, 2)

                if price_difference == 0:
                    continue

                # Update the customer pricelists
                pricelist_item_lines = env['product.pricelist.item'].search([
                    ('product_tmpl_id', '=', product_template_id),
                    ('compute_price', '=', 'fixed')
                ])

                # Define restricted pricelist IDs
                # 1168 is luigias group price list
                restricted_pricelist_ids = [1, 5, 6, 8, 11, 4, 3, 1168]

                log_entries = []
                for item in pricelist_item_lines:

                    # Skip the pricelist if it's in the restricted list
                    if item.pricelist_id.id in restricted_pricelist_ids:
                        continue

                    old_price = item.fixed_price
                    # Update based on the price difference
                    new_price = round(old_price + price_difference, 2)

                    # Check if the new price is valid
                    if new_price <= 0 or new_price < 0.5 * old_price:
                        # Raccogliamo l'informazione sull'errore invece di creare un'attività qui
                        issue_summary = f"Price Update Issue for {line.product_id.name}"
                        issue_note = f'Attempted to update price in pricelist "{item.pricelist_id.name}" to an invalid value: {new_price}. Update was not applied.'
                        price_issues.append((issue_summary, issue_note))
                        continue  # Skip this pricelist item and move to the next one

                    # Collect the client price changes using Markdown
                    log_entry = f"""<p>{item.pricelist_id.name} - Vecchio prezzo: {old_price} - Nuovo prezzo: {new_price} - Differenza: {price_difference}</p>
                    """
                    log_entries.append(log_entry)

                    # If the new price is valid, update it
                    item.write({'fixed_price': new_price})

                # After each line iteration, update the article content
                new_content = f"""<p><h3>{line.product_id.name} | {invoice_date} | {invoice_name} |Prezzo Recente: {most_recent_price} | New Price in invoice: {current_invoice_price} | Differenza: {price_difference}</h3></p>
                """
                for log_entry in log_entries:
                    new_content += log_entry + "\n\n"

                existing_article.ensure_one()
                existing_content = existing_article.body or ""
                updated_content = f"""{new_content}
                {existing_content}"""

                existing_article.write({'body': updated_content})

                if price_issues:
                    combined_summary = "Price Update Issues Detected"
                    combined_note = "\n".join(
                        [f"{summary}: {note}" for summary, note in price_issues])

                    activity_vals = {
                        'res_model_id': env['ir.model'].search([('model', '=', 'product.template')], limit=1).id,
                        'res_id': line.product_id.product_tmpl_id.id,
                        'activity_type_id': 4,  # To Do
                        'user_id': env.user.id,  # Current user ID
                        'summary': combined_summary,
                        'note': combined_note,
                    }
                    env['mail.activity'].create(activity_vals)
