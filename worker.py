import pymongo
from pymongo import MongoClient
import gridfs
import time
import io
import zipfile

client = pymongo.MongoClient('localhost',
        username='rooty',
        password='passy')

db = client.my_db
queue = db.queue

try:
    while True:
        time.sleep(2)
        job = None
        # 
        with client.start_session(causal_consistency=True) as session:
            grid_out = queue.find_one({"status": "waiting"}, no_cursor_timeout=True, session=session)

            if grid_out is not None:
                # Set the flag (atomically) - I own the job now
                queue.update_one({'_id': grid_out['_id']}, {'$set': {'status': 'running'}}, session=session)
                job = grid_out

        if job is not None:

            time.sleep(2)

            # Push fake result data
            # See https://stackoverflow.com/a/44946732/1360263  
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for file_name, data in [('1.txt', io.BytesIO(b'1'*10000000)), ('2.txt', io.BytesIO(b'222'))]:
                    zip_file.writestr(file_name, data.getvalue())
            fs = gridfs.GridFS(db)
            result_id = fs.put(zip_buffer.getvalue(), filename='result.zip', mimetype ='application/zip')

            queue.update_one({'_id': job['_id']}, {'$set': {'status': 'done', 'result_id': result_id}})

            print(queue.find_one({'_id': job['_id']}))

except KeyboardInterrupt:
    print('Stopping...')
