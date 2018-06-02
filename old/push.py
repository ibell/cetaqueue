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
