import pymongo
from pymongo import MongoClient
import gridfs
import io
import zipfile
import time

if __name__=='__main__':

    # This won't start until the wait is done
    print('Into main')
    client = pymongo.MongoClient('mongo',
                username='rooty',
                password='passy')

    db = client.my_db
    queue = db.queue
    fs = gridfs.GridFS(db)
    
    while True:
        with client.start_session(causal_consistency = True) as session:
            
            # Push in the data required for the job
            # See https://stackoverflow.com/a/44946732/1360263  
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                zip_file.write("simple.py")
            data_id = fs.put(zip_buffer.getvalue(), filename='result.zip', mimetype ='application/zip', session=session)
            
            job_info = {
                'status': 'waiting',
                'Dockerfile': open('simple.Dockerfile','r').read(),
                'data_id': data_id,
                'result_id': None
            }
            job_id = queue.insert_one(job_info, session=session)
            
            print('job pushed to db @ '+str(job_id))

        time.sleep(10.0)
