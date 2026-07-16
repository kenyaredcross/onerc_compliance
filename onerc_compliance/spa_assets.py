# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import json
import os

import frappe

_ASSET_BASE = "/assets/onerc_compliance/compliance/"


def get_spa_assets():
	"""Resolve the built SPA entry script and stylesheet from Vite's manifest.

	The bundle uses hashed filenames so browsers pick up new builds without
	stale-cache issues; the www pages call this to inject the current names.
	"""
	manifest_path = frappe.get_app_path(
		"onerc_compliance", "public", "compliance", ".vite", "manifest.json"
	)
	try:
		with open(manifest_path) as f:
			manifest = json.load(f)
	except (OSError, ValueError):
		frappe.log_error(
			title="Compliance SPA manifest missing",
			message=f"Could not read {manifest_path}. Run `npm run build` in apps/onerc_compliance/frontend.",
		)
		return {"js": "", "css": ""}

	entry = None
	css = ""
	for chunk in manifest.values():
		if chunk.get("isEntry"):
			entry = chunk
			if chunk.get("css"):
				css = chunk["css"][0]
		# With cssCodeSplit disabled the stylesheet is a standalone manifest
		# entry rather than being attached to the entry chunk.
		elif not css and chunk.get("file", "").endswith(".css"):
			css = chunk["file"]

	if not entry:
		return {"js": "", "css": ""}

	return {
		"js": _ASSET_BASE + entry["file"],
		"css": (_ASSET_BASE + css) if css else "",
	}
