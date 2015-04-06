#!/bin/env python
################################################################################
# Who: James Conner
# When: Jan 28, 2013
# What: archive
# How: Sublime Text 2
# Version: 0.1.1
# Why: Archive program for analytic environments with multi-tiered storage
################################################################################
# Updates:
# Ver:Who:When:Why
# 0.0.1:James Conner:Jan 28, 2013:Initial Creation
# 0.0.8:James Conner:Feb 19, 2013:
#  Complete rework of hashing so it is more modular and performant
#  Fixed absolute pathing of linked directories (main())
#  Created perfMeta function, exports ElementTree xml data instead of old hash
#  Converted tdy to UTC, and added an iso8601 conversion function
#  Added a fileInfo function to collect os.stat data on files
#  Fixed main() to include os.path.realpath to dereference symlinks
# 0.0.9:James Conner:Feb 20, 2013:Exclude archive files from the tar process
# 0.1.0:James Conner:Feb 20, 2013:globbing of file input
# 0.1.1:James Conner:Aug 16, 2013:Adding sunburnt/solr metadata upload
################################################################################
# ToDo
# 1. Create an option using the SUPPRESS_HELP flag to allow disabling Solr 
#    metadata uploads.  The default value for the option would be 'true'.
# 2. Convert the deprecated 'exclude' option in tarObj() to the newer 'filter' 
#    option found in Python 2.7+
# 3. Provide better error trapping around the Solr upload in publishMeta()
# 4. Create a class for file objects.
# 5. Convert OptionParser to GetOpt
# 6. Iterable list for unarchiving
# 7. Change nohup to screen in the wrapper
# 8. Create a python installation package
# 9. Refactor some of  the code to remove duplicate lines
# 10. Make the Metadata service modular, so other services than Solr can be used
# 11. Multithread the file handling and hashing
# 12. Incorporate csv hashing code for field obfuscation/tokenization
################################################################################

################################################################################
# Import Modules
################################################################################
import os
import sys
import hashlib
import fnmatch
import datetime
import errno
import tarfile
import pwd
import grp
import csv
import shutil
import glob
import sunburnt
import xml.etree.ElementTree as ET
from optparse import OptionParser
from optparse import SUPPRESS_HELP
from functools import partial
from common_functions import *



################################################################################
# Option Parser
################################################################################
parser = OptionParser(version = "0.1.1")

parser.add_option('-a', '--all',
	dest='all_var',
	action="store_true",
	default=False,
	metavar='ALL',
	help=('Archive all files and directories within the current directory.'))

parser.add_option('-c', '--cancel',
	dest='cancel_var',
	default='',
	metavar='CANCEL',
	help=('Cancel the archive request and retrieve files from the archive.'))

parser.add_option('-f', '--filename',
	dest='filename_var',
	default='',
	metavar='ARCHFILENAME',
	help=('The file or directory to be archived.'))

parser.add_option('-u', '--unarch-filename',
	dest='unarch_filename_var',
	default='',
	metavar='UNARCHFILENAME',
	help=SUPPRESS_HELP)

parser.add_option('-d','--delimiter',
	dest='delimiter_var',
	default=',',
	metavar='DELIMIT',
	help=SUPPRESS_HELP)

parser.add_option('-g', '--groups',
	dest='groups_var',
	default='1000',
	metavar='USERGROUPS',
	help=SUPPRESS_HELP)

(opts, arg) = parser.parse_args()



################################################################################
# Global Variables
################################################################################
# The cwd variable is used if the "archive all" option is selected.  It is used
# to perform an os.listdir() to create a list of all files inside the curr dir
cwd = os.getcwd()

# The sudoUser variable is required to perform the permCheck.  It is used to
# downgrade the program to the permissions of the initial user, so the permCheck
# function can validate the user performing the archive process is authorized
# to do so.
sudoUser=os.getenv("SUDO_USER")
sudoGrps=[int(x) for x in opts.groups_var.split(",")]

# In order to verify the sudoUser has permissions to archive a directory, an
# empty file will be created in the directory to validate the user's access.
validationFile="archive_validation_check.test"

# The tdy variable grabs the current timestamp which will be used by fileStamp
tdy=datetime.datetime.utcnow()
tdyISO=tdy.isoformat()+"Z"

