import frappe


def get_context(context):
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.no_cache = 1
	context.show_sidebar = 0
	user = frappe.session.user
	if user and user != "Guest":
		context.frappe_roles_json = frappe.as_json(frappe.get_roles(user))
	else:
		context.frappe_roles_json = "[]"
