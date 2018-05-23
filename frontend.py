import os
from flask import Flask, redirect, url_for, request, render_template,make_response
from pymongo import MongoClient
from bson.objectid import ObjectId
import gridfs

app = Flask(__name__)

client = MongoClient('mongo', 27017,
                     username='rooty',
                     password='passy')
db = client.my_db

@app.route('/')
def frontend():
    return render_template('frontend.html', items=list(db.queue.find()))

@app.route('/remove')
def remove():
    
    # Deleting a job from the queue
    key=request.values.get("_id")
    db.queue.remove({"_id":ObjectId(key)})
    return redirect("/")

@app.route('/downloadfile')
def downloadfile():
    key = request.values.get("_id")
    
    fs = gridfs.GridFS(db)
    file_ = fs.get(ObjectId(key))
    print(file_)
    
    response = make_response(file_.read())
    cd = 'attachment; filename='+str(key)+'.zip'
    response.headers['Content-Disposition'] = cd 
    response.mimetype = file_.mimetype
    return response

@app.route('/new', methods=['POST'])
def new():

    item_doc = {
        'name': request.form['name'],
        'Dockerfile': request.form['Dockerfile'],
        'meta': request.form['meta'],
        'status': 'waiting'
    }
    db.queue.insert_one(item_doc)

    return redirect(url_for('frontend'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)

