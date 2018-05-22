import pymongo
from pymongo import MongoClient
import gridfs
import time
import uuid

class ResultCollector(object):
    
    def __init__(self, db, callback = None):
        fs = gridfs.GridFS(db)
        print(type(fs))
        assert(isinstance(fs,gridfs.GridFS))
        self.callback = callback
        try:
            while True:
                for grid_out in fs.find({"filename": "result.zip"}, no_cursor_timeout=True):
                    
                    ## Alert (atomically), that the file is about to be downloaded
                    #db.fs.files.update({'_id': grid_out._id}, {'$set': {'status': 'downloading'}})
                    
                    data = grid_out.read()
                    fname = str(grid_out._id)+'.zip'
                    with open(fname, 'wb') as fp:
                        fp.write(data)
                        
                    print('got', fname)
                    
                    fs.delete(grid_out._id)
                    
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print('Stopping...')
    
if __name__=='__main__':

    client = pymongo.MongoClient('localhost:27017',
        username='rooty',
        password='passy')

    db = client.my_db
    ResultCollector(db)
