import json
import traceback
from datetime import date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import mysql.connector
from databaseConnection import getCredentials
from encryption import *

import numpy as np
import pandas as pd
from sklearn import tree

import requests

from xml.etree import ElementTree

def getUserByEmail(mysql, email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE email=%s",(email,))
    user = cur.fetchone()
    cur.close()
    return user

def getUserHashByEmail(mysql, email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT password FROM users WHERE email=%s",(email,))
    rows = cur.fetchall()
    if int(cur.rowcount) == 0:
        result = False
    else:
        result = rows[0]['password']
    cur.close()
    return result

def emailAlreadyExists(mysql, email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) AS num FROM users WHERE email=%s",(email,))
    amount = cur.fetchone()
    cur.close()
    if amount['num'] == 0:
        return False
    else:
        return True

def newUser(mysql, email, password):
    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (name, surname, sex, email, birth, height, weight, disease_start, password) VALUES (NULL, NULL, 'N', %s, NULL, NULL, NULL, NULL, %s)",(email,password,))
        mysql.connection.commit()
        cur.close()
        return True
    except:
        return False

def getUData(mysql, email):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT name, surname, sex, birth, height, weight, disease_start FROM users WHERE email=%s",(email,))
        data = cur.fetchone()

        birthField = data['birth']
        if birthField:
            birth = birthField.strftime("%Y-%m-%d")
        else:
            birth = None

        diseaseStartField = data['disease_start']
        if diseaseStartField:
            disease_start = diseaseStartField.strftime("%Y-%m-%d")
        else:
            disease_start = None

        data = [data['name'], data['surname'], data['sex'], birth, data['height'], data['weight'], disease_start]
        data = [{"text":encrypt(ob)} for ob in data]
        cur.close()
        return json.dumps(data)
    except:
        return json.dumps([{"text":encrypt("ERROR")}])

def updateUser(mysql, name, surname, sex, email, birth, height, weight, disease_start):
    try:
        cur = mysql.connection.cursor()
        if (name != ""):
            cur.execute("UPDATE users SET name=%s WHERE email=%s", (name, email),)
        if (surname != ""):
            cur.execute("UPDATE users SET surname=%s WHERE email=%s", (surname, email),)
        if (sex != ""):
            cur.execute("UPDATE users SET sex=%s WHERE email=%s", (sex, email),)
        if (birth != ""):
            cur.execute("UPDATE users SET birth=%s WHERE email=%s", (birth, email),)
        if (height != ""):
            cur.execute("UPDATE users SET height=%s WHERE email=%s", (height, email),)
        if (weight != ""):
            cur.execute("UPDATE users SET weight=%s WHERE email=%s", (weight, email),)
        if (disease_start != ""):
            cur.execute("UPDATE users SET disease_start=%s WHERE email=%s", (disease_start, email),)
        mysql.connection.commit()
        cur.close()
        return "Zaktualizowano informacje"
    except:
        return "Wystąpił błąd.\nSpróbuj ponownie."

def changeUserPassword(mysql, email, password):
    try:
        cur = mysql.connection.cursor()
        cur.execute("UPDATE users SET password=%s WHERE email=%s", (password, email),)
        mysql.connection.commit()
        cur.close()
    except:
        return json.dumps([{"text":encrypt("Error")}])
    return json.dumps([{"text":encrypt("Zmieniono")}])
    
def saveTestResult(mysql, email, points, date):
    try:
        idUser = getIdUserByEmail(mysql, email)
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM controlTests WHERE id_user = %s AND date = %s", (idUser, date,))
        cur.execute("INSERT INTO controlTests (id_user, date, value) VALUES (%s, %s, %s)", (idUser, date, int(points)),)
        mysql.connection.commit()
        cur.close()
        return json.dumps([{"text":encrypt("Zapisano wynik")}])
    except:
        return json.dumps([{"text":encrypt("Error")}])

def getUserStatistics(mysql, email):
    try:
        cur = mysql.connection.cursor()
        id_user = getIdUserByEmail(mysql, email)
        cur.execute("SELECT ct.date AS date, ct.value AS value, me.implemented AS implemented, w.rain AS rain, w.wind AS wind, w.temperature AS temperature FROM controlTests ct JOIN medicineEvents me ON (ct.id_user = me.id_user) JOIN weather w ON (ct.date = w.date) WHERE ct.date = me.date AND ct.id_user = %s ORDER BY date DESC",(id_user,))
        list = cur.fetchall()
        cur.close()
        data = [{"date":encrypt(el['date'].strftime("%Y-%m-%d")),"value":encrypt(el['value']),"implemented":encrypt(el['implemented']),"rain":encrypt(el['rain']),"wind":encrypt(el['wind']),"temperature":encrypt(el['temperature']),"dusting":encrypt(getDustingInfo(mysql, el['date'], email))} for el in list]
        return json.dumps(data)
    except:
        return json.dumps([{"date":encrypt("ERROR")}])

def getDustingInfo(mysql, date, email):
    dustingInfo = ""
    cur = mysql.connection.cursor()
    season36Str = getSeason36(date)
    cur.execute("SELECT af.name AS name, af." + season36Str[0] + " AS dusting FROM users u JOIN allergies a ON (u.id_user = a.id_user) JOIN asthmaFactors af ON (a.name = af.name) WHERE u.email = %s", (email,))
    dustingInfos = cur.fetchall()
    cur.close()
    for row in dustingInfos:
        dustingInfo += row['name'] + " " + str(row['dusting']) + "\n"
    return dustingInfo[:-1]

def getSeason36(today):
    day = today.day
    month = today.month
    if day > 20:
        partOfMonth123 = "3"
    elif day > 10:
        partOfMonth123 = "2"
    else:
        partOfMonth123 = "1"
    monthNames = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
    return monthNames[month-1] + partOfMonth123

def changeMedTakenState(mysql, email):
    try:
        cur = mysql.connection.cursor()
        todayStr = date.today().strftime("%Y-%m-%d")
        cur.execute("SELECT me.implemented AS implemented, u.id_user AS id_user FROM medicineEvents me JOIN users u ON (me.id_user = u.id_user) WHERE u.email=%s AND me.date=%s", (email, todayStr,))
        implementedRow = cur.fetchone()
        if not implementedRow:
            return json.dumps({"text":"NO ME FOR TODAY"})
        implementedBefore = implementedRow['implemented']
        idUser = implementedRow['id_user']
        if implementedBefore == 0:
            cur.execute("UPDATE medicineEvents SET implemented = TRUE WHERE id_user=%s AND date=%s", (idUser, todayStr),)
            returnText = "YES"
        else:
            cur.execute("UPDATE medicineEvents SET implemented = FALSE WHERE id_user=%s AND date=%s", (idUser, todayStr),)
            returnText = "NO"
        mysql.connection.commit()
        cur.close()
        return json.dumps({"text":encrypt(returnText)})
    except:
        return json.dumps({"text":encrypt("ERROR")})

def getTodaysPrediction(mysql, model, email):
    try:
        tomorowDate = date.today() + timedelta(days=1)
        tomorrowStr = tomorowDate.strftime("%Y-%m-%d")
        avr14, avr5, WNeg1 = getWResults(mysql, tomorrowStr, email)
        if WNeg1 == 0:
            prediction = "Wypełnij ankietę, aby otrzymać pierwszą prognozę Twojego stanu"
        else:
            season, month = getSeason36(tomorowDate)
            max_dusting = getMaxDusting(mysql, season, email)
            if max_dusting == -1 or max_dusting == None:
                prediction = "Wprowadź informacje o tym, na co jesteś uczulony, aby otrzymać prognozę Twojego stanu"
            else:
                rain, wind, temperature = getTodaysWeatherForcast(mysql, tomorrowStr)
                last6dosages = getLast6dosages(mysql, tomorrowStr, email)
                negative_med_change, positive_med_change = getDosagesChanges(last6dosages)
                row = [avr14,avr5,WNeg1,negative_med_change,positive_med_change,max_dusting,rain,wind,temperature,month]
                row_list = [row]
                print(row)
                test_data = pd.DataFrame(row_list, columns=["avr14","avr5","W-1","negative_med_change","positive_med_change","max_dusting","rain","wind","temperature","month36"])
                labels_predicted = model.predict(test_data)
                prediction = int(labels_predicted[0])
                if prediction == 1:
                    prediction = "Wkrótce nastąpi polepszenie"
                elif prediction == 0:
                    prediction = "Obecny stan się utrzyma"
                elif prediction == -1:
                    prediction = "Wkrótce nastąpi pogorszenie"
        return json.dumps({"text":encrypt(prediction)})
    except:
        return json.dumps({"text":encrypt(".")})

def getTodaysWeatherForcast(mysql, date):
    cur = mysql.connection.cursor()
    cur.execute("SELECT rain, wind, temperature From weather WHERE date = %s", (date,))
    weatherRow = cur.fetchone()
    return weatherRow['rain'], weatherRow['wind'], weatherRow['temperature']

def getSeason36(today):
    day = today.day
    month = today.month
    
    if day > 20:
        partOfMonth123 = "3"
    elif day > 10:
        partOfMonth123 = "2"
    else:
        partOfMonth123 = "1"
    
    monthNames = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]

    return monthNames[month-1] + partOfMonth123, month

def getMaxDusting(mysql, season, email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT MAX(af."+season+") AS maxDusting FROM asthmaFactors af JOIN allergies a ON (af.name = a.name) JOIN users u ON (u.id_user = a.id_user) WHERE u.email = %s", (email,))
    dustingRow = cur.fetchone()
    if dustingRow:
        return dustingRow['maxDusting']
    else:
        return -1

def getLast6dosages(mysql, today, email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT d.dosage FROM dosages d JOIN medicineEvents me ON (me.id_dosage = d.id_dosage) JOIN users u ON (u.id_user = me.id_user) WHERE me.date <= %s AND u.email = %s ORDER BY date DESC LIMIT 6", (today, email,))
    last6Dosages = cur.fetchall()
    cur.close()
    return last6Dosages

def getDosagesChanges(last6dosages):
    if len(last6dosages) <= 2:
        return 0, 0
    else:
        minus = 0
        plus = 0
        for i in range(1,len(last6dosages)-1):
            print(last6dosages)
            if int(last6dosages[i-1]['dosage']) < int(last6dosages[i]['dosage']):
                plus += 1
            elif int(last6dosages[i-1]['dosage']) > int(last6dosages[i]['dosage']):
                minus += 1
            else:
                pass
        return minus, plus

def getWResults(mysql, today, email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT ct.value AS value FROM controlTests ct JOIN users u ON (u.id_user = ct.id_user) WHERE u.email = %s AND ct.date < %s ORDER BY date DESC LIMIT 14", (email, today,))
    last6Dosages = cur.fetchall()
    last6Dosages = [last6Dosage['value'] for last6Dosage in last6Dosages]
    cur.close()
    return avr(last6Dosages), avr(getLast5Elements(last6Dosages)), getLast1Element(last6Dosages)
    
def avr(list):
    if len(list) == 0:
        return 0
    else:
        sum = 0
        count = 0
        for el in list:
            if el != 0:
                sum += el
                count += 1
        if count == 0:
            return 0
        else:
            return sum / count

def getLast5Elements(list):
    if len(list) >= 5:
        return list[-5:]
    else:
        return list

def getLast1Element(list):
    for i in range(len(list)-1,-1,-1):
        if list[i] != 0:
            return list[i]
    return 0

def getColorInfoByEmail(mysql, email):
    try:
        todayStr = date.today().strftime("%Y-%m-%d")
        cur = mysql.connection.cursor()
        cur.execute("SELECT me.implemented AS implemented FROM medicineEvents me JOIN users u ON (u.id_user = me.id_user) WHERE u.email = %s AND me.date = %s", (email, todayStr,))
        row = cur.fetchone()
        if not row:
            return json.dumps({"text":encrypt("NO ME FOR TODAY")})
        implemented = row['implemented']
        cur.close()
        if implemented == 1:
            return json.dumps({"text":encrypt("YES")})
        elif implemented == 0:
            return json.dumps({"text":encrypt("NO")})
        else:
            return json.dumps({"text":encrypt("ERROR")})
    except:
        return json.dumps({"text":encrypt("ERROR")})

def addFirstMedicineEventAndTestByEmail(mysql, email):
    try:
        todayStr = date.today().strftime("%Y-%m-%d")
        cur = mysql.connection.cursor()
        idUser = getIdUserByEmail(mysql, email)
        cur.execute("INSERT INTO medicineEvents (id_user, implemented, date, id_dosage) VALUES (%s, FALSE, %s, 1)", (idUser, todayStr,))
        cur.execute("INSERT INTO controlTests (id_user, date, value) VALUES (%s, %s, 0)", (idUser, todayStr,))
        mysql.connection.commit()
        cur.close()
        return json.dumps({"text":encrypt("success")})
    except:
        return json.dumps({"text":encrypt("ERROR")})

def addMissingMedicineEventsAndTestsByEmail(mysql, email):
    try:
        todayDate = date.today()
        todayStr = todayDate.strftime("%Y-%m-%d")
        cur = mysql.connection.cursor()
        idUser = getIdUserByEmail(mysql, email)
        cur.execute("SELECT date AS date FROM medicineEvents WHERE id_user = %s ORDER BY date DESC LIMIT 1", (idUser,))
        row = cur.fetchone()
        lastDateME = row['date']
        cur.execute("SELECT date AS date FROM controlTests WHERE id_user = %s ORDER BY date DESC LIMIT 1", (idUser,))
        row = cur.fetchone()
        lastDateCT = row['date']

        if todayDate != lastDateME:
            iDate = lastDateME
            while True:
                iDate += timedelta(days=1)
                iDateStr = iDate.strftime("%Y-%m-%d")
                lastIdDosage = getYasterdaysIdDosageByIdUserAndDate(mysql, idUser, (iDate-timedelta(days=1)).strftime("%Y-%m-%d"),)
                cur.execute("INSERT INTO medicineEvents (id_user, implemented, date, id_dosage) VALUES (%s, FALSE, %s, %s)", (idUser, iDateStr, lastIdDosage,))
                if iDate == todayDate:
                    break

        if todayDate != lastDateCT:
            iDate = lastDateCT
            while True:
                iDate += timedelta(days=1)
                iDateStr = iDate.strftime("%Y-%m-%d")
                cur.execute("INSERT INTO controlTests (id_user, date, value) VALUES (%s, %s, 0)", (idUser, iDateStr,))
                if iDate == todayDate:
                    break
        
        mysql.connection.commit()
        cur.close()
        return json.dumps({"text":encrypt("success")})
    except:
        return json.dumps({"text":encrypt("ERROR")})

def getYasterdaysIdDosageByIdUserAndDate(mysql, idUser, date,):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id_dosage FROM medicineEvents WHERE id_user = %s AND date = %s", (idUser, date,))
    row = cur.fetchone()
    cur.close()
    return row['id_dosage']

def getIdUserByEmail(mysql, email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id_user FROM users WHERE email = %s", (email,))
    row = cur.fetchone()
    cur.close()
    return row['id_user']
        
def getMedicinesByEmail(mysql, email):
    cur = mysql.connection.cursor()
    idUser = getIdUserByEmail(mysql, email)
    cur.execute("SELECT m.name AS name FROM medicines m JOIN medicinesUsed mu ON (mu.id_medicine = m.id_medicine) WHERE mu.id_user = %s AND mu.stop_date IS NULL", (idUser,))
    medicineNames = cur.fetchall()
    data = [{"medicineName":encrypt(el['name'])} for el in medicineNames]
    cur.close()
    return json.dumps(data)

def addNewMedicineByEmail(mysql, medicineName, email):
    try:
        cur = mysql.connection.cursor()
        idUser = getIdUserByEmail(mysql, email)
        cur.execute("INSERT INTO medicines (name) VALUES (%s)", (medicineName,))
        mysql.connection.commit()
        cur.execute("SELECT id_medicine FROM medicines WHERE name = %s", (medicineName,))
        id_medicine_row = cur.fetchone()
        id_medicine = id_medicine_row['id_medicine']
        todayStr = date.today().strftime("%Y-%m-%d")
        cur.execute("INSERT INTO medicinesUsed (id_user, id_medicine, start_date, stop_date) VALUES (%s, %s, %s, NULL)", (idUser, id_medicine, todayStr,))
        mysql.connection.commit()
        cur.close()
        return json.dumps({"text":encrypt("success")})
    except:
        return json.dumps({"text":encrypt("ERROR")})

def deleteMedicinesUsedByEmail(mysql, medicinesToDelete, email):
    try:
        cur = mysql.connection.cursor()
        idUser = getIdUserByEmail(mysql, email)
        todayStr = date.today().strftime("%Y-%m-%d")
        for medicine in medicinesToDelete:
            idMedicine = getIdMedicineByMedicineName(mysql, medicine)
            cur.execute("UPDATE medicinesUsed SET stop_date = %s WHERE id_user = %s AND id_medicine = %s", (todayStr, idUser, idMedicine,))
        mysql.connection.commit()
        cur.close()
        return json.dumps({"text":encrypt("success")})
    except:
        return json.dumps({"text":encrypt("ERROR")})
        
def getIdMedicineByMedicineName(mysql, medicineName):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id_medicine FROM medicines WHERE name = %s", (medicineName,))
    row = cur.fetchone()
    cur.close()
    return row['id_medicine']

def changeDosageByEmailAndMode(mysql, email, mode):
    try:
        cur = mysql.connection.cursor()
        idUser = getIdUserByEmail(mysql, email)
        todayStr = date.today().strftime("%Y-%m-%d")
        cur.execute("SELECT d.dosage AS dosage, d.id_dosage AS id_dosage FROM dosages d JOIN medicineEvents me ON (d.id_dosage = me.id_dosage) WHERE me.id_user = %s AND me.date = %s LIMIT 1", (idUser, todayStr,))
        row = cur.fetchone()
        oldDosage = row['dosage']
        idDosage = row['id_dosage']
        if mode == "0":
            result = oldDosage
        elif mode == "1":
            if oldDosage == "0":
                result = oldDosage
            else:
                newDodage = str(int(oldDosage)-1)
                saveNewDosage(mysql, idUser, newDodage)
                result = newDodage
        elif mode == "2":
            if oldDosage == "10":
                result = oldDosage
            else:
                newDodage = str(int(oldDosage)+1)
                saveNewDosage(mysql, idUser, newDodage)
                result = newDodage
        else:
            result = "ERROR"
        cur.close()
        return json.dumps({"text":encrypt(result)})
    except:
        return json.dumps({"text":encrypt("ERROR")})
    
def saveNewDosage(mysql, idUser, newDodageName):
    cur = mysql.connection.cursor()
    cur.execute("SELECT id_dosage FROM dosages WHERE dosage = %s", (newDodageName,))
    row = cur.fetchone()
    idDosage = row['id_dosage']
    todayStr = date.today().strftime("%Y-%m-%d")
    cur.execute("UPDATE medicineEvents SET id_dosage = %s WHERE id_user = %s AND date = %s", (idDosage, idUser, todayStr,))
    mysql.connection.commit()
    cur.close()

def getUsersAllergiesByEmail(mysql, email):
    cur = mysql.connection.cursor()
    idUser = getIdUserByEmail(mysql, email)
    cur.execute("SELECT name FROM allergies WHERE id_user = %s", (idUser,))
    allergieNames = cur.fetchall()
    data = [{"text":encrypt(el['name'])} for el in allergieNames]
    cur.close()
    return json.dumps(data)

def addNewAllergyByEmail(mysql, email, newAllergy):
    try:
        cur = mysql.connection.cursor()
        idUser = getIdUserByEmail(mysql, email)
        cur.execute("INSERT INTO allergies (id_user, name) VALUES (%s, %s)", (idUser, newAllergy,))
        mysql.connection.commit()
        cur.close()
        return json.dumps({"text":encrypt("success")})
    except:
        return json.dumps({"text":encrypt("ERROR")})

def deleteAllergiesUsedByEmail(mysql, email, allergiesToDelete):
    try:
        cur = mysql.connection.cursor()
        idUser = getIdUserByEmail(mysql, email)
        for allergy in allergiesToDelete:
            cur.execute("DELETE FROM allergies WHERE id_user = %s AND name = %s", (idUser, allergy,))
        mysql.connection.commit()
        cur.close()
        return json.dumps({"text":encrypt("success")})
    except:
        return json.dumps({"text":encrypt("ERROR")})

def getAllAsthmaFactorsNames(mysql):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT name FROM asthmaFactors")
        asthmaFactorsNames = cur.fetchall()
        data = [{"text":el['name']} for el in asthmaFactorsNames]
        cur.close()
        return json.dumps(data)
    except:
        return json.dumps({"text":"ERROR"})

def getAndSaveWeather():
    api_key = "5a4211dc147c481028c7a850f0bec41e"
    base_url = "http://api.openweathermap.org/data/2.5/weather?"
    city_name = "Krakow" 
    complete_url = base_url + "q=" + city_name + "&appid=" + api_key
    response = requests.get(complete_url) 
    res = response.json() 
    if res["cod"] != "404": 
        main = res['main']
        temperatureMax = "%.1f" % (main['temp_max'] - 273.15)
        wind = res['wind']
        speed = wind['speed']
        try:
            rain = res['rain']
            d1 = rain['1h']
        except:
            d1 = 0
        tomorrowStr = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        mysql = dbConnection()
        cur = mysql.cursor()
        cur.execute("INSERT INTO weather (date, temperature, wind, rain) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE temperature = %s, wind = %s, rain = %s", (tomorrowStr, temperatureMax, speed, d1, temperatureMax, speed, d1,))
        mysql.commit()
        cur.close()
        mysql.close()
    else: 
        return

def dbConnection():
    myHost, myUser, myPasswd, myDatabase, port = getCredentials()
    dataBase = mysql.connector.connect(
        host = myHost,
        user = myUser,
        passwd = myPasswd,
        database = myDatabase,
        port = port
    )
    return dataBase


# traceback.print_exc()
