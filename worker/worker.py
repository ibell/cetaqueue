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

print('about to connect to db')
client = pymongo.MongoClient('outside',
        username='rooty',
        password='passy')
print('connected to db')

db = client.my_db
queue = db.queue

foot = r"""

ADD worker_entrypoint.sh ./entrypoint.sh
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
try:
    while True:
        time.sleep(0.01)
        job = None
        #
        with client.start_session(causal_consistency=True) as session:
            grid_out = queue.find_one({"status": "waiting"}, no_cursor_timeout=True, session=session)

            if grid_out is not None:
                # Set the flag (atomically) - I own the job now

                queue.update_one({'_id': grid_out['_id']}, {'$set': {'status': 'running'}}, session=session)
                job = grid_out

        if job is not None:
            with tempfile.TemporaryDirectory() as tmpdirname:
                # Get the paths to files where output will be written
                stdout_path = os.path.join(tmpdirname,'mystdout.txt')
                stderr_path = os.path.join(tmpdirname,'mystderr.txt')
                
                try:
                    # Write the Dockerfile from the job spec
                    Dockerfile = job['Dockerfile'] + foot
                    print('Dockerfile\n==========')
                    print(Dockerfile)
                    with open(os.path.join(tmpdirname, "Dockerfile"),'w') as fp:
                        fp.write(Dockerfile)
                    
                    # Grab the docker-compose file for the build
                    shutil.copy2('/docker-compose.yml',tmpdirname)
                    shutil.copy2('/worker_entrypoint.sh',tmpdirname)

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

                    stdout_save = sys.stdout
                    stderr_save = sys.stderr

                    with open(stdout_path,'w') as fp_out:
                        with open(stderr_path,'w') as fp_err:

                            ## tee the output to both file and terminal
                            #sys.stdout = stream_tee(stdout_save, fp_out)
                            #sys.stderr = stream_tee(stderr_save, fp_err)
                            
                            the_volume = os.path.split(tmpdirname)[1]+'_output'
                            
                            cmns = dict(shell=True, cwd=tmpdirname, stdout = sys.stdout, stderr = sys.stderr)

                            # Build and run the job
                            fp_out.write('About to run container...')
                            subprocess.check_call('docker-compose up --build', **cmns)
                            subprocess.check_call('docker-compose down', **cmns)
          
                            # Copy the files out of the volume that was attached to the container
                            # by spinning up another mini-container
                            subprocess.check_call('docker run -v '+the_volume+':/output --name helper busybox true', **cmns)
                            subprocess.check_call('docker cp helper:/output .', **cmns)
                            subprocess.check_call('docker rm helper', **cmns)
                            subprocess.check_call('docker volume rm '+the_volume, **cmns)

                    # Zip up the output folder
                    shutil.make_archive(os.path.join(tmpdirname,'output'),'zip',(os.path.join(tmpdirname,'output/')))

                    # Send the zip back to the db
                    with open(os.path.join(tmpdirname,'output.zip'),'rb') as fp:
                        result_id = fs.put(fp.read(), filename='output.zip', mimetype ='application/zip')

                    stdout = open(stdout_path).read() if os.path.exists(stdout_path) else 'No stdout'
                    stderr = open(stderr_path).read() if os.path.exists(stderr_path) else 'No stderr'

                    queue.update_one({'_id': job['_id']}, {'$set': {
                        'status': 'done', 
                        'result_id': result_id, 
                        'stdout': stdout,
                        'stderr': stderr
                    }})

                except BaseException as BE:
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
