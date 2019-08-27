# stare

The python wrapper for the Glance API.

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
