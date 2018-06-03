
## Server

Install docker + docker-compose, and then:
```
docker-compose up --build -d
```
and go to http://localhost:5000 to access the build queue.

## Worker

Enter ``worker`` folder, then
```
docker-compose up --build -d
```

You can connect multiple workers if you like

## Push job

The spec for the job is defined by the Dockerfile. Important notes:

* The ``CMD`` is the definition of the job to be done in the Dockerfile
* All files should be pushed into the Docker image that will be needed for the build
* All commands will be run by a user that has r/w access to the ``/output`` folder
* The Dockerfile + contents of .zip file should allow for a runnable Docker image

Here is a minimal example:
```
FROM continuumio/miniconda3
COPY simple.py .
CMD python -u simple.py
```
where simple.py does nothing more than 
```
import os
with open("/output/hihihihihi.txt",'w') as fp:
   fp.write('hello')
```
A script that will post this job with the ``requests``  library reads like
```
import requests, os, zipfile
url = 'http://localhost:5000/add_job'

with zipfile.ZipFile(os.path.join(os.path.dirname(__file__),'data.zip'), 'w') as myzip:
    myzip.write(os.path.join(os.path.dirname(__file__),'simple.py'), arcname='simple.py')

zname = os.path.join(os.path.dirname(__file__),'data.zip')
dname = os.path.join(os.path.dirname(__file__),'simple.Dockerfile')

files = {'file': ('data.zip', open(zname, 'rb'), 'application/zip')}
Dockerfile = open(dname).read()
r = requests.post(url, files=files, data= dict(Dockerfile=Dockerfile))
print(r.text)

if os.path.exists(zname):
    os.remove(zname)
```