# fileStamp is the tdy tuple joined up as a string, so it can be used as the
# filename of the output tar file in the tarObj function.
fileStamp="_".join([str(tdy.year),str(tdy.month).zfill(2),str(tdy.day).zfill(2),str(tdy.hour).zfill(2),str(tdy.minute).zfill(2),str(tdy.second).zfill(2),str(tdy.microsecond).zfill(6)])

# The archiveDir is the name of the folder where the archives targzs are stored
# for each client.  The archiveDir is added onto the /mount/+1_dir/ path name.
# Example: /prod-01/tesco_uk/archive -> /mount/+1_dir/archiveDir
archiveDir="archive"
archiveExt=".tar"
archiveMetaExt=".xml"

# The details for the Solr Server.  The meta data is published to the Solr
# instance so that users can search for their archived files based on several
# meta data parameters.
solrServer="localhost"
solrPort="8080"
solrInstance="live"


################################################################################
# Functions
################################################################################

##### Included from common_functions:
##### Validations
## user_exists(user):
## uid_exists(user):
## group_exists(group):
## gid_exists(group):

##### CONVERSIONS
## user_to_uid(user):
## uid_to_user(user):
## group_to_gid(group):
## gid_to_group(group):

##### USER IN GROUP
## userInGrp(uid,gid):

##### PERMISSION OCTETS
## getOctects(objPath):


# PUBLISH META DATA TO SOLR
def publishMeta(mdList):
	""" Establish the Solr Instance, add the metadata, and commit it"""
	try:
		# Instantiate the interface to the Solr instance
		si = sunburnt.SolrInterface("http://%s:%s/solr/%s/" % (solrServer,solrPort,solrInstance))
		# Add the XML metadata to the instance
		si.add(mdList)
	except:
		raise
	finally:
		# Commit/Save the metadata
		si.commit()



# META DATA CREATION
def perfMeta(fileNameList,archPath,mnt,client):
	""" Create the metadata for the file for search engine """

	# Declare the archFile and metaFile locations
	archFile = os.path.join(archPath,fileStamp+archiveExt)
	metaFile = os.path.join(archPath,fileStamp+archiveMetaExt)

	# Create an empty list for the file/dir metadata
	mdList = []

	# Create the XML element "add".  This element is required
	# for Solr to add it to the instance.  All of the file
	# metadata xml 'doc' entries will go under this element.
	xmlTop = ET.Element("add")


	# For each file name in the list passed to the function
	for fileName in fileNameList:
		# Check if the file is an actual file
		if os.path.isfile(fileName):

			# Create an empty dict for the file
			fileDict={}

			fileDict = fileInfo(fileName)
			fileDict["id"] = perfHash(fileName)
			fileDict["market"] = client
			fileDict["mount"] = mnt
			fileDict["archive_name"] = archFile
			fileDict["archive_time"] = tdyISO
			fileDict["archive_owner"] = sudoUser

			# Create a 'doc' element under 'add' for the file data
			xmlRecord = ET.SubElement(xmlTop,"doc")

			# For each metadata key in the file dict, create a field
			# in the XML and add the value.
			for key in fileDict:
				field = ET.SubElement(xmlRecord,"field",name=key)
				field.text = str(fileDict[key])

			# For each file, add the meta data to the mdList[]
			mdList.append(fileDict)



		# The file wasn't a file, so check if it's a directory
		elif os.path.isdir(fileName):
			# It is a directory, so attempt to traverse it for file names.
			try:
				# os.walk() produces 3 pieces of information, only two of which
				# we're going to use:  root and files.
				for root,dirs,files in os.walk(fileName):
					# For each file that was discovered in the os.walk()
					for names in files:
						# Create a quick variable and set it to the path and name
						# of the file in question.
						fn=os.path.join(root,names)

						# Create an empty dict for the file
						fileDict={}

						fileDict = fileInfo(fn)
						fileDict["id"] = perfHash(fn)
						fileDict["market"] = client
						fileDict["mount"] = mnt
						fileDict["archive_name"] = archFile
						fileDict["archive_time"] = tdyISO
						fileDict["archive_owner"] = sudoUser

						# Create a 'doc' element under the 'add' for the file data
						xmlRecord = ET.SubElement(xmlTop,"doc")

						# For each metadata key in the file dict, create a field
						# in the XML and add the value.
						for key in fileDict:
							field = ET.SubElement(xmlRecord,"field",name=key)
							field.text = str(fileDict[key])

						# For each file, add the meta data to the mdList[]
						mdList.append(fileDict)


			# Couldn't os.walk() the directory.  Probably a permissions problem.
			except:
				raise

		# Not a file, or a directory, so don't hash it.
		else:
			pass

	# Write out the metaFile with the full XML data of all the files
	ET.ElementTree(xmlTop).write(metaFile)

	# Publish the metadata to Solr
	publishMeta(mdList)



