restricted_pricelist_ids = [1, 5, 6, 8, 11, 4, 3]
order = record

if not order:
    raise UserError("This action can only be triggered on a sale order.")

partner = order.partner_id
# If the partner is a contact of a company (has a parent_id), use the company's details
if partner.parent_id:
    partner = partner.parent_id

pricelist = partner.property_product_pricelist

if pricelist.id in restricted_pricelist_ids:
    # Search for a pricelist with the partner's (company's) name in it
    existing_pricelist = env['product.pricelist'].search([
        ('name', 'ilike', partner.name)
    ], limit=1)

    if existing_pricelist:
        pricelist = existing_pricelist
    else:
        # Create a new pricelist with the partner's (company's) name
        pricelist = env['product.pricelist'].create({
            'name': partner.name,
            'currency_id': order.currency_id.id
        })

for line in order.order_line:
    product_template = line.product_id.product_tmpl_id
    if product_template.detailed_type != 'product':
        continue  # skip this line if it's not a standard product

    # Check if pricelist item for this product template already exists
    pricelist_item = env['product.pricelist.item'].search([
        ('pricelist_id', '=', pricelist.id),
        ('product_tmpl_id', '=', product_template.id),
        ('applied_on', '=', '1_product')
    ], limit=1)

    item_vals = {
        'product_tmpl_id': product_template.id,
        'fixed_price': line.price_unit,
        'applied_on': '1_product',
        'min_quantity': 1
    }

    if pricelist_item:
        # Update existing pricelist item
        pricelist_item.write(item_vals)
    else:
        # Create a new pricelist item for this product template
        item_vals['pricelist_id'] = pricelist.id
        env['product.pricelist.item'].create(item_vals)

# Get the action ID for the sale.order model
action_id = env.ref('sale.action_orders').id

# Generate the URL pointing to the original sale order
document_url = f"/web#id={order.id}&model=sale.order&action={action_id}&view_type=form"
document_link = f'<a href="{document_url}">View Original Order</a>'

# Record a note on the company contact using OdooBot's ID with the link to the original document
env['mail.message'].create({
    'body': f"Pricelist items have been updated/created successfully. {document_link}",
    'res_id': partner.id,
    'model': 'res.partner',
    'message_type': 'notification',
    'subtype_id': env.ref('mail.mt_note').id,  # This makes it a note
    'author_id': 1  # Set the author to OdooBot with ID 1
})

# Optionally, you can return a message or an action after the operation.
# log("Pricelist items have been updated/created successfully.", level='info')
