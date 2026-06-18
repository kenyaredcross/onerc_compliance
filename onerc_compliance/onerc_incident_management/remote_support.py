# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""Remote support orchestration (vendor-neutral; AnyDesk and others swap via settings).

Flow:
  1. An agent clicks "Start Remote Session" on an Incident / Service Request.
  2. :func:`start_session` requests a one-time token from the provider (isolated in
     :func:`_request_provider_token` so the provider can be swapped) and records an
     Onerc Remote Support Session, then sends the target user the link.
  3. When the session ends the provider calls :func:`session_webhook`, which closes
     the session and posts the outcome as a work note on the linked record.

SMS delivery is deferred (onerc_sms not present) — the link goes by email/Desk.
"""
import frappe
from frappe import _
from frappe.utils import get_url, now_datetime

REFERENCE_DOCTYPES = ("Onerc Incident", "Onerc Service Request")


@frappe.whitelist()
def start_session(reference_doctype, reference_name, target_user=None):
	"""Create a remote support session for an Incident / Service Request."""
	if reference_doctype not in REFERENCE_DOCTYPES:
		frappe.throw(_("Remote support is only available on Incidents and Service Requests."))
	ref = frappe.get_doc(reference_doctype, reference_name)
	settings = frappe.get_cached_doc("Onerc Remote Support Settings")

	if not target_user:
		target_user = ref.get("reported_by") or ref.get("requested_for") or ref.get("requested_by")

	token = _request_provider_token(settings, reference_doctype, reference_name)
	session = frappe.get_doc(
		{
			"doctype": "Onerc Remote Support Session",
			"reference_type": reference_doctype,
			"reference_name": reference_name,
			"agent": frappe.session.user,
			"target_user": target_user,
			"session_token": token["token"],
			"provider_session_id": token.get("session_id"),
			"consent_given": 0 if settings.consent_required else 1,
			"status": "Requested",
			"started_on": now_datetime(),
		}
	).insert(ignore_permissions=True)

	_notify_target(session, token)
	return session.name


def _request_provider_token(settings, reference_doctype, reference_name):
	"""Obtain a one-time session token from the remote-support provider.

	Isolated so the provider (AnyDesk, etc.) can be swapped purely via Onerc Remote
	Support Settings. When no provider base URL is configured we mint a placeholder
	token so the whole flow is exercisable without an external dependency.
	"""
	base_url = (settings.provider_api_base_url or "").strip()
	if not base_url:
		return {"token": frappe.generate_hash(length=12), "session_id": None}
	# A live integration would POST to {base_url} using `credentials_reference` and
	# return the provider's token + session id. Kept stubbed for Phase 1.
	return {"token": frappe.generate_hash(length=12), "session_id": None}


def _notify_target(session, token):
	if not session.target_user:
		return
	link = f"{get_url()}/app/onerc-remote-support-session/{session.name}"
	try:
		frappe.sendmail(
			recipients=[session.target_user],
			subject=_("Remote support session started"),
			message=_(
				"A support agent has started a remote session.<br>"
				"Session token: <b>{0}</b><br>Details: {1}"
			).format(token["token"], link),
		)
	except Exception:
		frappe.log_error(title="Onerc remote support notification failed")


@frappe.whitelist(allow_guest=True)
def session_webhook(**kwargs):
	"""Provider callback fired when a session ends.

	Accepts: ``session`` (our name) or ``provider_session_id``, plus ``secret``,
	``duration`` (seconds), ``ended_on`` and ``agent``. Verifies the shared secret
	configured in Onerc Remote Support Settings, closes the session and posts a
	work note on the linked Incident / Service Request.
	"""
	data = frappe._dict(kwargs)
	settings = frappe.get_cached_doc("Onerc Remote Support Settings")
	secret = settings.get_password("webhook_secret", raise_exception=False)
	if secret and data.secret != secret:
		frappe.throw(_("Invalid webhook secret"), frappe.PermissionError)

	session = _find_session(data)
	if not session:
		return {"ok": False, "error": "session not found"}

	session.db_set("status", "Ended")
	session.db_set("ended_on", data.ended_on or now_datetime())
	if data.duration:
		session.db_set("duration", data.duration)
	if data.agent and not session.agent:
		session.db_set("agent", data.agent)

	_post_work_note(session, data)
	return {"ok": True, "session": session.name}


def _find_session(data):
	if data.get("session") and frappe.db.exists("Onerc Remote Support Session", data.session):
		return frappe.get_doc("Onerc Remote Support Session", data.session)
	if data.get("provider_session_id"):
		name = frappe.db.get_value(
			"Onerc Remote Support Session", {"provider_session_id": data.provider_session_id}
		)
		if name:
			return frappe.get_doc("Onerc Remote Support Session", name)
	return None


def _post_work_note(session, data):
	if not (session.reference_type and session.reference_name):
		return
	if not frappe.db.exists(session.reference_type, session.reference_name):
		return
	ref = frappe.get_doc(session.reference_type, session.reference_name)
	ref.add_comment(
		"Comment",
		_("Remote support session {0} ended. Duration: {1}s. Agent: {2}.").format(
			session.name, data.get("duration") or "?", session.agent or data.get("agent") or "?"
		),
	)
