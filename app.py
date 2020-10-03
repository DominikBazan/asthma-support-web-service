from flask import Flask, render_template, url_for, request, redirect, session, jsonify
from flask_mysqldb import MySQL, MySQLdb
from databaseConnection import getCredentials
from encryption import *
import json
from db_operations import *
import base64

import numpy as np
import pandas as pd
from sklearn import tree

app = Flask(__name__)

myHost, myUser, myPasswd, myDatabase, port = getCredentials()

app.config['MYSQL_HOST'] = myHost
app.config['MYSQL_USER'] = myUser
app.config['MYSQL_PASSWORD'] = myPasswd
app.config['MYSQL_DB'] = myDatabase
app.config['MYSQL_PORT'] = port
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

def changeDecision(vector):
    for i in range(0, len(vector)):
        if vector[i] >= 1:
            vector[i] = 1
        else:
            if vector[i] <= -1:
                vector[i] = -1
            else:
                vector[i] = 0

dataset_train = pd.read_csv('./classifierData/TEST.csv')

noColumn = dataset_train.shape[1]

features_train = dataset_train.iloc[:, :noColumn - 2]
labels_train = dataset_train.iloc[:, [noColumn - 1]]
labels_train = np.ravel(labels_train)
changeDecision(labels_train)

model = tree.DecisionTreeClassifier()

model.fit(features_train, labels_train)

def getWeather():
    return getAndSaveWeather()

scheduler = BackgroundScheduler()
job = scheduler.add_job(getWeather, 'interval', hours=3)
scheduler.start()

getWeather()

@app.route('/')
def index():
    return "AstmaSupport - index page 2."

@app.route('/weatherUpdate')
def weatherUpdate():
    getWeather()
    return "Weather update done.\n"

def getFieldFromJSON(request, field):
    return json.loads(json.dumps(request.get_json()))[field]

@app.route('/registerRequest', methods = ['POST'])
def register():
    email = decrypt(getFieldFromJSON(request, "email"))
    password = decrypt(getFieldFromJSON(request, "password"))
    if emailAlreadyExists(mysql, email):
        return json.dumps([{"text":encrypt("Taken")}])
    enkryptedPassword = base64.b64encode(password.encode("utf-8"))
    if newUser(mysql, email, password):
        return json.dumps([{"text":encrypt("Success")}])
    else:
        return json.dumps([{"text":encrypt("Failure")}])

@app.route('/passwordHash', methods = ['POST'])
def getHash():
    email = decrypt(getFieldFromJSON(request, "text"))
    userHash = getUserHashByEmail(mysql, email)
    if userHash == False:
        return json.dumps([{"text":encrypt("")}])
    else:
        return json.dumps([{"text":encrypt(userHash)}])

@app.route('/getUserData', methods = ['POST'])
def getUserData():
    return getUData(mysql, decrypt(getFieldFromJSON(request, "text")))

@app.route('/updateUserData', methods = ['POST'])
def updateUserData():
    message = updateUser(mysql,
        decrypt(getFieldFromJSON(request, "name")),
        decrypt(getFieldFromJSON(request, "surname")),
        decrypt(getFieldFromJSON(request, "sex")),
        decrypt(getFieldFromJSON(request, "email")),
        decrypt(getFieldFromJSON(request, "birth")),
        decrypt(getFieldFromJSON(request, "height")),
        decrypt(getFieldFromJSON(request, "weight")),
        decrypt(getFieldFromJSON(request, "disease_start"))
    )
    return json.dumps([{"text":encrypt(message)}])

@app.route('/changePassword', methods = ['POST'])
def changePassword():
    email = decrypt(getFieldFromJSON(request, "email"))
    password = decrypt(getFieldFromJSON(request, "password"))
    return changeUserPassword(mysql, email, password)

@app.route('/addTestResult', methods = ['POST'])
def addTestResult():
    email = decrypt(getFieldFromJSON(request, "email"))
    points = decrypt(getFieldFromJSON(request, "points"))
    date = decrypt(getFieldFromJSON(request, "date"))
    return saveTestResult(mysql, email, points, date)

@app.route('/getStatistics', methods = ['POST'])
def getStatistics():
    email = decrypt(getFieldFromJSON(request, "text"))
    return getUserStatistics(mysql, email)
    
@app.route('/changeTodaysMedicineTakenState', methods = ['POST'])
def changeMedicineTakenState():
    email = decrypt(getFieldFromJSON(request, "text"))
    return changeMedTakenState(mysql, email)

@app.route('/getPrediction', methods = ['POST'])
def getPrediction():
    email = decrypt(getFieldFromJSON(request, "text"))
    return getTodaysPrediction(mysql, model, email)

@app.route('/getColorInfo', methods = ['POST'])
def getColorInfo():
    email = decrypt(getFieldFromJSON(request, "text"))
    return getColorInfoByEmail(mysql, email)

@app.route('/addFirstMedicineEventAndTest', methods = ['POST'])
def addFirstMedicineEvent():
    email = decrypt(getFieldFromJSON(request, "text"))
    return addFirstMedicineEventAndTestByEmail(mysql, email)

@app.route('/addMissingMedicineEventsAndTests', methods = ['POST'])
def addMissingMedicineEventsAndTests():
    email = decrypt(getFieldFromJSON(request, "text"))
    return addMissingMedicineEventsAndTestsByEmail(mysql, email)

@app.route('/getMedicines', methods = ['POST'])
def getMedicines():
    email = decrypt(getFieldFromJSON(request, "text"))
    return getMedicinesByEmail(mysql, email)

@app.route('/addNewMedicine', methods = ['POST'])
def addNewMedicine():
    medicineName = decrypt(getFieldFromJSON(request, "medicineName"))
    email = decrypt(getFieldFromJSON(request, "email"))
    return addNewMedicineByEmail(mysql, medicineName, email)

@app.route('/deleteMedicinesUsed', methods = ['POST'])
def deleteMedicinesUsed():
    email = decrypt(getFieldFromJSON(request, "email"))
    medicinesToDelete = getFieldFromJSON(request, "medicinesToDelete")
    return deleteMedicinesUsedByEmail(mysql, medicinesToDelete, email)

@app.route('/changeDosage', methods = ['POST'])
def changeDosage():
    email = decrypt(getFieldFromJSON(request, "email"))
    mode = decrypt(getFieldFromJSON(request, "mode"))
    return changeDosageByEmailAndMode(mysql, email, mode)

@app.route('/getUsersAllergies', methods = ['POST'])
def getUsersAllergies():
    email = decrypt(getFieldFromJSON(request, "text"))
    return getUsersAllergiesByEmail(mysql, email)

@app.route('/addNewAllergy', methods = ['POST'])
def addNewAllergy():
    email = decrypt(getFieldFromJSON(request, "email"))
    newAllergy = decrypt(getFieldFromJSON(request, "allergyName"))
    return addNewAllergyByEmail(mysql, email, newAllergy)

@app.route('/deleteAllergiesUsed', methods = ['POST'])
def deleteAllergiesUsed():
    email = decrypt(getFieldFromJSON(request, "email"))
    allergiesToDelete = getFieldFromJSON(request, "allergiesToDelete")
    return deleteAllergiesUsedByEmail(mysql, email, allergiesToDelete)

@app.route('/getAllAsthmaFactors', methods = ['POST'])
def getAllAsthmaFactors():
    # May be usefull in the future
    # email = decrypt(getFieldFromJSON(request, "text"))
    return getAllAsthmaFactorsNames(mysql)


if __name__ == "__main__":
    # app.run()
    app.run(debug=True)
  