import time

from flask import Flask, request, jsonify
from applications.configuration import Configuration
from applications.models import database, Glas, Izbori, Ucesnik, IzboriUcesnik
from adminDecorator import roleCheck
from flask_jwt_extended import JWTManager
from datetime import datetime
from sqlalchemy import func, and_
import os

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)

def sortBrojGlasova(item):
    return int(item["brGlasova"])

def missingFieldCheck(**fields):
    for field in fields:
        if(fields[field] == ""):
            return field
    return ""

def checkInvalidDateAndTime(start, end):
    try:
        datetimeStart = None
        datetimeEnd = None

        # datetimeStart = datetime.fromisoformat(start)
        # datetimeEnd = datetime.fromisoformat(end)

        possibleFormats = ["%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"]
        for format in possibleFormats:
            try:
                datetimeStart = datetime.strptime(start, format)
                datetimeEnd = datetime.strptime(end, format)
            except ValueError:
                pass

        if(datetimeStart is None or datetimeEnd is None):
            raise ValueError

        if(datetimeStart >= datetimeEnd):
            return True

        sviIzbori = Izbori.query.all()
        for izbori in sviIzbori:
            postojeciIzboriStart = izbori.pocetak
            postojeciIzboriEnd = izbori.kraj
            if((datetimeStart <= postojeciIzboriStart and datetimeEnd <= postojeciIzboriEnd and postojeciIzboriStart <= datetimeEnd) or
                    (datetimeStart <= postojeciIzboriStart and postojeciIzboriEnd <= datetimeEnd) or
                    (postojeciIzboriStart <= datetimeStart and datetimeEnd <= postojeciIzboriEnd) or
                    (postojeciIzboriStart <= datetimeStart and postojeciIzboriEnd <= datetimeEnd and datetimeStart <= postojeciIzboriEnd)):
                return True

    except ValueError:
        return True

    return False

def checkInvalidParticipant(predsednicki, ucesnici):
    if(len(ucesnici) < 2):
        return True
    for idUcesnika in ucesnici:
        if(type(idUcesnika) != int):
            return True
        ucesnikBaza = Ucesnik.query.filter(Ucesnik.id == idUcesnika).first()
        if ((ucesnikBaza is None) or (ucesnikBaza.pojedinac and not predsednicki) or (not ucesnikBaza.pojedinac and predsednicki)):
            return True
    return False

@application.route("/createParticipant", methods = ["POST"])
@roleCheck(role = "admin")
def createParticipant():
    ime = request.json.get("name", "")
    pojedinac = request.json.get("individual", "")

    missingFieldName = missingFieldCheck(name = ime, individual = pojedinac)
    if(missingFieldName != ""):
        return jsonify(message = f"Field {missingFieldName} is missing."), 400

    noviUcesnik = Ucesnik(ime = ime, pojedinac = pojedinac)
    database.session.add(noviUcesnik)
    database.session.commit()

    return jsonify(id = noviUcesnik.id)

@application.route("/getParticipants", methods = ["GET"])
@roleCheck(role = "admin")
def getParticipants():
    ucesnici = []
    ucesniciIzBaze = Ucesnik.query.all()
    for ucesnik in ucesniciIzBaze:
        ucesnikDict = {
            "id": int(ucesnik.id),
            "name": ucesnik.ime,
            "individual": bool(ucesnik.pojedinac)
        }
        ucesnici.append(ucesnikDict)


    return jsonify(participants = ucesnici), 200

@application.route("/createElection", methods = ["POST"])
@roleCheck(role = "admin")
def createElection():
    start = request.json.get("start", "")
    end = request.json.get("end", "")
    individual = request.json.get("individual", "")
    participants = request.json.get("participants", "")

    missingField = missingFieldCheck(start = start, end = end, individual = individual, participants = participants)
    if(missingField != ""):
        return jsonify(message = f"Field {missingField} is missing."), 400

    invalidDateAndTime = checkInvalidDateAndTime(start, end)
    if(invalidDateAndTime):
        return jsonify(message = "Invalid date and time."), 400

    invalidParticipant = checkInvalidParticipant(individual, participants)
    if (invalidParticipant):
        return jsonify(message="Invalid participants."), 400

    noviIzbori = Izbori(pocetak = start, kraj = end, predsednicki = individual)

    database.session.add(noviIzbori)
    database.session.commit()

    rb = 1
    for ucesnik in participants:
        ucesnikRed = IzboriUcesnik(izboriId = noviIzbori.id, ucesnikId = ucesnik, redniBroj=rb)
        rb = rb + 1
        database.session.add(ucesnikRed)
    database.session.commit()

    return jsonify(pollNumbers = list(range(1, len(participants) + 1))), 200

@application.route("/getElections", methods=["GET"])
@roleCheck(role = "admin")
def getElections():
    izboriNiz = []

    sviIzbori = Izbori.query.all()
    for izbori in sviIzbori:
        izboriDict = {
            "id": int(izbori.id),
            "start": izbori.pocetak.isoformat(sep='T', timespec='auto'),
            "end": izbori.kraj.isoformat(sep='T', timespec='auto'),
            "individual": bool(int(izbori.predsednicki)),
            "participants": []
        }
        ucesniciIzboraBaza = Ucesnik.query.join(IzboriUcesnik).filter(IzboriUcesnik.izboriId == izbori.id).all()

        for ucesnik in ucesniciIzboraBaza:
            ucesnikDict = {
                "id": ucesnik.id,
                "name": ucesnik.ime
            }
            izboriDict["participants"].append(ucesnikDict)
        izboriNiz.append(izboriDict)

    return jsonify(elections = izboriNiz), 200

