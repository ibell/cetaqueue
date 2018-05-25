import requests
url = 'http://localhost:5000/add_job'
files = {'file': ('data.zip', open('data.zip', 'rb'), 'application/zip')}
Dockerfile = open('simple.Dockerfile').read()
r = requests.post(url, files=files, data= dict(Dockerfile=Dockerfile))
print(r.text)
