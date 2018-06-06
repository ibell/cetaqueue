
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

Here is a minimal example Dockerfile:
```
FROM continuumio/miniconda3
COPY simple.py .
CMD python -u simple.py
```
where ``simple.py`` does nothing more than 
``` python
with open("/output/hihih.txt",'w') as fp:
   fp.write('hello')
```
A Python script that will post this job with the ``requests``  library reads like
``` python
import requests, os, zipfile
url = 'http://localhost:5000/add_job'

# Absolute paths to the files, needed if this script is run from
# another working directory
zname = os.path.join(os.path.dirname(__file__),'data.zip')
dname = os.path.join(os.path.dirname(__file__),'simple.Dockerfile')
sname = os.path.join(os.path.dirname(__file__),'simple.py')

# Pack up the simple.py file into a zip file
with zipfile.ZipFile(zname, 'w') as myzip:
    myzip.write(sname, arcname='simple.py')

# Do the POST with requests library
files = {'file': ('data.zip', open(zname, 'rb'), 'application/zip')}
Dockerfile = open(dname).read()
r = requests.post(url, files=files, data= dict(Dockerfile=Dockerfile))
# Print the reponse for debugging purposes
print(r.text)

# Cleanup the generated zip file
if os.path.exists(zname): os.remove(zname)
```
