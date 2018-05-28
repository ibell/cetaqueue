import pymongo
from pymongo import MongoClient
import gridfs
import time

class ResultCollector(object):
    
    
    def __init__(self, client, callback = None):
        print('results collector up')
        db = client.my_db
        fs = gridfs.GridFS(db)
        print(type(fs))
        assert(isinstance(fs,gridfs.GridFS))
        self.callback = callback
        queue = db.queue
        try:
            while True:
                time.sleep(0.1)
                job = None
                # 
                with client.start_session(causal_consistency=True) as session:
                    grid_out = queue.find_one({"status": "waiting"}, no_cursor_timeout=True, session=session)
                    if grid_out is not None:
                        print(str(grid_out), 'gotten')
                    
                        # Set the flag (atomically) - I own the job now
                        queue.update_one({'_id': grid_out['_id']}, {'$set': {'status': 'done'}}, session=session)
                        job = grid_out
                        
                if job is not None:
                
                    fname = str(job['data_id'])+'.zip'
                    with open(fname, 'wb') as fp:
                        fp.write(fs.get(job['data_id']).read())
                    print('got', fname)
                    
                #fs.delete(grid_outdata_id)
                    
        except KeyboardInterrupt:
            print('Stopping...')
    
if __name__=='__main__':

    client = pymongo.MongoClient('mongo',
        username='rooty',
        password='passy')
    
    ResultCollector(client)
