# **cfs\_archive : The StorNext Clustered File System Archive utility**

An application for archiving data on StorNext Clustered FileSystems (CFS) and Libraries.

&nbsp;

&nbsp;

## **Objective**

The StorNext Clustered FileSystems (CFS) can be quite massive: Petabytes in size and Billions of files.  One of the unique features of StorNext is that it also has Integrated Life-Cycle Management (ILM) in the CFS, which is able to push data down to lower cost disks and eventually tape using a policy based system.  Once data is pushed down to tape, it can also automatically replicate to multiple tapes, so one is kept in the tape library for on-line access and another ejected for off-site archival.  Standard Backup And Recovery (BAR) applications (EMC Networker, IBM Tivoli, HP DataProtector, etc) cannot integrate with this capability, so an alternative application had to be created which fufilled all of the requirements.

&nbsp;

&nbsp;

## **Requirements**

There were many requirements behind the creation of the CFS Archive:

* **Simple to Operate** - The product is internal user-facing and needs to be operated with minimal training or reference.
* **Non-Delayed Execution** - Many archiving systems delay execution until a certain time of day.  With large data volumes, that design is not viable.
* **Referencable Metadata** - Basic Metadata about the objects being archived have to go into a data catalog (Solr) so it can be easily located again when needed.
* **Project Bundling** - All assets associated with a project should be grouped together, not just data.  Thus the directory archiving is included.
* **User Directed Archiving** - Users need the ability to execute their own archiving as needed, to control their own storage space.
* **User Directed Unarchiving** - Users cannot wait for the typical IT or Data Service Level Agreements (SLAs) to locate and recover needed data.
* **Group Interoperability** - Users need the ability to over-ride sub-dir/file ownership and permissions on very large projects, to perform archives.  This is not typically advised, and is avoided in most BAR software.
* **Reliable Archiving Replacement** - Standard Backup And Recover (BAR) programs do not integrate with the StorNext CFS as needed. The replacement archive utility needs to be as reliable as the standard products.
* **Programmatic Execution for Automation** - In ETL job chains, iterim data is constantly generated, some of which needs to be saved for QA and long-term analysis.  The program has to easily integrate with other scripted environments.
* **Integrated Life-cycle Management (ILM)** - Achieve cost and performance gains by pushing "warm" data through the ILM system.
* **Multi-Tenant Storage Architecture** - The archive program has to keep archived tenant data separated from other tenants that share the storage namespace.

&nbsp;

&nbsp;


## **Installation & Configuration**


### OS Dependencies
* RHEL/CentOS 5 or higher (should be fine on other Linux platforms, but not tested)
* Standard StorNext Filesystem layout of `/<device_name>/<tenant>/<data>/...` is required.
* Sudoers


### Python Dependencies
* Python 2.6 or higher (tarfile module requires the exclude option in Python 2.6)
* Sunburnt (for Solr)
* httplib2 or requests (for Solr)
* lxml (for Solr)
* pytz

### File Descriptions
* cfs_archive = The wrapper script
* cfs_archive.py = The program
* common_functions.py = Common library file
* README.md = This document
* csv_hash.py = Field hashing utility, often used to obfuscate data prior to archiving


### Installation Steps
1. Wrapper, CFS Archive Program, csv_hash and common_functions library
 * Place the wrapper script and archive program somwehre in the $PATH.  `/usr/local/bin` is recommended.
 * Place the common_functions library and csv_hash.py program somewhere in the Python library path (Ex: `/usr/lib64/python2.6/`)
2. Sudoers
 * Add an entry to /etc/sudoers, pointing to the location of the archive program.  
 * `All    ALL = (ALL) NOPASSWD: /usr/local/bin/cfs_archive.py`
3. Solr Cluster
 * If no Solr server is available to push Metadata into, you can disable this feature by commenting out the line `publishMeta(mdList)` in the `perfMeta()` function.
 * If a Solr environment is available, it works with both a singleton and a clustered configuration.
 * Only Tomcat backed Solr environments have been tested.
