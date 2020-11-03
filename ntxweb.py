import os
from flask import Flask, render_template, session, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_moment import Moment
#from flask_wtf import FlaskForm
#from wtforms import StringField, SubmitField
#from wtforms.validators import DataRequired

from flask_socketio import SocketIO, emit, disconnect
from threading import Lock
#from flask_sqlalchemy import SQLAlchemy
#from flask_migrate import Migrate
import random

try:
    import ntxpi
    aquarium = ntxpi.aquarium()
except ModuleNotFoundError:
    print('failure to import & load aquarium')
#    aquarium = ntxpisim.aquariumsim()
    

basedir = os.path.abspath(os.path.dirname(__file__))

async_mode = None
app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'
socketio = SocketIO(app, async_mode=async_mode, cors_allowed_origins="*")
thread = None
thread_lock = Lock()

bootstrap = Bootstrap(app)
moment = Moment(app)



# runs every x seconds and updates values on WEBUI
aqdict = {
    'temp': aquarium.get_temp(),
    'drv0' : True if random.randrange(0,2) == 0 else False,
    'drv1' : True if random.randrange(0,2) == 0 else False,
    'drv0Spd' : 0,
    'drv1Spd' : 0,
    'AqFlag' : random.randrange(0,2),
    'CleanFlag' : random.randrange(0,2),
    'WasteFlag' : random.randrange(0,2),
    'SpareFlag' : random.randrange(0,2),
    'exchangeState' : False
    }

aqConfig = {
    'tempmax' : 40,
    'tempmin' : 10
}

def aqState():
    while True:
        socketio.sleep(1)
        aqdict['temp'] = aquarium.get_temp()
        aqdict['CleanFlag'] = random.randrange(0,2)
        aqdict['AqFlag'] = random.randrange(0,2)
        aqdict['drv0'] = True if random.randrange(0,2) == 0 else False
        if aqdict['exchangeState'] == True:
            aquarium.drv8825(500, 0, 5000)
            aqdict['exchangeState'] = False
        #pinstatus = aquarium.pinsIn
        socketio.emit('aqStatemsg', 
            {'data' : aqdict}, 
            namespace='/aqState')

#@app.shell_context_processor
#def make_shell_context():
#	return dict(db=db, User=User, Role=Role)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.route('/')
def index():
    return render_template('index.html')
'''
@app.route('/analytics')
def analytics():
    return render_template('analytics.html')
'''
@socketio.on('connect', namespace='/aqState')
def aqState_monitor():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(aqState)

@socketio.on('disconnect', namespace='/aqState')
def test_disconnect():
    print('Client disconnected')
    #uncompleted

@socketio.on('my_event', namespace='/aqState')
def test_message(message):
    #sanity check for what is received
    for x in message['data']:
        print('Data received: %s is %s' % (x, message['data'][x])) # sanity check for 
        aqdict[x] = message['data'][x]
        print('Dictionary updated: %s is %s' % (x, aqdict[x])) # sanity check for 
    socketio.emit('aqStatemsg', {'data' : aqdict}, namespace='/aqState')
    #aqConfig['tempmax'] = message['data']
    #print(aqConfig['tempmax'])

@socketio.on('button_event', namespace='/aqState')
def button_message(message):
    print(message['data']['exchange'])
    #aqConfig['tempmax'] = message['data']
    #print(aqConfig['tempmax'])

if __name__ == '__main__': 
  socketio.run(app, host='0.0.0.0',debug=True, use_reloader=False) 