def perfHash(fileName):
	""" Perform a SHA1 hash against a file.  Constructed using partial buffers to avoid memory problems"""
	try:
		# Open the file so we can read chunks at a time to prevent a memory
		# over run when dealing with very large files
		with open(fileName, mode='rb') as f:
		# Set d to the appropriate hash library, sha1 in this case
			d = hashlib.sha1()
			# For each 1024M block of partial data
			for buf in iter(partial(f.read, 1073741824), b''):
				# Update the hash object with the 1024M block
				d.update(buf)
		return(d.hexdigest())
	except:
		raise



def fileInfo(fileName):
	""" Create a basic dictionary containing file information and return it"""
	fileData=os.stat(fileName)
	fileDict={}
	fileDict["atime"]=time8601(fileData.st_atime)
	fileDict["mtime"]=time8601(fileData.st_mtime)
	fileDict["ctime"]=time8601(fileData.st_ctime)
	fileDict["owner"]=uid_to_user(fileData.st_uid)
	fileDict["group"]=gid_to_group(fileData.st_gid)
	fileDict["size"]=fileData.st_size
	fileDict["mode"]=oct(fileData.st_mode)[-3:]
	fileDict["name"]=os.path.basename(fileName)
	fileDict["path"]=os.path.dirname(fileName)
	return(fileDict)



def time8601(tzTimeStamp):
	"""Create an ISO 8601 timestamp"""
	# Solr requires a combined ISO8601 timestamp format with UTC (Z = Zulu) flag
	return(datetime.datetime.utcfromtimestamp(tzTimeStamp).isoformat()+"Z")



def splitPath(path): 
	"""Converts a path to a list. Absolute paths are handled correctly""" 

	# Take the path and iterate over it functionally with the OS separater object
	dir_list = filter(lambda x: len(x) > 0, path.split(os.sep)) 

	# The path splitter will remove the beginning slash, so if the path was
	# originally an absolute path, put a slash at the beginning of the list.
	if path.startswith("/"): 
		dir_list.insert(0, "/") 
	return(dir_list)



def findMount(obj,i=0):
	"""Return the first mount path after root, the remaining path and the client dir"""

	# Split the path object into discrete components
	obj_atomic=splitPath(obj)

	# Set the empty variables for obj_mount and obj_remainder
	obj_mount,obj_remainder="",""

	# Loop over the number of elements in the path object
	while i < len(obj_atomic):

		# Attempt to discover the mount path by joining the element to the variable
		obj_mount = os.path.join(obj_mount,obj_atomic[i])

		# Root (/) is a mounted filesystem, but not the one we're looking for, so
		# ignore the first loop round, and test if the obj_mount is a filesystem
		if os.path.ismount(obj_mount) and i > 0:

			# If we've found the mount path, then join up the remainder of the path
			# into a single variable to be returned.
			obj_remainder=os.path.join(*obj_atomic[i+1:])

			# Return the mount path, the remainder of the path, and the first
			# directory after the mount path (to be used in the mkdir tree)
			return(obj_mount,obj_remainder,obj_atomic[i+1])
			break
		i+=1



def tarExclude(fileName):
	"""Determine if the filename needs to be excluded from the tarObj function"""
	TorF = False
	if fileName.find("archive.out") > -1:
		TorF = True
	return(TorF)



def tarObj(fileNameList,archPath):
	"""Tar a file or directory"""
	# The checkPerm function downgraded the privs of the process to the
	# original sudo user.  Now re-escalate the privledges to root so we 
	# can create the tar while preserving ownership and permissions
	# Use a try/except/else framework so we can handle errors
	os.setuid(0)
	os.setgid(0)
	try:

		tarFile=os.path.join(archPath,fileStamp+archiveExt)

		# Attempt to open the file with the datetime prefix.  File is opened
		# as a gzipped compressed tar file. This action is performed as root.
		with tarfile.open(tarFile,mode="w",bufsize=102400) as tarobj:
			for i in fileNameList:
				# Add the target object to the gzipped tar archive
				tarobj.add(i,exclude=tarExclude)
				print("Completed: "+i)
				# Writing completed, now close the archive
			tarobj.close()
			print("Archive file: "+tarFile)
			return(True)

	# Check for any errors     
	except:
		# Problem with the permissions check, exit immediately
		print("Error with permissions check")
		sys.exit(5000)



