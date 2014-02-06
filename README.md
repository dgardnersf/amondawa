##Overview

Amondawa provides a ReST interface for storing and querying time series data. It is inspired by KairosDB
and openTSDB.  It is written to take advantage of Amazon's AWS services - using dynamoDB as a
backend store and packaged to run atop Elastic Beanstalk.  It delegates time series computation to
the Python Pandas library.

The project is currently in an experimental phase and its performance has not been characterized.

##Features

  - time series down-sampling and aggregation
  - counter (rate) and gauge (sum, min. max, avg) style rollups
  - numeric and non-numeric time series values
  - multiple metric domains (e.g. customers)
  - HMAC authentication and domain level authorization
  - obfuscated (hashed) metric stream tags (not yet implemented)
  - data aging and expiration

##Getting started

###Environment

###Setup

1. Optionally set the AMDW_TABLE_SPACE environment variable.  Table spaces allow multiple Amondawa instances to
   co-exist in the same AWS region.  The feature is implemented by prepending a token to table names.  The prefix
   is controlled via the AMDW_TABLE_SPACE environment variable:

> $ export AMDW_TABLE_SPACE=myamdw

   (The remainder of this document will use the default prefix 'amdw'.)

2. Optionally set the AMDW_REGION environment variable.  The Amondawa service uses AWS dynamoDB tables and
   must know which AWS region it is deployed to.  The AMDW_REGION variable controls this and defaults
   to 'us-west-2'.

> $ export AMDW_REGION=us-west-1

3. Amondawa configuration is stored in a table named amdw_config.  The configuration is loaded via the bin/configure
   utility from the command line.  Configuration variables are stored as a Python dictionary which may be edited
   before running the configure utility.

> $ bin/configure config/configuration.py
> ...
> overwrite Amondawa us-west-2 region configuration using above configuration? Y/[N]:
> Y
> Configuration written.

4. Create the Amondawa credentials table.  The bin/ac (ac: access control) utility allows you to create API keys
  which control read/write access to Amondawa data domains.

> $ bin/ac create_table
> configuring amdw_credentials table in region us-west-2
> Create amdw_credentials table in region us-west-2?Y/[N]Y
> waiting for amdw_credentials table to be ACTIVE...
> amdw_credentials table created.

5. Create a client API key.  The API key controls read/write access to metric domains.  Below we add a key
   with read/write access to all domains:

> $ bin/ac --permission *:rw add
> configuring amdw_credentials table in region us-west-2
> WARNING: granting access to '*' will allow access to any domain. Continue?Y/[N]Y
> Add new access key with initial permissions set(['*:w', '*:r'])?Y/[N]Y
> Added access key 29RNPPRR26ILGPQ60WHS

6. Create the Amondawa dynamoDB schema.  The dynamoDB tables required to store data and metadata
   (tag and metric names) are created using the bin/create_schema utility:

> $ bin/create_schema
> Create Amondawa schema in region: >>>> us-west-2 <<<< Y/[N]?
> Y
> Schema created.

### Running

Amondawa may be run locally (for development purposes) or deployed to AWS Elastic Beanstalk.

#### Running locally

The application is run locally by invoking the WSGI entry point on the command line:

> $ ./application.py
> * Running on http://0.0.0.0:5000/
> * Restarting with reloader

#### Deploying to AWS elastic Beanstalk

1. Ensure that the file .ebextensions/environment.config reflects desired region and table space (see 1,2 above for
description of these environment variables).  This file is used to set AMDW_TABLE_SPACE and AMDW_REGION in the
WSGI/ Elastic Beanstalk environment.  It is initially set to match the default values of these variables.


> $ vi .ebextensions/environment.config:
>
> option_settings:
>  - option_name: AMDW_TABLE_SPACE
>    value: amdw
>  - option_name: AMDW_REGION
>    value: us-west-2


2. Create deployment archive (zip file).  The bin/package utility is used to create a zip file of the
application code, requirements.txt (pip dependency manifest) and some required library dependencies:

> bin/package

3. Use the Elastic Beanstalk console to create a new Application. Enter name and description.

> screen1

3. Select Environment Type 'Web Server', Predefined Configuration 'Python' and Environment Type
'Load balancing, autoscaling'.

> screen2

4. Upload the zip file created above.

> screen3

5. Choose a unique environment name e.g. 'amondawa-dev'

> screen4

6. Skip the 'Additional Resources' screen (no selections are required).

> screen5

7. Choose an instance type and key pair.  A key pair is required to access Elastic Beanstalk instance for
debugging purposes.  An email address can be provided to receive notifications of changes to the Elastic
Beanstalk environment.  An instance profile must be provided.  The instance profile should correspond to a role
with full dynamoDB access from the AWS EC2 service (see AWS IAM documentation on creating IAM Roles for EC2).

> screen6

