import pymongo
from pymongo import MongoClient
import gridfs

if __name__=='__main__':
    # This won't start until the wait works
    print('Into main')
    client = pymongo.MongoClient('mongo'
                username='rooty',
                password='passy')

    db = client.my_db
    coll = db.coll
    for i in range(100):
        print(coll.insert({'a'+str(i):i}))

    fs = gridfs.GridFS(db)
    _id = fs.put(b'something wicked this way comes...')
    print(fs.get(_id).read())
