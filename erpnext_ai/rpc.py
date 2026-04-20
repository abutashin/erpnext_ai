import frappe
import json
import ast

def _parse_arg(arg):
    """
    Helper: Converts Strings (from AI) back into Python Lists/Dicts
    """
    if not arg:
        return None
    if isinstance(arg, (dict, list)):
        return arg
    if isinstance(arg, str):
        arg = arg.strip()
        # Try JSON first
        try: return json.loads(arg)
        except: pass
        # Try Python Literal (single quotes)
        try: return ast.literal_eval(arg)
        except: pass
    return arg

@frappe.whitelist()
def get_record(doctype, name, fields=None):
    # 1. CLEANUP: Remove 'cmd' which is injected by Frappe routing
    # (not needed here, but for consistency)
    # 2. PARSING: Convert strings back to Python Lists/Dicts
    # (GET parameters always arrive as strings)
    clean_fields = _parse_arg(fields) or []

    # 3. EXECUTE
    return frappe.get_doc(doctype, name).as_dict(fields=clean_fields)

@frappe.whitelist()
def list_records(doctype, **kwargs):
    # 1. CLEANUP: Remove 'cmd' which is injected by Frappe routing
    kwargs.pop('cmd', None)

    # 2. MAPPING: Frappe uses 'limit_page_length', not 'limit'
    if 'limit' in kwargs:
        kwargs['limit_page_length'] = kwargs.pop('limit')

    # 3. PARSING: Convert strings back to Python Lists/Dicts
    # (GET parameters always arrive as strings)
    for key in ['fields', 'filters']:
        if key in kwargs and isinstance(kwargs[key], str):
            kwargs[key] = _parse_arg(kwargs[key])

    # 4. EXECUTE
    return frappe.get_list(doctype, **kwargs)

@frappe.whitelist()
def count_records(doctype, filters=None):
    """
    RPC Method for 'erp_count'
    """
    try:
        clean_filters = _parse_arg(filters) or {}
        return frappe.db.count(doctype, clean_filters)
    except Exception as e:
        return 0

@frappe.whitelist()
def exists_record(doctype, filters=None):
    """
    RPC Method for 'erp_exists'
    """
    try:
        clean_filters = _parse_arg(filters) or {}
        return frappe.db.exists(doctype, clean_filters) is not None
    except Exception as e:
        return False