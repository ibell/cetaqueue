import datetime
import os
from flask import Flask, redirect, url_for, request, render_template,make_response
from pymongo import MongoClient
from bson.objectid import ObjectId
import gridfs
from werkzeug import secure_filename
from ansi2html import Ansi2HTMLConverter
from tasks import run_Dockerfile
from flask_mail import Message, Mail


app = Flask(__name__)
# To use google, also need to enable less secure apps in google account
app.config.update(
  MAIL_SERVER='smtp.gmail.com',
  MAIL_PORT=465,
  MAIL_USE_SSL=True,
  MAIL_USERNAME='ian.h.bell',
  MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD', None),  # Define as ENV variable in host
  MAIL_DEFAULT_SENDER='ian.h.bell@gmail.com'
)
mail = Mail(app)

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
            'result_id': None,
            'date': datetime.datetime.utcnow()
        }
        
        job_id = str(db.queue.insert_one(job_info).inserted_id)
        
        # Tell celery to run the job
        run_Dockerfile.delay(job_id)

        recipient = request.form.get('email-start', None)
        if recipient is not None:
            msg = Message("Job started", recipients=[recipient], html="Added "+str(job_id) + '@' + str(job_info['date']))
            mail.send(msg)
        
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
    # See https://pypi.org/project/ansi2html/ for colored ansi -> HTML conversions
    key = request.values.get("_id")
    job = db.queue.find_one({"_id":ObjectId(key)})
    if job is None:
        return 'None'
    else:
        contents = job.get('stdout','No stdout')
        return Ansi2HTMLConverter().convert(contents)

@app.route('/view_stderr')
def view_stderr():
    key = request.values.get("_id")
    job = db.queue.find_one({"_id":ObjectId(key)})
    if job is None:
        return 'None'
    else:
        contents = job.get('stderr','No stderr')
        return Ansi2HTMLConverter().convert(contents)

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

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
