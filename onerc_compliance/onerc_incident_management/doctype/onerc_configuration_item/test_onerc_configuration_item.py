# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt
"""Tests for the minimal Onerc Configuration Item stub and its wiring into Onerc Incident."""
import frappe
from frappe.tests import IntegrationTestCase

IGNORE_TEST_RECORD_DEPENDENCIES = ["User", "Geo Node", "Onerc Configuration Item"]


class IntegrationTestOnercConfigurationItem(IntegrationTestCase):
	def _make_ci(self, name, **overrides):
		data = {"doctype": "Onerc Configuration Item", "ci_name": name, "ci_type": "Server"}
		data.update(overrides)
		return frappe.get_doc(data).insert(ignore_permissions=True)

	def test_valid_creation_defaults_active(self):
		ci = self._make_ci("_Test CI Web01")
		self.assertTrue(frappe.db.exists("Onerc Configuration Item", ci.name))
		self.assertEqual(ci.status, "Active")

	def test_dependency_parent_child(self):
		parent = self._make_ci("_Test CI DBHost")
		child = self._make_ci("_Test CI AppOnDB", parent_ci=parent.name)
		self.assertEqual(child.parent_ci, parent.name)
		# Dependent CIs are discoverable from the parent.
		dependents = frappe.get_all(
			"Onerc Configuration Item", filters={"parent_ci": parent.name}, pluck="name"
		)
		self.assertIn(child.name, dependents)

	def test_cannot_depend_on_itself(self):
		ci = self._make_ci("_Test CI SelfRef")
		ci.parent_ci = ci.name
		with self.assertRaises(frappe.ValidationError):
			ci.save(ignore_permissions=True)

	def test_incident_affected_ci_wired(self):
		field = frappe.get_meta("Onerc Incident").get_field("affected_ci")
		self.assertIsNotNone(field)
		self.assertEqual(field.options, "Onerc Configuration Item")
