import time

from flask import Flask, request, jsonify
from applications.configuration import Configuration
from applications.models import database, Glas, Izbori, Ucesnik, IzboriUcesnik
from flask_jwt_extended import JWTManager
from redis import Redis
from datetime import datetime
from sqlalchemy import and_
import threading
import os

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)

def getActiveElection():
    now = datetime.now()
    now = datetime.isoformat(now)

    aktivniIzbori = Izbori.query.filter(and_(Izbori.pocetak <= now, Izbori.kraj > now)).first()

    return aktivniIzbori

def checkDuplicateBallot(GUID):
    duplikat = Glas.query.filter(Glas.GUID == GUID).first()
    if(duplikat != None):
        return True
    return False

def checkInvalidPollNumber(rbUcesnika, izboriId):
    izboriUcesnik = IzboriUcesnik.query.filter(and_(IzboriUcesnik.izboriId == izboriId, IzboriUcesnik.redniBroj == rbUcesnika)).first()
    if(izboriUcesnik != None):
        return False
    return True

def daemonThread():
    done = False
    while not done:
        try:
            with application.app_context():
                with Redis(host=Configuration.REDIS_HOST) as redis:
                    subscriber = redis.pubsub()
                    subscriber.subscribe([Configuration.REDIS_VOTES_LIST])

                    done = True
                    print("Connection established.");

                    for glasKodovan in subscriber.listen():
                        if(glasKodovan["data"] == 1): # prva poruka koja se primi bude data = 1, zato je preskoci
                            continue
                        if(glasKodovan["data"].decode("utf-8") == "EOF"): # proveri da li je poslata poruka za kraj fajla
                           database.session.commit()
                        else:
                            glas = glasKodovan["data"].decode("utf-8")
                            glas = glas.split(",")

                            GUID = glas[0]
                            rbUcesnika = int(glas[1])
                            jmbgZvanicnika = glas[2]

                            aktivniIzbori = getActiveElection()
                            if(aktivniIzbori != None):
                                if(checkDuplicateBallot(GUID) == True):
                                    glas = Glas(GUID=GUID, jmbgZvanicnika=jmbgZvanicnika, izboriId=aktivniIzbori.id, rbUcesnika=rbUcesnika, validan=False,
                                                razlogNevalidnosti="Duplicate ballot.")
                                    database.session.add(glas)
                                    #database.session.commit()
                                    #print("ODBACEN GUID:" + GUID + ", rbUcesnika:" + str(rbUcesnika) + ", " + jmbgZvanicnika + " - DUPLIKAT")
                                    continue

                                if(checkInvalidPollNumber(rbUcesnika, aktivniIzbori.id) == True):
                                    glas = Glas(GUID=GUID, jmbgZvanicnika=jmbgZvanicnika, izboriId=aktivniIzbori.id,
                                                rbUcesnika=rbUcesnika, validan=False,
                                                razlogNevalidnosti="Invalid poll number.")
                                    database.session.add(glas)
                                    #database.session.commit()
                                    print("ODBACEN GUID:" + GUID + ", rbUcesnika:" + str(rbUcesnika) + ", " + jmbgZvanicnika + " - RB NIJE VALIDAN")
                                    continue

                                # upisivanje validnog glasa
                                glas = Glas(GUID=GUID, jmbgZvanicnika=jmbgZvanicnika, izboriId=aktivniIzbori.id,
                                            rbUcesnika=rbUcesnika, validan=True)
                                database.session.add(glas)
                                #database.session.commit()
                                print("GUID:" + GUID + ", rbUcesnika:" + str(rbUcesnika) + ", " + jmbgZvanicnika + ", TIME: " + str(datetime.now()))
                            else:
                                print("Nema aktivnih izbora za uneti glas" + str(datetime.now()))
        except Exception as error:
            print(error)

if(__name__ == "__main__"):
    os.environ['TZ'] = 'Europe/Belgrade'
    time.tzset()
    database.init_app(application)
    print(str(datetime.now()))
    threading.Thread(target=daemonThread, args=()).start()