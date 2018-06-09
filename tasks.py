import time
import io
import zipfile
import tempfile
import subprocess
import sys
import os
import shutil

import pymongo
from pymongo import MongoClient
import gridfs
from bson import ObjectId

from celery import Celery
app = Celery('tasks', broker='pyamqp://rooty:passy@rabbitmq//')

print('about to connect to db')
client = pymongo.MongoClient('mongo',
        username='rooty',
        password='passy')
print('connected to db')

db = client.my_db
queue = db.queue

foot = r"""

ADD worker_entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Add user baleen and put it into its own group and also the docker group so
# that it can launch child docker instances
RUN groupadd -g 628 baleen && \
    useradd -r -u 628 -g baleen baleen 

ENV GOSU_VERSION 1.10
RUN set -ex; \
	\
	fetchDeps=' \
		ca-certificates \
		wget \
	'; \
	apt-get update; \
	apt-get install -y --no-install-recommends $fetchDeps; \
	rm -rf /var/lib/apt/lists/*; \
	\
	dpkgArch="$(dpkg --print-architecture | awk -F- '{ print $NF }')"; \
	wget -O /usr/local/bin/gosu "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$dpkgArch"; \
	wget -O /usr/local/bin/gosu.asc "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$dpkgArch.asc"; \
	\
	chmod +x /usr/local/bin/gosu; \
# verify that the binary works
	gosu nobody true; \
	\
	apt-get purge -y --auto-remove $fetchDeps

ENTRYPOINT ["/entrypoint.sh"]
"""

class StdErrTeer(object):
    def __init__(self, file_stream):
        self.old_stderr = sys.stderr
        self.file_obj = file_stream
        # Point the stream to me
        sys.stderr = self
    
    def __enter__(self):
        pass
    
    def __exit__(self, type, value, traceback):
        self.file_obj.close()
        sys.stderr = self.old_stderr
    
    def write(self, data):
        self.file_obj.write(data)
        self.file_obj.flush()
        self.old_stderr.write(data)
        self.old_stderr.flush()
        
    def fileno(self):
        return self.file_obj.fileno()
        
    def flush(self):
        pass
    
class StdOutTeer(object):
    def __init__(self, file_stream):
        self.old_stdout = sys.stdout
        self.file_obj = file_stream
        # Point the stream to me
        sys.stdout = self
    
    def __enter__(self):
        pass
    
    def __exit__(self, type, value, traceback):
        self.file_obj.close()
        sys.stdout = self.old_stdout
    
    def write(self, data):
        self.file_obj.write(data)
        self.file_obj.flush()
        self.old_stdout.write(data)
        self.old_stdout.flush()
        
    def fileno(self):
        return self.file_obj.fileno()
        
    def flush(self):
        pass
    
def subprocess_redirected(command, path, **kwargs):
    """
    Run a subprocess, piping all output to terminal via parallel stdout and stderr pipes,
    as well as to temporary files.
    
    In a caller function, the stdout and stderr can be redirected to file and the 
    normal location.  See the Redirector class
    """
    
    callback = kwargs.pop('callback', None)
    delay_s = kwargs.pop('delay_s', 1.0)
    
    path_out = os.path.join(path, 'buff_stdout')
    path_err = os.path.join(path, 'buff_stderr')
    
    with open(path_out,'w') as write_out, \
         open(path_out,'r',1) as read_out, \
         open(path_err,'w') as write_err, \
         open(path_err,'r',1) as read_err:
             
        kwargs['stdout'] = write_out
        kwargs['stderr'] = write_err

        # Start the process, redirecting to the file buffers
        process = subprocess.Popen(command, **kwargs)
        while process.poll() is None: # poll() value of None indicates still working
            sys.stdout.write(read_out.read())
            sys.stderr.write(read_err.read())
            time.sleep(0.05)
            if callback is not None:
                callback()
                
        # Read the remaining
        sys.stdout.write(read_out.read())
        sys.stderr.write(read_err.read())
        
        # Check the return code
        rc = process.returncode
        if rc != 0:
            raise ValueError("Process returned with error code "+rc)
        
    for fname in path_err, path_out:
        if os.path.exists(fname):
            os.remove(fname)

