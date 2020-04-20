# stare

[![GitHub Actions Status](https://github.com/kratsg/stare/workflows/CI/badge.svg)](https://github.com/kratsg/stare/actions?workflow=CI) [![GitHub Actions Deploy Status](https://github.com/kratsg/stare/workflows/Publish%20Python%20%F0%9F%90%8D%20distributions%20%F0%9F%93%A6%20to%20PyPI%20and%20TestPyPI/badge.svg)](https://github.com/kratsg/stare/actions?workflow=Publish+Python+%F0%9F%90%8D+distributions+%F0%9F%93%A6+to+PyPI+and+TestPyPI)

The python wrapper for the Glance API.

## Environment Variables

See [stare/settings/base.py](src/stare/settings/base.py) for all environment variables that can be set. All environment variables for this package are prefixed with `STARE`. As of now, there are:

* `STARE_USERNAME`: CERN account username
* `STARE_PASSWORD`: CERN account password
* `STARE_AUTH_URL`: authentication server
* `STARE_SITE_URL`: API server
* `STARE_CASSETTE_LIBRARY_DIR`: for tests, where to store recorded requests/responses

## CLI Usage

Use `stare --help` for the various options provided.

## Python Usage

```
import stare
glance = stare.Glance()

# get publication information of a publication
pub_info = glance.publication('HDBS-2018-33')
# get publications for a given activity/reference code (see table below)
pubs = glance.publications(activity_id=26, reference_code='HIGG')
```

## Activity IDs

Activity IDs are currently in a different API project (under SCAB Nominations) which SUSY conveners have access to. For now, this is a partial list to make it easier.

|ID |CODE|NAME                  |
|---|----|----------------------|
|36 |SUSY|SUSY                  |
|37 |BGF |Background forum      |
|38 |CDM |Common Dark Matter    |
|39 |TGSK|3rd generation squarks|
|40 |EW  |EW                    |
|41 |ISG |InclSqGl              |
|42 |RPVL|RPVLL                 |
|43 |RVEW|SUSY Review           |
|199|STPR|Strong production     |
|200|RUN2|Run2 Summaries        |

## SSL

In order to get SSL handshakes working (certificate verification), one needs to make sure we add/trust the CERN Certification Authorities (CA) for both the Root and the Grid CAs. Specifically, we rely on the Root CA to sign/issue the Grid CA. The Grid CA is what's relied on for the SSL chain. To make this happen, we'll need both PEM for each CA combined into a single `CERN_chain.pem` file which is bundled up with this package.

Going to the [CERN CA Files website](https://cafiles.cern.ch/cafiles/) and downloading the CERN Root Certification Authority 2 (DER file) and CERN Grid Certification Authority (PEM file). We can then convert the DER to PEM as follows (for the Root CA):

```
openssl x509 -in CERN_ROOT_CA_2.crt -inform der -outform pem -out CERN_ROOT_CA_2.pem
```

and then combine the two

```
cat CERN_GRID_CA_2.pem CERN_ROOT_CA_2.pem > CERN_chain.pem
```

This can be passed into any python `requests::Session` via `verify='/path/to/CERN_chain.pem'` and SSL verification should work.

[1] [DER vs PEM?](https://support.ssl.com/Knowledgebase/Article/View/19/0/der-vs-crt-vs-cer-vs-pem-certificates-and-how-to-convert-them)


# Reference
* http://bhomnick.net/design-pattern-python-api-client/
* https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/
  * Thanks to @webknjaz [da900a16](https://github.com/kratsg/stare/commit/da900a1669af8b72fe8fbbf1c83d8d95e412af8e)
