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
                    with open(os.path.join(tmpdirname, "Dockerfile"),'w') as fp:
                        fp.write(job['Dockerfile'])
                    # Grab the docker-compose file for the build
                    shutil.copy2('/docker-compose.yml',tmpdirname)
                    # Print it out, just for debugging
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
                    
                    # Make the output folder
                    output_path = os.path.join(tmpdirname,'output')
                    os.makedirs(output_path)
                    subprocess.check_call('ls -al', shell=True, cwd=tmpdirname, stdout = sys.stdout, stderr = sys.stderr)
                    
                    with open(stdout_path,'w') as fp_out:
                        with open(stderr_path,'w') as fp_err:
                            
                            ## tee the output to both file and terminal
                            #sys.stdout = stream_tee(stdout_save, fp_out)
                            #sys.stderr = stream_tee(stderr_save, fp_err)

                            # Build and run the job
                            fp_out.write('About to run container...')
                            subprocess.check_call('docker-compose up --build', shell=True, cwd=tmpdirname, stdout = sys.stdout, stderr = sys.stderr)
                            
                    # Zip up the output folder
                    shutil.make_archive(os.path.join(tmpdirname,'output'),'zip',output_path)
                    subprocess.check_call('ls -al', shell=True, cwd=tmpdirname+'/output', stdout = sys.stdout, stderr = sys.stderr)
                    
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
