# -*- coding: utf-8 -*-
# Copyright (c) 2019, Mahmoud Marouf and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe

from datetime import date
import datetime

from frappe.utils import getdate, today, add_years, format_datetime
from frappe.model.naming import set_name_by_naming_series
from frappe import throw, _, scrub
from frappe.permissions import add_user_permission, remove_user_permission, \
	set_user_permission_if_allowed, has_permission
from frappe.model.document import Document
from erpnext.utilities.transaction_base import delete_events
from frappe.utils.nestedset import NestedSet

class EmployeeUserDisabledError(frappe.ValidationError): pass
class EmployeeLeftValidationError(frappe.ValidationError): pass

class Employee(Document):


	def validate(self):
		from erpnext.controllers.status_updater import validate_status
		validate_status(self.status, ["Active", "Temporary Leave", "Left", 'Resign','With In Article 81', 'With Out Article 81',
		 							'Marriage Within 6 Months Or 3 Months Of Childbirth', 'Force Majeure',
									'With In Article 80', 'With Out Article 80', 'End By Employer',
									 'Expiration Of The Contract Or Agreement Of The Parties'])

		self.employee = self.name
		self.set_employee_name()
		self.validate_date()
		self.set_total()




	def set_employee_name(self):
		self.employee_name = ' '.join(filter(lambda x: x, [self.first_name, self.middle_name, self.last_name]))

	def set_total(self):
		joining = self.date_of_joining
		leaving = self.date_of_leaving
		date1 =  datetime.datetime.strptime(joining, "%Y-%m-%d").date()
		date2 =  datetime.datetime.strptime(leaving, "%Y-%m-%d").date()
		delta =  (date2 - date1).days
		years = delta/365.25

		if years >2 and years <= 5:
			if self.status == 'Left':
				throw(_("The worker is not worth the end of service reward."))
				self.total = 0
			elif self.status == 'Resign':
				self.total = (((self.last_salary/2)*years)/3)
			elif self.status == 'With In Article 81':
				self.total = ((self.last_salary/2)*years)
			elif self.status == 'With Out Article 81':
				throw(_("The worker is not worth the end of service reward."))
				self.total = 0
			elif self.status == 'Marriage Within 6 Months Or 3 Months Of Childbirth':
				self.total = ((self.last_salary/2)*years)
			elif self.status == 'Force Majeure':
				self.total = ((self.last_salary/2)*years)

			elif self.status == 'With In Article 80':
				self.total = ((self.last_salary/2)*years)

			elif self.status == 'With Out Article 80':
				self.total = ((self.last_salary/2)*years)

			elif self.status == 'End By Employer':
				self.total = ((self.last_salary/2)*years)
			elif self.status == 'Expiration Of The Contract Or Agreement Of The Parties':
				self.total = ((self.last_salary/2)*years)

		elif years > 5 and years < 10:
			first_five = ((5*self.last_salary)/2)
			following_five = ((years - 5)*self.last_salary)

			if self.status == 'Left':
				throw(_("The worker is not worth the end of service reward."))
				self.total = 0
			elif self.status == 'Resign':
				self.total = (sum((first_five,following_five))*0.666666667)
			elif self.status == 'With In Article 81':
				self.total = sum((first_five,following_five))
			elif self.status == 'With Out Article 81':
				throw(_("The worker is not worth the end of service reward."))
				self.total = 0
			elif self.status == 'Marriage Within 6 Months Or 3 Months Of Childbirth':
				self.total = sum((first_five,following_five))
			elif self.status == 'Force Majeure':
				self.total = sum((first_five,following_five))
			elif self.status == 'With In Article 80':
				self.total = sum((first_five,following_five))
			elif self.status == 'With Out Article 80':
				self.total = sum((first_five,following_five))
			elif self.status == 'End By Employer':
				self.total = sum((first_five,following_five))
			elif self.status == 'Expiration Of The Contract Or Agreement Of The Parties':
				self.total = sum((first_five,following_five))
		elif years >= 10:
			first_five = ((5*self.last_salary)/2)
			following_years = ((years - 5)*self.last_salary)
			if self.status == 'Left':
				throw(_("The worker is not worth the end of service reward."))
				self.total = 0
			elif self.status == 'Resign':
				self.total = sum((first_five,following_years))
			elif self.status == 'With In Article 81':
				self.total = sum((first_five,following_years))
			elif self.status == 'With Out Article 81':
				throw(_("The worker is not worth the end of service reward."))
				self.total = 0
			elif self.status == 'Marriage Within 6 Months Or 3 Months Of Childbirth':
				self.total = sum((first_five,following_years))
			elif self.status == 'Force Majeure':
				self.total = sum((first_five,following_years))
			elif self.status == 'With In Article 80':
				self.total = sum((first_five,following_years))
			elif self.status == 'With Out Article 80':
				self.total = sum((first_five,following_years))
			elif self.status == 'End By Employer':
				self.total = sum((first_five,following_years))
			elif self.status == 'Expiration Of The Contract Or Agreement Of The Parties':
				self.total = sum((first_five,following_years))


	def validate_date(self):
		if self.date_of_birth and getdate(self.date_of_birth) > getdate(today()):
			throw(_("Date of Birth cannot be greater than today."))

		if self.date_of_birth and self.date_of_joining and getdate(self.date_of_birth) >= getdate(self.date_of_joining):
			throw(_("Date of Joining must be greater than Date of Birth"))

		elif self.date_of_leaving and self.date_of_joining and (getdate(self.date_of_leaving) <= getdate(self.date_of_joining)):
			throw(_("Date Of leaving must be greater than Date of Joining"))



@frappe.whitelist()
def create_user(employee, user = None, email=None):
	emp = frappe.get_doc("Employee", employee)

	employee_name = emp.employee_name.split(" ")
	middle_name = last_name = ""

	if len(employee_name) >= 3:
		last_name = " ".join(employee_name[2:])
		middle_name = employee_name[1]
	elif len(employee_name) == 2:
		last_name = employee_name[1]

	first_name = employee_name[0]

	if email:
		emp.prefered_email = email

	user = frappe.new_doc("User")
	user.update({
		"name": emp.employee_name,
		"email": emp.prefered_email,
		"enabled": 1,
		"first_name": first_name,
		"middle_name": middle_name,
		"last_name": last_name,
		"gender": emp.gender,
		"birth_date": emp.date_of_birth,
		"phone": emp.cell_number,
		"bio": emp.bio
	})
	user.insert()
	return user.name

def has_user_permission_for_employee(user_name, employee_name):
	return frappe.db.exists({
		'doctype': 'User Permission',
		'user': user_name,
		'allow': 'Employee',
		'for_value': employee_name
	})
