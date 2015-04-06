#!/bin/env python
#################################################################
# Who: James Conner
# When: June 16, 2008
# What: csv_hash.py
# Version: 1.0.3
# Why: Encrypt fields within a CSV file
#################################################################
# Updates:
# Ver:Who:When:Why
# 0.0.1:James Conner:Jun 16 2008:Initial creation
# 0.0.2:James Conner:Jul 07 2008:Added multi field hashing
# 1.0.0:James Conner:Aug 21 2008:Added MD5 output of SHA256 hash
# 1.0.1:James Conner:Aug 21 2008:Fixed field check
# 1.0.2:James Conner:Nov 29 2011:Added inline salt functionality
# 1.0.3:James Conner:Nov 29 2011:Added file source salt
#################################################################

#################################################################
# Import Modules
#################################################################
import os
import sys
import string
import hashlib
import csv
from optparse import OptionParser

#################################################################
# Global Variables
#################################################################

#################################################################
# Option Parser
#################################################################
parser = OptionParser(version = "1.0.3")

parser.add_option('-d','--delimiter',
    dest='delimiter_info',
    default=',',
    metavar='DELIMIT',
    help=('The delimiter.  Default is \',\'.'))

parser.add_option('-i','--infile',
    dest='infilename_info',
    default='',
    metavar='INFILENAME',
    help=('Name of the input file. This is a required variable.'))

parser.add_option('-f','--field',
    dest='field_info',
    action='append',
    type='int',
    metavar='FIELDNUM',
    help=('Which field to encrypt. This is a required variable.'))

parser.add_option('-o','--outfile',
    dest='outfilename_info',
    default='outfile.csv',
    metavar='OUTFILENAME',
    help=('Name of the output file'))

parser.add_option('--md5',
    dest='md5_info',
    action='store_true',
    default=False,
    metavar='MD5',
    help=('Use MD5 against the SHA256 hash.'))

parser.add_option('-s','--salt',
    dest='salt_info',
    default='',
    metavar='SALT',
    help=('Use a salt value against the data prior to hashing. If the string is an existing filename, it will read the first line of the file and use it as the salt.  Otherwise, the string will be used as the salt.'))

(opts, arg) = parser.parse_args()
 
#################################################################
# Functions
#################################################################

def check_options(option,option_name):
    """Simple check to see if the required options are set"""
    if not option:
        print "ERROR: %s variable has not been assigned!" % option_name
        sys.exit(10)


def perf_hash (DATA,MD5):
    """ Perform the actual hashing function against a cell of data"""
    # Look to see if the MD5 flag has been set to true.  If it
    # has, then perform a sha256 (stripping off the returned \n),
    # and MD5 the sha256.  This should result in a unique string,
    # which is considerably smaller thant the sha256.
    if MD5 is True:
        TEMP_DATA = hashlib.sha256(DATA).hexdigest().strip()
        return (hashlib.md5(TEMP_DATA).hexdigest())
    else:
    # The MD5 flag wasn't set, so just return the sha256 results.
        return(hashlib.sha256(DATA).hexdigest().strip())


def csv_file (FILENAME,DELIMITER,FIELDNUM,OUTFILE,MD5FLAG,SALT):
    """This function performs the csv file handling, and passes the field information to the perf_hash() function"""
    # Create a variable from the SALT metavar.  If the SALT 
    # metavar ends up being a filename, then the SALTVAR is 
    # overwritten with the first line from the file in a later 
    # "if" condition.  
    # The SALTVAR variable is part of the string passed to the
    # perf_hash() function.
    SALTVAR=SALT

    # Try to open the source file for reading.  If any error, 
    # just raise the error without fancy trapping.
    try:
        r = csv.reader(open(FILENAME, 'r'), dialect='excel', delimiter=DELIMITER)
    except:
        raise

    # Try to open the destination file for writing.  If any error,
    # just raise the error without fancy trapping.  Most common
    # error will be inability to write to directory.
    try:
        w = csv.writer(open(OUTFILE, 'w'), dialect='excel', delimiter=DELIMITER)
    except:
        raise

    # Check if the SALT metavar has been set.
    if SALT:
        # The SALT metavar not null, check to see if it's a file.
        if os.path.isfile(SALT):
            try:
                # SALT was a file, so now open the file, read the
                # first line into SALTVAR, and close the file.
                f = open(SALT,'r')
                SALTVAR = f.readline().strip()
                f.close()
            except:
                raise
        # Nope, the SALT metavar wasn't a file, just a string.
        else:
            try:
                # Since SALT was just a string, we want to keep
                # a record of what was used during the hash, just
                # in case it's needed later, or if hashing other
                # files to get consistent hash output.

                # Open a file with the extention of .salt, write
                # out the value of the SALT metavar, and then
                # close the file.
                f = open(OUTFILE+'.salt','w')
                f.write(SALT)
                f.close()
            except:
                raise

    # Now to cycle through the rows, checking each field to hash
    for rows in r:
        # Cycle through the fields entered for hashing.  Could
        # be multiple fields, thus the for loop.
        for f in FIELDNUM:
            # Set the value of the row/field in question to the
            # output of the perf_hash() function
            rows[int(f)] = perf_hash(SALTVAR+rows[int(f)],MD5FLAG)

        try:
            # Write out the row, with the hashed field(s)
            w.writerow(rows)
        except:
            # Something went wrong!
            raise

#################################################################
# Program Execution
#################################################################

if __name__ == "__main__":
    try:
        # Validate a filename was passed to hash
        check_options(opts.infilename_info, "infilename_info")
    except:
        raise

    try: 
        # Validate at least one field was passed to hash
        check_options(opts.field_info, "field_info")
    except:
        raise

    # Execute the primary function
    csv_file(opts.infilename_info, opts.delimiter_info, opts.field_info, opts.outfilename_info, opts.md5_info, opts.salt_info)