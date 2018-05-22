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
    coll = db.coll
    for i in range(5):
        print(coll.insert({'a'+str(i):i}))

    fs = gridfs.GridFS(db)
    _id = fs.put(b'something wicked this way comes...')
    
    while True:

        # See https://stackoverflow.com/a/44946732/1360263  
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
            for file_name, data in [('1.txt', io.BytesIO(b'1'*10000)), ('2.txt', io.BytesIO(b'222'))]:
                zip_file.writestr(file_name, data.getvalue())
            
        _id = fs.put(zip_buffer.getvalue(), filename='result.zip')
        print('Zip result pushed to db @ '+str(_id))

        time.sleep(1.0)
