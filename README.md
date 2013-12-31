
Amondawa provides a ReST interface for storing and querying time series data.
It is inspired by KairosDB and openTSDB.  It is written to take advantage of
Amazon's AWS services - using dynamoDB as a backend store and packaged to run
atop Elastic Beanstalk.

The project is currently in an experimental phase and its performance has not
been characterized. 

** Features:

  - time series downsampling and aggregation
  - counter (rate) and gauge (sum, min. max, avg) style rollups
  - numeric and non-numeric time series values
  - multiple metric domains (e.g. customers)
  - HMAC authentication and domain level authorization
  - obfuscated (hashed) metric stream tags
  - data aging and expiration