@app.task
def add(x,y):
    return x+y

@app.task
def run_Dockerfile(job_id):
    try:
        job = queue.find_one({'_id': ObjectId(job_id)})

        if job is not None:
            with tempfile.TemporaryDirectory() as tmpdirname:
                # Get the paths to files where output will be written
                stdout_path = os.path.join(tmpdirname,'mystdout.txt')
                stderr_path = os.path.join(tmpdirname,'mystderr.txt')
                
                try:
                    with StdOutTeer(open(stdout_path,'w')) as redir_out, \
                        StdErrTeer(open(stderr_path,'w')) as redir_err:
                            
                        # Write the Dockerfile from the job spec
                        Dockerfile = job['Dockerfile'] + foot
                        print('Dockerfile\n==========')
                        print(Dockerfile)
                        with open(os.path.join(tmpdirname, "Dockerfile"),'w') as fp:
                            fp.write(Dockerfile)
                        
                        # Grab the docker-compose file for the build
                        shutil.copy2('/docker-compose.yml',tmpdirname)
                        shutil.copy2('/worker_entrypoint.sh',tmpdirname)

                        subprocess_redirected('ls -al', tmpdirname, shell=True, cwd=tmpdirname)


                        # Print it out, just for debugging
                        print('docker-compose\n==========')
                        print(open('docker-compose.yml').read())

                        # Get the input data and write to file
                        fs = gridfs.GridFS(db)
                        file_ = fs.get(ObjectId(job['data_id']))  
                        fname = os.path.join(tmpdirname, file_.filename)
                        with open(fname, 'wb') as fp:
                            fp.write(file_.read())

                        # Unpack the data to the root of the temporary folder
                        with zipfile.ZipFile(fname) as myzip:
                            myzip.printdir()
                            myzip.extractall(path=tmpdirname)

                        # Build and run the job
                        print('About to run container...')
                        
                        # Copy the files out of the volume that was attached to the container
                        # by spinning up another mini-container
                        # Idea from: https://stackoverflow.com/a/37469637/1360263
                        
                        the_volume = os.path.split(tmpdirname)[1] + '_output'
                        helper = 'helper_' + os.path.split(tmpdirname)[1]
                        for command in ['docker-compose up --build',
                                        'docker-compose down',
                                        'docker run -v '+the_volume+':/output --name '+helper+' busybox true',
                                        'docker cp '+helper+':/output .',
                                        'docker rm '+helper,
                                        'docker volume rm '+the_volume
                                        ]:
                            subprocess_redirected(command, tmpdirname, shell=True, cwd=tmpdirname)

                        # Zip up the output folder
                        shutil.make_archive(os.path.join(tmpdirname,'output'),'zip',(os.path.join(tmpdirname,'output/job')))

                        # Send the zip back to the db
                        with open(os.path.join(tmpdirname,'output.zip'),'rb') as fp:
                            result_id = fs.put(fp.read(), filename='output.zip', mimetype ='application/zip')
                            
                        print('ready to push')

                        stdout = open(stdout_path).read() if os.path.exists(stdout_path) else 'No stdout'
                        stderr = open(stderr_path).read() if os.path.exists(stderr_path) else 'No stderr'
                        print('stdout(len:{0:d}): {1:s}'.format(len(stdout),stdout))
                        print('stderr(len:{0:d}): {1:s}'.format(len(stderr),stderr))
                        
                        queue.update_one({'_id': job['_id']}, {'$set': {
                            'status': 'done', 
                            'result_id': result_id, 
                            'stdout': stdout,
                            'stderr': stderr
                        }})

                except BaseException as BE:
                    
                    print('ERROR')
                    stdout = open(stdout_path).read() if os.path.exists(stdout_path) else 'No stdout'
                    stderr = open(stderr_path).read() if os.path.exists(stderr_path) else 'No stderr'
                    print(str(BE))
                    queue.update_one({'_id': job['_id']}, {'$set': {
                        'status': 'failed', 
                        'result_id': None, 
                        'message': str(BE),
                        'stdout': stdout,
                        'stderr': stderr
                    }})

            print(queue.find_one({'_id': job['_id']}))

    except KeyboardInterrupt:
        print('Stopping...')
        
    print('Goodbye...')