4. StorNext Information Life-cycle Management Policies
 * Create the appropriate ILM policy on the archive directory for each tenant as desired.  This will control how long the data will reside on the lower cost storage, and when it will be pushed out to the Tape Arrays.  The storage backend utilized (disk or tape) is transparent to the users.  Even if the data resides on tape, there will be a "tombstone" marker in the filesystem on disk.  When the "tombstone" is accessed, it will automatically instantiate the recovery of the data from the Tape Array to the disk storage.  Additionally, the tombstone can be 0 bytes, or it can contain enough data so that the user can immediately access the beginning of the file from disk, while the remainder is spinning up in the Tape Array.  This is all configurable in the StorNext policies.


### Configuration Steps
1. Edit the paths found in the small wrapper script (cfs_archive) to match the location of the cfs_archive.py program.
2. Comment out the line `publishMeta(mdList)` in the `perfMeta()` function if no Solr cluster will be used for Metadata collection.
3. Edit the "archive\*" and "solr\*" variables in the "Global Variables" to match your environment.


### Solr Search and Recovery (SSAR) Interface
##### Description
A Python based application which uses the [Solr API for Python] (https://cwiki.apache.org/confluence/display/solr/Using+Python) to pass queries and return results from the Solr cluster.  Web interface included.
* Not covered in this documentation


### XML Search and Recovery (XSAR) Interface
##### Description
A Python based application which uses the [ElementTree XML API] (https://docs.python.org/2/library/xml.etree.elementtree.html) to query and return results from the XML metadata files directly in the archive namespace of the CFS.
* Not covered in this documentation

&nbsp;

&nbsp;


## **Output Details**
### Type of outputs
There are four outputs of this program.
1. The data tar file
2. The metadata XML file
3. The archive.out job file
4. The Solr metadata XML push

When the cfs_archive application is executed, one of the tasks is to evaluate the tenant path (Ex: `/<device_name>/<tenant>/<data>/`), and create the appropriate archive path (Ex: `/<device_name>/<tenant>/<archPath>/`) if it does not already exist.  Additionally, it creates year and month subdirectories under the archive path, as well (Ex: `/<device_name>/<tenant>/<archPath>/<year>/<month>`).  The data tar file and the metadata XML file are placed inside the appropriate month subdirectory.

The archive.out file is created by the wrapper in the current working directory.  It contains the the names of the files archived within data tar file and the metadata XML file and any errors that are raised during the process.

The last output of the program is the push of the metadata in XML format to a Solr instance.  This is the same metadata that is created for the output XML file.  Pushing the metadata to Solr creates an easily searchable catalog of metadata concerning the files that have been archived, as well as some metadata regarding the archive process itself.  All metadata fields are searchable in Solr.


### Example showing tar, xml and out files:
```bash
[james@server /prod-01/tenant/project/]$ date
Wed Apr  1 16:33:29 EDT 2015

[james@server /prod-01/tenant/project/]$ touch testfile

[james@server /prod-01/tenant/project/]$ cfs_archive -f testfile

[james@server /prod-01/tenant/project/]$ tail -n 1 archive.out
Archive file: /prod-01/tenant/archive/2015/04/2015_04_01_20_35_10_176240.tar

[james@server /prod-01/tenant/project/]$ ls -AFlh /prod-01/tenant/archive/2015/04/
total 8K
-rw-r--r-- 1 james  james 1.6K Apr 01 20:35 2015_04_01_20_35_10_176240.tar
-rw-r--r-- 1 james  james 2.5K Apr 01 20:35 2015_04_01_20_35_10_176240.xml
```


### Metadata Objects
##### Archive Metadata
* Archive File Name
* Archive Time
* Archive Initiator

##### Per File Metadata
* Filename
* Sha1 Hash
* Tenant/Client
* Mount Point
* Atime
* Mtime
* Ctime
* Owner
* Group
* Size
* Mode
* Path

&nbsp;

&nbsp;


## **Examples of Use**
##### Archive the entire contents of a directory.  All files and sub-directories will be archived.

```bash
[james@server /prod-01/tenant/project/]$ ls -AFlh
total 36K
drwxr-sr-x 2 james  james 4.0K Mar 31 00:23 data/
drwxr-sr-x 2 james  james 4.0K Mar 31 18:31 lib/
-rw-r--r-- 1 james  james 1.6K Mar 31 16:16 step1.R
-rw-r--r-- 1 james  james 2.5K Mar 31 00:55 step2.R
-rw-r--r-- 1 james  james 2.4K Mar 30 23:42 step3.R
-rw-r--r-- 1 james  james 2.2K Mar 30 23:19 step4.R
-rw-r--r-- 1 james  james 6.8K Mar 31 00:12 step5.R
-rw-r--r-- 1 james  james  999 Mar 31 05:31 step6.R

[james@server /prod-01/tenant/project/]$  cfs_archive -a

[james@server /prod-01/tenant/project/]$ ls -AFlh
total 4K
-rw-r--r-- 1 james  james 3.6K Apr  1 16:16 archive.out

[james@server /prod-01/tenant/project/]$ ls -AFlh /prod-01/tenant/archive/2015/04/
total 16K
-rw-r--r-- 1 james  james 9.6K Apr 01 16:16 2015_04_01_16_16_12_176240.tar
-rw-r--r-- 1 james  james 3.5K Apr 01 16:16 2015_04_01_16_16_12_176240.xml
```
&nbsp;

##### Archive a single file or directory.

```bash
[james@server /prod-01/tenant/project/]$ ls -AFlh
total 36K
drwxr-sr-x 2 james  james 4.0K Mar 31 00:23 data/
drwxr-sr-x 2 james  james 4.0K Mar 31 18:31 lib/
-rw-r--r-- 1 james  james 1.6K Mar 31 16:16 step1.R
-rw-r--r-- 1 james  james 2.5K Mar 31 00:55 step2.R
-rw-r--r-- 1 james  james 2.4K Mar 30 23:42 step3.R
-rw-r--r-- 1 james  james 2.2K Mar 30 23:19 step4.R
-rw-r--r-- 1 james  james 6.8K Mar 31 00:12 step5.R
-rw-r--r-- 1 james  james  999 Mar 31 05:31 step6.R

[james@server /prod-01/tenant/project/]$  cfs_archive -f data

[james@server /prod-01/tenant/project/]$ ls -AFlh
total 36K
drwxr-sr-x 2 james  james 4.0K Mar 31 18:31 lib/
-rw-r--r-- 1 james  james 1.6K Mar 31 16:16 step1.R
-rw-r--r-- 1 james  james 2.5K Mar 31 00:55 step2.R
-rw-r--r-- 1 james  james 2.4K Mar 30 23:42 step3.R
-rw-r--r-- 1 james  james 2.2K Mar 30 23:19 step4.R
-rw-r--r-- 1 james  james 6.8K Mar 31 00:12 step5.R
-rw-r--r-- 1 james  james  999 Mar 31 05:31 step6.R
-rw-r--r-- 1 james  james 1.6K Apr  1 16:18 archive.out

[james@server /prod-01/tenant/project/]$ ls -AFlh /prod-01/tenant/archive/2015/04/
total 12K
-rw-r--r-- 1 james  james 8.6K Apr 01 16:18 2015_04_01_16_18_19_176240.tar
-rw-r--r-- 1 james  james 1.5K Apr 01 16:18 2015_04_01_16_18_19_176240.xml
```

&nbsp;

##### Unarchive a data file.

```bash
[james@server /prod-01/tenant/project/]$  cfs_archive -u /prod-01/tenant/archive/2015/04/2015_04_01_16_18_19_176240.tar
```

&nbsp;

&nbsp;


## **Architecture**
##### Design Decisions
* Since this program erases data after the archive process, any non-trivial errors cause the program to exit and raise the error.  Additional programmatic error handling could be included in the application, but it is preferred to intervene manually due to the sensitivity of the process.
* Python was picked as the language of choice due to the varity of actions incurred in the program (file handling, hashing, xml generation, metadata publishing, permissions munging, text parsing, etc).  Python could handle the requirements easily.
* Classes were avoided predominately due to supportability within the company. Few of the support staff are Object Oriented programmers.
* Software compression was deliberately not used as part of the archive process.  When data is pushed through the ILM system and onto tape, the Tape Arrays utilize hardware based compression.
* Software encryption for data at rest was deliberately not used as well, since the tape libraries also feature hardware based encryption for data at rest in the ILM system.
* Despite having the program run as root via sudo, many of the tests for file access drop the elevated privileges and test as the user and group(s).  This allows for the scenario where the group owner of a directory can archive all subdirectories, even if they aren't the owner or in the correct group for the subdirectories.
* The method of testing for file access, instead of evaluating permissions, follows the pythonic [EAFP] (https://docs.python.org/2/glossary.html) (easier to ask forgiveness than permission) style.
* Prevent the users from being able to do anyting destructive by making the archives immutable from the user's perspective.

&nbsp;

&nbsp;


## **Future enhancements**
1. Create an option using the SUPPRESS_HELP flag to allow disabling Solr metadata uploads.  The default value for the option would be 'true'
2. Convert the deprecated 'exclude' option in `tarObj()` to the newer 'filter' option found in Python 2.7+
3. Provide better error trapping around the Solr upload in `publishMeta()`
4. Create a class for file objects
5. Convert OptionParser to GetOpt
6. Iterable list for unarchiving
7. Change nohup to screen in the wrapper
8. Create a python installation package
9. Refactor some of  the code to remove duplicate lines
10. Make the Metadata service modular, so other services than Solr can be used
11. Multithread the file handling and hashing
12. Incorporate csv hashing code for field obfuscation/tokenization
13. Use mock to create full unit test scripts.  

&nbsp;

&nbsp;

## **Testing**
Unit testing scripts need to be written with mock for ongoing development support.  Initially, since the functions are fairly small, I performed unit testing by hand using print statements and sample test files for testing explicit scenarios, but that is unsustainable for long term support.  Mock's 'action/assertion' pattern works well with the architecture of this program, and the patch decorator will allow for easy object replacement during the tests.

&nbsp;

&nbsp;


## **Information About StorNext**

The StorNext filesystem from Quantum is a horizontally scalable clustered filesystem, capable of storing Petabytes of data within a single namespace.  It also includes a unique Integrated Life-cycle Management (ILM) capability, which enables users to push data to cheaper tiers of storage, without grossly impacting performance. Frequently cited users of StorNext are CERN, ABC, Disney, NBC, and the BBC.

[StorNext Website] (http://www.stornext.com/)

[StorNext Technical Briefing Document] (https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=3&cad=rja&uact=8&ved=0CDQQFjAC&url=https%3A%2F%2Fiq.quantum.com%2FexLink.asp%3F6794293OT46K58I40409072&ei=8jcbVfvvFrb9sASZwYHIDg&usg=AFQjCNFCZfaAmWMcKzVLxZXF2ymvsNkwrg&sig2=6Px6cSRosBcNNaoLuDCuSg)

[An Overview Video] (https://www.youtube.com/watch?v=Dor11DecGZg)

&nbsp;

&nbsp;

## **Information About the Author**
[LinkedIn Profile] (https://www.linkedin.com/in/jamesbconner)

[StackOverflow Profile] (http://stackoverflow.com/users/2073581/jamcon)


