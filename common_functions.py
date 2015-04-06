import os
import sys
import pwd
import grp
################################################################################
# Common Functions
################################################################################
# VALIDATIONS
def user_exists(user):
	"""Verify user is present on system(s)"""
	try:
		if pwd.getpwnam(user):
			return True
	except KeyError:
		return(False)


def uid_exists(user):
	"""Verify UID is present on system(s)"""
	try:
		if pwd.getpwuid(int(user)):
			return True
	except KeyError:
		return(False)


def group_exists(group):
	"""Verify group is present on system(s)"""
	try:
		if grp.getgrnam(group):
			return True
	except KeyError:
		return(False)


def gid_exists(group):
	"""Verify GID is present on system(s)"""
	try:
		if grp.getgrgid(group):
			return True
	except KeyError:
		return(False)


# CONVERSIONS
def user_to_uid(user):
	"""Translate a username to a uid."""
	try:
		username = pwd.getpwnam(user)[2]
		return username
	except KeyError:
		return(False)


def uid_to_user(user):
	"""Translate a uid to a username."""
	try:
		username = pwd.getpwuid(int(user))[0]
		return username
	except KeyError:
		return(False)


def group_to_gid(group):
	"""Translate a groupname to a gid."""
	try:
		groupname = grp.getgrnam(group)[2]
		return groupname
	except KeyError:
		return(False)


def gid_to_group(group):
	"""Translate a gid to a groupname."""
	try:
		groupname = grp.getgrgid(int(group))[0]
		return groupname
	except KeyError:
		return(False)


# USER IN GROUP
def userInGrp(uid,gid):
	"""Determine if a user is part of a group"""
	if pwd.getpwuid(uid)[0] in grp.getgrgid(gid)[3]:
		return(True)
	else:
		return(False)


# PERMISSION OCTETS
def getOctects(objPath):
	"""Stat a file object and return the last 3 characters of st_mode"""
	return(oct(os.stat(objPath).st_mode)[-3])