def unTarObj(fileName):
	"""unTar a file or directory"""
	try:
		# Open the file and extract all files, assuming absolute paths in the tar
		with tarfile.open(fileName,"r") as tarobj:
			tarobj.extractall('/')
			tarobj.close()
	except:
		raise



def rmFiles(fileNameList,archPath):
	"""Remove the original files after they have been archived"""
	# Set a local variable for the person who executed the script
	sudoID=user_to_uid(sudoUser)
	
	for fileName in fileNameList:
		# Let's be certain who we are ... set user/group to root
		os.setuid(0)
		os.setgid(0)

		# Get the group ownership of the file in question
		groupID=os.stat(fileName)[5]

		# Check to see if the original user is in the group
		if userInGrp(sudoID,groupID) == True:
			# Downgrade the user perms to the sudo user who instantiated the process
			os.setegid(groupID)
		else:
			# User wasn't in the group, so let's use the default user's group
			os.setegid(1000)

		# Drop user privs to the original user
		os.seteuid(sudoID)
		

		# Perform all tests as the original user
		# Trying to remove a mount point is not going to work
		if os.path.ismount(fileName):
			print("Cannot remove a mount point!")
			sys.exit(7003)
			
		# Test if fileName is a file
		elif os.path.isfile(fileName):
			try:
				os.remove(fileName)
			except OSError:
				print("Error removing file")
				raise
				sys.exit(7002)

		# Test if fileName is a directory
		elif os.path.isdir(fileName):
			try:
				shutil.rmtree(fileName)
			except OSError:
				print("Error removing directory")
				raise
				sys.exit(7001)

		# If fileName is something else (block,pipe,etc), exit!
		else:
			print("Unknown filetype set for deletion, erroring out")
			raise
			sys.exit(7000)



def checkPerm(fileNameList):
	"""Drop permissions and check user is allowed to access files"""
	sudoID=user_to_uid(sudoUser)

	for fileName in fileNameList:
		os.setuid(0)
		os.setgid(0)
		os.setgroups([0])

		# Check to see if the object desired for archive is a mount point
		# Error out immediately if it is a mount point
		if os.path.ismount(fileName):
			print("Cannot archive a mount point")
			sys.exit(1000)

		# Check to see if the object desired for archive is a directory
		# If it is a directory, pythonically attempt to create a file in
		# the directory to determine permission access.
		elif os.path.isdir(fileName):
			groupID=os.stat(fileName)[5]

			if userInGrp(sudoID,groupID) == True:
				# Downgrade the user perms to the sudo user who instantiated the process
				os.setegid(groupID)
			else:
				os.setegid(1000)
			os.setgroups(sudoGrps)
			os.seteuid(sudoID)


			if os.stat(fileName).st_uid == sudoID or os.stat(fileName).st_gid in sudoGrps:
			
				try:
					# Create the test file inside the target directory
					fp = open(os.path.join(fileName,validationFile),"w")
				# Capture IO errors
				except IOError as e:
					# Check if the error is EACCES, which means permissions denied
					if e.errno == errno.EACCES:
						print("Access Denied")
						sys.exit(1010)
					# Not a permission error, so raise the error as unhandled
					raise
				# The try succeeded and no exceptions encountered, so continue
				else:
					# Using the file object opened in the try
					with fp:
						# Close the empty file object 
						fp.close()
						# Now pythonically remove the empty file object, since it
						# shouldn't be included in the archive.  Use a try/except
						# to remove the file if it exists, otherwise just pass this
						# step
						try:
							os.remove(os.path.join(fileName,validationFile))
						except OSError:
							pass
						# Set the uid of the program back to root
						os.setuid(0)
						os.setgid(0)
						# All tests passed, return validation to calling function/process
						#print("Access Granted")
						return(True)
			else:
				print("You do not own the directory, and are not in the group")
				sys.exit(1050)


		# Check to see if  the object desired for archive is a file
		elif os.path.isfile(fileName):

			groupID=os.stat(fileName)[5]
			if userInGrp(sudoID,groupID) == True:
				# Downgrade the user perms to the sudo user who instantiated the process
				os.setegid(groupID)
			else:
				os.setegid(1000)
			os.setgroups(sudoGrps)
			os.seteuid(sudoID)

			# Pythonically attempt to validate access by opening the file
			try:
				fp = open(fileName,'ab')
			# Capture IO errors
			except IOError as e:
				# Check if the error is EACCES, which means permission denied
				if e.errno == errno.EACCES:
					print("Access Denied")
					sys.exit(1020)
				# Not a permission error, so raise the error as unhandled
				raise
			# The try succeeded and no exceptions encountered, so continue
			else:
				# Using the file object opened in the try
				with fp:
					# Close the file object
					fp.close()
					# Set the uid of the program back to root
					os.setuid(0)
					os.setgid(0)
					# All tests passed, return validation to calling function/process
					#print("Access Granted")
					return(True)

		# The target for archive isn't a dir, file or mount, so exit immediately
		else:
			print("Object type not handled")
			sys.exit(1001)

	return(True)



