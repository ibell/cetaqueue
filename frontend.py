import os
from flask import Flask, redirect, url_for, request, render_template,make_response
from pymongo import MongoClient
from bson.objectid import ObjectId
import gridfs
from werkzeug import secure_filename

app = Flask(__name__)

client = MongoClient('mongo', 27017,
                     username='rooty',
                     password='passy')
db = client.my_db

@app.route('/add_job', methods=['GET', 'POST'])
def add_job():
    if request.method == 'POST':
        file = request.files['file']
        filename = secure_filename(file.filename)
        fs = gridfs.GridFS(db)
        data_id = fs.put(file, mimetype=file.content_type, filename=filename)
        
        job_info = {
            'status': 'waiting',
            'Dockerfile': request.form['Dockerfile'],
            'data_id': data_id,
            'result_id': None
        }
        job_id = db.queue.insert_one(job_info)
        
        print('job pushed to db @ '+str(job_id))
            
        return redirect(url_for('frontend'))
    return '''
    <!DOCTYPE html>
    <html>
    <head>
    <title>Upload new file</title>
    </head>
    <body>
    <h1>Upload new file</h1>
    <form action="" method="post" enctype="multipart/form-data">
    <p>
    <label for="Dockerfile">Dockerfile</label>
    <TEXTAREA name="Dockerfile" rows="20" cols="80">The contents of Dockerfile</TEXTAREA></p>
    <p><label for="file">File</label>
    <input type="file" name="file"></p>
    <p><input type="submit" value="Upload"></p>
    </form>
    </body>
    </html>
    '''
    
@app.route('/')
def frontend():
    return render_template('frontend.html', items=list(db.queue.find()))

@app.route('/remove')
def remove():
    
    # Deleting a job from the queue
    key=request.values.get("_id")
    db.queue.remove({"_id":ObjectId(key)})
    return redirect(url_for('frontend'))

@app.route('/view_stdout')
def view_stdout():
    key = request.values.get("_id")
    job = db.queue.find_one({"_id":ObjectId(key)})
    if job is None:
        return 'None'
    else:
        return job.get('stdout','No stdout').replace('\n','<br>')

@app.route('/view_stderr')
def view_stderr():
    key = request.values.get("_id")
    job = db.queue.find_one({"_id":ObjectId(key)})
    if job is None:
        return 'None'
    else:
        return job.get('stderr','No stderr').replace('\n','<br>')

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