@application.route("/getResults", methods = ["GET"])
@roleCheck(role = "admin")
def getResults():
    if(request.args.get("id", "") != ""):
        time.sleep(5)
        izboriId = int(request.args.get("id"))
        izbori = Izbori.query.filter(Izbori.id == izboriId).first()
        if(izbori is None):
            return jsonify(message="Election does not exist."), 400

        now = datetime.now()
        now = datetime.isoformat(now)
        if(now < datetime.isoformat(izbori.kraj)):
            return jsonify(message="Election is ongoing."), 400

        ucesnici = IzboriUcesnik.query.join(Ucesnik, Ucesnik.id == IzboriUcesnik.ucesnikId).\
                    add_columns(Ucesnik.ime, IzboriUcesnik.redniBroj).\
                    filter(IzboriUcesnik.izboriId == izboriId).all()

        listaUcesnika = []
        for ucesnik in ucesnici:
            listaUcesnika.append({
                "name": ucesnik.ime,
                "pollNumber": int(ucesnik.redniBroj),
                "result": 0
            })

        ukupanBrojGlasova = int(Glas.query.filter(and_(Glas.izboriId == izboriId, Glas.validan == True)).count())
        if(izbori.predsednicki):

            for ucesnikNaIzborima in listaUcesnika:
                brojGlasova = Glas.query.filter(and_(ucesnikNaIzborima["pollNumber"] == Glas.rbUcesnika, Glas.validan == True, Glas.izboriId == izboriId)).count()
                ucesnikNaIzborima["result"] = round(int(brojGlasova) / ukupanBrojGlasova, 2) if ukupanBrojGlasova != 0 else 0
        else:
            osvojioMandata = []

            for ucesnikNaIzborima in listaUcesnika:
                brojGlasovaUcesnik = Glas.query.filter(
                    and_(ucesnikNaIzborima["pollNumber"] == Glas.rbUcesnika, Glas.validan == True, Glas.izboriId == izboriId)).count()

                if(ukupanBrojGlasova == 0 or round(brojGlasovaUcesnik / ukupanBrojGlasova,2) < 0.050000001):
                    osvojioMandata.append({
                        "rb":ucesnikNaIzborima["pollNumber"],
                        "mandata": -1,
                        "brGlasova": brojGlasovaUcesnik
                    }) # nije presao cenzus
                else:
                    osvojioMandata.append({
                        "rb":ucesnikNaIzborima["pollNumber"],
                        "mandata": 0,
                        "brGlasova": brojGlasovaUcesnik
                    }) # presao cenzus

            # sortiraj liste opadajuce po broju glasova
            osvojioMandata.sort(reverse=True, key=sortBrojGlasova)

            # racunaj broj mandata
            ostaloMandata = 250
            while (ostaloMandata > 0):
                indMax = 0
                maxKoef = -1
                for i in range(0, len(osvojioMandata)):
                    if(osvojioMandata[i]["mandata"] != -1):
                        koef = round(osvojioMandata[i]["brGlasova"] / (1 + osvojioMandata[i]["mandata"]), 4)
                        if(koef >= maxKoef):
                            indMax = i
                            maxKoef = koef
                ostaloMandata -= 1
                osvojioMandata[indMax]["mandata"] += 1

            # prepisi broj mandata za svakog ucesnika
            for i in range(0, len(listaUcesnika)):
                for j in range(0, len(osvojioMandata)):
                    if(listaUcesnika[i]["pollNumber"] == osvojioMandata[j]["rb"]):
                        if(osvojioMandata[j]["mandata"] == -1):
                            listaUcesnika[i]["result"] = 0
                        else:
                            listaUcesnika[i]["result"] = osvojioMandata[j]["mandata"]
                        break

        # dodaj nevalidne glasove
        nevalidniGlasovi = []
        nevalidniGlasoviBaza = Glas.query.filter(and_(Glas.izboriId == izboriId, Glas.validan == False)).all()

        for nevalidniGlas in nevalidniGlasoviBaza:
            nevalidniGlasovi.append({
                "electionOfficialJmbg": nevalidniGlas.jmbgZvanicnika,
                "ballotGuid": nevalidniGlas.GUID,
                "pollNumber": nevalidniGlas.rbUcesnika,
                "reason": nevalidniGlas.razlogNevalidnosti
            })

        return jsonify(participants=listaUcesnika, invalidVotes=nevalidniGlasovi), 200
    else:
        return jsonify(message="Field id is missing."), 400



@application.route("/", methods = ["GET"])
def test():
    start = datetime.fromisoformat("2021-06-16T15:55:46+01:00")
    end = datetime.fromisoformat("2021-06-16T15:55:46+01:00")
    return str(start > end)

if(__name__ == "__main__"):
    os.environ['TZ'] = 'Europe/Belgrade'
    time.tzset()
    database.init_app(application)
    application.run(debug=True, host="0.0.0.0", port=5005)
    #application.run(debug=True, port=5010)