def main():
	"""Primary function of the application.  Process control occurs here."""
	try:

		# Create an empty list which will be passed to the child functions for iteration. 
		fileList=[]

		# Check for a filename.  
		if opts.filename_var:
			if os.path.exists(opts.filename_var) or "*" in opts.filename_var:

				for i in glob.glob(opts.filename_var):
					# Filename option is set, append the filename argument to the empty fileList.
					fileList.append(os.path.realpath(os.path.normpath(os.path.abspath(i))))

				mnt,remainder,client=findMount(os.path.realpath(os.path.normpath(os.path.abspath(opts.filename_var))))
				archPath=os.path.join(mnt,client,archiveDir,str(tdy.year).zfill(2),str(tdy.month).zfill(2))

				try:
					os.makedirs(archPath,0700)
				except OSError:
					pass

				if checkPerm(fileList) == True:
					# Set the uid of the program back to root, just in case
					os.setuid(0)
					os.setgid(0)
					# Pass the fileList containing the filename argument to the perfMeta function.
					perfMeta(fileList,archPath,mnt,client)
					# Pass the fileList containing the filename argument to the tarObj function.
					if tarObj(fileList,archPath) == True:
						rmFiles(fileList,archPath)
				else:
					print("Permissions error.")
					sys.exit(6000)

			else:
				print("File does not exist.")
				sys.exit(6001)


		# Check if the "archive all" option is set.
		elif opts.all_var:
			# Reset the fileList to the list of all files in the current dir.
			for i in os.listdir(cwd):
				fileList.append(os.path.realpath(os.path.normpath(os.path.abspath(i))))

			if fileList:

				mnt,remainder,client=findMount(os.path.realpath(os.path.normpath(os.path.abspath(cwd))))
				archPath=os.path.join(mnt,client,archiveDir,str(tdy.year).zfill(2),str(tdy.month).zfill(2))

				try:
					os.makedirs(archPath,0700)
				except OSError:
					pass

				if checkPerm(fileList) == True:
					# Set the uid of the program back to root
					os.setuid(0)
					os.setgid(0)
					# Pass the fileList containing the filename argument to the perfMeta function.
					perfMeta(fileList,archPath,mnt,client)
					# Pass the fileList containing the filename argument to the tarObj function.
					if tarObj(fileList,archPath)== True:
						rmFiles(fileList,archPath)
				else:
					print("Permissions error.")
					sys.exit(6000)

			else:
				print("No files in directory.")
				sys.exit(6002)

		# Check if the cancel option was selected.
		elif opts.cancel_var:
			# Since the archive filesystem is on the live filesystem, there is no way to cancel.
			print("The cancel option no longer exists.\nPlease use the unarchive option.")


		# Check if the unarchive option is set.
		elif opts.unarch_filename_var:
			# Currently does not take a list argument for iteration.  Perhaps future version.
			# fileList.append(opts.unarch_filename_var)
			# Pass the argument for the unarchive option directly to the unTarObj function.
			unTarObj(opts.unarch_filename_var)


		# Any other options are invalid.
		else:
			# Generic error.
			print("Unknown option selected.")
			sys.exit(2000)

	# Something unexpected happened, error out.
	except:
		#print("Unknown exception.")
		#sys.exit(2001)
		raise



################################################################################
# Program Execution
################################################################################

if __name__ == "__main__":
	main()
