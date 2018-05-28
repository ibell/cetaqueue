import time
import io
import zipfile
import tempfile
import subprocess
import sys
import os

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
            try:
                with tempfile.TemporaryDirectory() as tmpdirname:
                    
                    # Write the Dockerfile from the job spec
                    with open(os.path.join(tmpdirname, "Dockerfile"),'w') as fp:
                        fp.write(job['Dockerfile'])

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
                        
                    stdout_path = os.path.join(tmpdirname,'mystdout.txt')
                    stderr_path = os.path.join(tmpdirname,'mystderr.txt')
                    with open(stdout_path,'w') as fp_out:
                        with open(stderr_path,'w') as fp_err:

                            # Build the image for the job
                            subprocess.check_call('docker image build -t job .', shell=True, cwd=tmpdirname, stdout = fp_out, stderr = fp_err)
                            
                            # Run the container
                            fp_out.write('About to run container...')
                            subprocess.check_call('docker container run job', shell=True, cwd=tmpdirname, stdout = fp_out, stderr = fp_err)

                    # Push fake result data
                    # See https://stackoverflow.com/a/44946732/1360263  
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                        for file_name, data in [('1.txt', io.BytesIO(b'1'*10000000)), ('2.txt', io.BytesIO(b'222'))]:
                            zip_file.writestr(file_name, data.getvalue())
                    fs = gridfs.GridFS(db)
                    result_id = fs.put(zip_buffer.getvalue(), filename='result.zip', mimetype ='application/zip')
                    
                    stdout = open(stdout_path).read() if os.path.exists(stdout_path) else 'No stdout'
                    stderr = open(stderr_path).read() if os.path.exists(stderr_path) else 'No stderr'

                    queue.update_one({'_id': job['_id']}, {'$set': {
                        'status': 'done', 
                        'result_id': result_id, 
                        'stdout': stdout,
                        'stderr': stderr
                    }})
                
            except BaseException as BE:
                queue.update_one({'_id': job['_id']}, {'$set': {'status': 'failed', 'result_id': None, 'message': str(BE)}})

            print(queue.find_one({'_id': job['_id']}))

except KeyboardInterrupt:
    print('Stopping...')