8. Wait for the environment to start.

> screen8

### Schema

Schema related configuration requires a understanding of the schema which, in turn, can best be understood
in terms of a sample query:

> POST /api/v1/domain123/datapoints
>
> {
>   'start_absolute': 1391636098059,      # epoch time milliseconds
>   'end_absolute': 1391636105348,        # epoch time milliseconds
>   'metrics': [{
>       'name': 'bytes_in',
>        'tags': {
>          'name': 'venka',
>          'status': 'protected',
>          'type': 'storage'
>        }
>   }]
> }

The query message allows the client to perform multiple sub-queries simultaneously (the metrics field above is a list),
but for illustration purposes, a single sub-query is shown above.  Here we are querying the bytes_in metric between
the times 1391636098059 and 1391636105348.  The name-value pairs specified in the tags dictionary are used to
filter the list of streams that produce bytes_in data. Streams that do not contain all (3) matching key-value
pairs will not be included in the search result.

The HTTP request URI contains the additional parameter 'domain.'  In this case, the domain contains the value
domain123.  This value can be used to separate metrics into logical groups (e.g. by customer, data center,
project etc.

#### Datapoints schema

The metric values are located in a datapoints table with a dynamoDB hash key composed of

> domain, metric, base_time, tags

Base time is used to segment the data for a metric stream across the dynamoDB datapoints table.  The segment size
(COLUMN_HEIGHT) is configurable (in milliseconds) and is chosen so that queries (on the average) will
balanced across the table.

> base_time = timestamp - timestamp % COLUMN_HEIGHT

The tags component of the hash key is a flattened version of the steams tags e.g.:

> "{'key1':'value1','key2':'value2','key3':'value3'}"

A key for a stream matching the illustrated query might have these components (note the addition of
'key4'):

> domain123, bytes_in, 1391636000000, "{'key1':'value1','key2':'value2','key3':'value3', 'key4': 'value4'}"

The datapoints table's range key is time offset from the base time.  Using the hash key and offset range,
metric values are retrieved.

#### Datapoints Index schema

In order to locate matching stream key-value dictionaries (within the datapoints table hash key), an index
table is used. The hash key for the index table is composed of two fields:

> domain, metric

The range key is:

> base_time, tags

Because range keys are stored in sorted order, this scheme allows the index table to be queried for values
between the starting and ending base times.  The tags on the resultant range keys are then compared to the
incoming query tags.   The matching keys are used to construct hash keys in the datapoints table.

In our example the index hash key would contain:

> domain123, bytes_in

and the range key might contain:

> 1391636000000,  "{'key1':'value1','key2':'value2','key3':'value3', 'key4': 'value4'}"

One observes here that the index is just a re-arrangement of the datapoints hash key which allows efficient
selection of potentially matching tags within the range of the starting and ending base times.


#### Datapoints Blocks

In order to more conveniently manage the older time series data, a limit may be placed on the total history
maintained.  Additionally, the total history may be broken into a number of blocks (separate datapoints and index
tables).  For example we may want to store a year of total history in 12 (30 day) blocks.  Data may only be written
to the youngest block.  Older blocks (tables) have diminished configured write capacity (as they are not written to
and this saves on cost).  Dividing metric data into history blocks will allow batch processing (e.g. down-sampling)
of older data.  A master dynamoDB table is used to maintain references to the tables which store these blocks.


### Configuration


> configuration = {
>  'store_column_height':   5*MIN,        # milliseconds of measurements in a datapoints hashkey
>  'store_history':         1*HR,         # milliseconds of history to store (more will be deleted)
>  'store_history_blocks':  3,            # history will be divided into this many archive blocks
>  'mt_readers':            20,           # number of datapoints query threads
>  'mt_writers':            5,            # number of datapoints writer threads
>  'mt_write_delay':        2,            # number of seconds to wait for more datapoints before flushing
>                                         #   datapoints write buffer
>  'cache_datapoints':      400,          # datapoints LRU cache size
>  'cache_query_index_key': 400,          # index_key (query) LRU cache size
>  'cache_write_index_key': 400,          # index_key (write) LRU cache size
>  'tp_write_datapoints':   160,          # dynamo datapoints table write throughput
>  'tp_read_datapoints':    80,           # dynamo datapoints table read throughput
>  'tp_write_index_key':    160,          # dynamo index key table write throughput
>  'tp_read_index_key':     80,           # dynamo index key table read throughput
>  'mx_create_next_min':    4,            # cutoff time in minutes remaining for creating next datapoints tables
>  'mx_create_next_pct':    15,           # cutoff time in percent remaining for creating next datapoints tables
>  'mx_turndown_min':       2,            # cutoff time in minutes expired for turning down write throughput
>  'mx_turndown_pct':       20,           # cutoff time in percent expired for turning down write throughput
> }



