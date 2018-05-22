import pymongo
from pymongo import MongoClient
import gridfs

client = pymongo.MongoClient('localhost:27017',
    username='rooty',
    password='passy')

db = client.my_db
fs = gridfs.GridFS(db)

for grid_out in fs.find({"filename": "result.zip"},
                        no_cursor_timeout=True):
    data = grid_out.read()
    
    with open('zizizizi.zip','wb') as fp:
        fp.write(data)
