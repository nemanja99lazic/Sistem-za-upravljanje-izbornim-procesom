import csv
import io
import os
import time

from flask import Flask, request, jsonify, Response
from configuration import Configuration
from izborniZvanicnikDecorator import roleCheck
from flask_jwt_extended import JWTManager, get_jwt
from redis import Redis

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)

@application.route("/vote", methods = ["POST"])
@roleCheck(role = "izborni zvanicnik")
def vote():
    try:
        content = request.files['file'].stream.read().decode('cp1252')
        stream = io.StringIO(content)
        reader = csv.reader(stream)

        claims = get_jwt()
        mojJmbg = claims["jmbg"];

        brojReda = 0
        glasovi = []
        for row in reader:
            # if(len(row) < 2):
            #     return jsonify(message = "Field file missing."), 400
            # if(len(row) > 2):
            if(len(row) != 2):
                return jsonify(message = "Incorrect number of values on line " + str(brojReda) + "."), 400

            try:
                guid = row[0]
                rbUcesnika = int(row[1])
                glas = {
                    "guid": guid,
                    "rbUcesnika": rbUcesnika
                }

                if(rbUcesnika <= 0):
                    raise ValueError

                glasovi.append(guid + "," + str(rbUcesnika) + "," + str(mojJmbg))
            except ValueError:
                return jsonify(message = "Incorrect poll number on line " + str(brojReda) + "."), 400

            brojReda = brojReda + 1

        for glas in glasovi:
            done = False
            while not done:
                with Redis(host=Configuration.REDIS_HOST) as redis:
                    redis.publish(channel = Configuration.REDIS_VOTES_LIST, message=glas)
                    print("Izborni zvanicnik objavio: " + glas)
                    done = True

        with Redis(host=Configuration.REDIS_HOST) as redis:
            redis.publish(channel=Configuration.REDIS_VOTES_LIST, message="EOF") # posalji EOF red
            print("Izborni zvanicnik objavio: EOF")

        return Response(status = 200)
    except Exception:
        return jsonify(message="Field file is missing."), 400

if(__name__ == "__main__"):
    os.environ['TZ'] = 'Europe/Belgrade'
    time.tzset()
    application.run(debug=True, host="0.0.0.0", port=5015)
    #application.run(debug=True, port=5015)