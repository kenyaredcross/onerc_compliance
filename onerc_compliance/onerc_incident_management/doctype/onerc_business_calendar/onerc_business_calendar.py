# Copyright (c) 2026, Kelvin Njenga and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import get_time

WORKING_DAY_FIELDS = (
	"work_monday",
	"work_tuesday",
	"work_wednesday",
	"work_thursday",
	"work_friday",
	"work_saturday",
	"work_sunday",
)


class OnercBusinessCalendar(Document):
	def validate(self):
		if get_time(self.business_end_time) <= get_time(self.business_start_time):
			frappe.throw("Business end time must be after the start time.")
		if not any(self.get(field) for field in WORKING_DAY_FIELDS):
			frappe.throw("Select at least one working day.")
