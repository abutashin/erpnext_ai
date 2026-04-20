import frappe

SETTINGS_DOCTYPE = "ERPNext AI Settings"

def get_settings():
    # Single DocType -> singleton document
    return frappe.get_single(SETTINGS_DOCTYPE)
