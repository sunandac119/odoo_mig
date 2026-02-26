# POS Refund Policy Enforcer (Odoo 14)

This addon enforces strict refund policies in POS:
- Only users in **POS Chief Cashier** group can process refunds.
- Refund must be made in the **same branch** as the original sale (if `pos.config` has `branch_id`), otherwise same company.
- Refund must be processed in a **new session** (not the original session).
- Prevent **multiple full refunds** of the same order. Partial refunds are allowed through the existing **pos_order_return** wizard and are limited by `max_returnable_qty`.

## Requirements
- Odoo 14
- `point_of_sale`, `stock`
- OCA's `pos_order_return` (for partial refund wizard).

## Installation
1. Copy the folder `pos_refund_policy_enforcer` into your addons path.
2. Update Apps list and install the module.
3. Assign the **POS Chief Cashier** group to users who can process refunds.

## Notes
- If you don't use branches, the module will fallback to company check.
- If you want to allow multiple partial refunds (split across orders), remove the strict block in `PosOrderLine._check_return_qty`.