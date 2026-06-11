import frappe


def get_context(context):
	context.csrf_token = frappe.sessions.get_csrf_token()
	context.no_cache = 1
	context.show_sidebar = 0
	user = frappe.session.user
	if user and user != "Guest":
		context.full_name = frappe.utils.get_fullname(user)
		context.frappe_roles_json = frappe.as_json(frappe.get_roles(user))
	else:
		context.full_name = ""
		context.frappe_roles_json = "[]"
