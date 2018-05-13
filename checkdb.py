import pymongo
from pymongo import MongoClient
import gridfs

def client_if_possible(*args,**kwargs):
    try:
        client = pymongo.MongoClient(*args, **kwargs,
                                    serverSelectionTimeoutMS=0.01)
        client.server_info() # force connection on a request as the
                            # connect=True parameter of MongoClient seems
                            # to be useless here
        return client
    except pymongo.errors.ServerSelectionTimeoutError as err:
        # do whatever you need
        print(err)

if __name__=='__main__':
    print('Into main')
    client = client_if_possible('mongo',
                username='rooty',
                password='passy')
    db = client.my_db
    coll = db.coll
    for i in range(100):
        print(coll.insert({'a'+str(i):i}))

    fs = gridfs.GridFS(db)
    _id = fs.put(b'something wicked this way comes...')
    print(fs.get(_id).read())
