import requests, os, zipfile, argparse
url = 'http://localhost:5000/add_job'

zname = os.path.join(os.path.dirname(__file__),'data.zip')
dname = os.path.join(os.path.dirname(__file__),'simple.Dockerfile')


if __name__=='__main__':
    
    parser = argparse.ArgumentParser(description='Push some simple jobs')
    parser.add_argument('N', type=int, nargs=1, help='an integer for the accumulator',default=1)
    args = parser.parse_args()

    for _ in range(args.N[0]):
    
        with zipfile.ZipFile(zname, 'w') as myzip:
            myzip.write(os.path.join(os.path.dirname(__file__),'simple.py'), arcname='simple.py')

        files = {'file': ('data.zip', open(zname, 'rb'), 'application/zip')}
        Dockerfile = open(dname).read()
        r = requests.post(url, files=files, data= dict(Dockerfile=Dockerfile))

        if os.path.exists(zname):
            os.remove(zname)
