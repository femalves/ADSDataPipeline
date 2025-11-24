
Reads flat/classic files with (mostly) non-bibliographic data and
sends nonbib and metrics protobufs to master pipeline.

Note: while in the Classic back office these files are sorted case insensitively, local copies will be created in the container for this pipeline that will be sorted case sensitively! This logic is not part of the code base in this Github repo, but in the repository that is used to create and deploy the containers.

# Overview
There are ~30 input files.  Each row in every file begins with a bibcode. It is followed by a tab character and then
data from that bibcode.

The nonbib protobuf holds a variety of information for a specific
bibcode.  It is computed by reading all the data for a bibcode from
every file and then massaging the data a bit.  Computing the metrics
protobuf is not as straightforward.  Computing the metrics values
requires the citation network, the reference network and the list of 
refereed bibcodes.  All three of these are cached in memory in simple
python containers.

Master pipeline uses a postgres database to store results from the
various pipelines (nonbib, bib, fulltext, etc.).  Pipelines
avoid sending data to master for bibcodes that have not changed.
Nonbib computes which bibcodes have changed data by comparing yesterday's
data files to today's data files.  It computes a list of changed
canonical bibcodes with a series of unix shell commands.  The command
to compute changed bibcodes is 
```
python3 run.py COMPUTE_DIFF
```
Changes to Classic bibcodes are stored in the file at logs/input/current/changedBibcodes.txt. Changes to CitationCapture bibcodes are stored in logs/input/current/changedBibcodes_CC.txt.

This pipeline can send nonbib and metrics protobufs for a given list of
bibcodes.  To update master with the changed bibcodes from a file use the command
```
#Process only Classic Records
python3 run.py PROCESS_FILE logs/input/current/changedBibcodes.txt
#Process Classic and CitationCapture Records
python3 run.py PROCESS_FILE logs/input/current/changedBibcodes.txt --include-CitationCapture-file logs/input/current/changedBibcodes_CC.txt
#Process only CitationCapture Records
python3 run.py PROCESS_FILE logs/input/current/changedBibcodes_CC.txt --only-CitationCapture
```
To initialize master, simply process all of the canonical bibcodes:
```
python3 run.py logs/input/current/bibcodes.list.can --include-CitationCapture logs/input/current/bibcodes_CC.list.can
```

ADSDataPipeline can also process a space separated list of bibcodes using the command
```
#Only Classic Records
python3 PROCESS_BIBCODES --bibcodes BIBCODE1 BIBCODE2 ... BIBCODEN
#Only generated nonbib protobufs for Classic Records
python3 PROCESS_BIBCODES --bibcodes BIBCODE1 BIBCODE2 ... BIBCODEN --no-metrics
#Only CitationCapture Records
python3 PROCESS_BIBCODES --bibcodes BIBCODE1 BIBCODE2 ... BIBCODEN --only-CitationCapture
```

### Notes:

- **Because of the way bibcodes are handled, the pipeline cannot handle mixed groups of Classic and CitationCapture bibcodes specified with the `--bibcodes` flag.**

- **For CitationCapture records, ADSDataPipeline only calculates the metrics protobuf so the `--no-metrics` flag cannot be called with any process that handles CitationCapture records.**
# Memory Caches
Computing metrics requires the entire reference and citation networks
as well a list of all the refereed bibcodes.  The reference and
citation networks are cached in memory into python defaultdicts where
the key is the bibcode and the default value is [].  Refereed status
is cached in a python set of bibcodes.  The cache code reads these
files directly, it does not use the reader.py code.

The `COMPUTE_DIFFS` command produces merged network files that contain both CitationCapture and Classic records. These can be identified by the `.merged` extension.

# Nonbib Processing
Conceptually, the code reads one line from each of the ~30 input
files.  This yields all the nonbib data for the next bibcode.  It is
transformed into a nonbib probobuf and sent to master.  

Some implementation details complicate this picture.  Every bibcode
does not appear in every file so one can't just read the next line
from every file and naively merge.  In some files the data for a
bibcode is spread acroos multiple lines (requiring merging of data).
A few values values are computed (e.g., property) from the data read
in.  Some files contain arrays of data (reads, downloads) for each
bibcode, some hold a couple values, some only one.  Some detail data
is not sent to master (e.g., author list read in but only number of
authors is used). 

# Metrics Processing
If we have initialized the cache, as we read the nonbib data one bibcode at a
time we can also compute the metrics record.  Essensically the same core
metrics code from the old pipeline is used the compute a metrics
record.  It is converted to a metrics protobuf and sent to master.

# Describing And Reading Files  
About 30 files need to be consumed.  As noted above, the different
data files have different customs and quirks.  This complicates
reading all the files.  The
code to deal with the complications in a single reader class, 
NonbibFileReader in adsdata/reader.py.  The goal of the reader is
generate "ready to use" data that needs little further massaging.  It
supports a small "description language" where the idiosyncrasies and
customs of each file are explicitly declared.  

What idiosycrasies and properties are supported?  
As noted above, the various files encode data of different type
(boolean, array, hashtables, etc.).  So for each file we encode the
default value to use for bibcodes that aren't in the file.  We use the
type of the default value to convert the string read from the file.
Some files have a single line for each bibcode and that contains an
list of similar values (e.g., the number of reads per year).  We read
lists of similar data into an array.  In other files, the multiple
values in a single line contains very different values (e.g.,
relevance holds 4 values: boost, citation_count, read_count and
norm_cites).  Data like this is read into a python dict where the
keys are defined in the "description language".
Some data links values are always stored in
arrays of dicts even when there is a single value (for example, url and
title).  To indicate this, the keys in the file description is enclosed in
a list.  

There are
cases where we want to associate some data with all bibcodes in a
file.  For example, all the data links info read from the file
spires/all.links must have a link_type of 'INSPIRE' and a
link_sub_type of NA.  To accomidate these constants each file property
dict can include 'extra_values' that are merged with the data other for
a bibcode.  This 'extra_values' field also holds 
additional elements for the 'property' list.

# Converting Nonbib Data To Protobuf
The nonbib protobuf sent to master contains only a subset and a
summary of the data read in.  There is code in process.py that
converts the full nonbib dict to a nonbib protobuf.  

# Performance
A single thread can send nonbib and metrics protobufs to the master
pipeline faster than workers on master can process them.





