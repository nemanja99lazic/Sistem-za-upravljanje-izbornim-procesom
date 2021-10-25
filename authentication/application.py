import re
import os
import time

from flask import Flask, request, Response, jsonify;
from sqlalchemy import and_;
from configuration import Configuration
from models import database, UlogaKorisnika, Korisnik
from roleCheckDecorator import roleCheck
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, create_refresh_token, get_jwt, get_jwt_identity;

application = Flask(__name__)
application.config.from_object(Configuration)
jwt = JWTManager(application)

def missingFieldsCheck(jmbg, ime, prezime, email, lozinka):
    if(len(jmbg) == 0):
        return "jmbg"
    if(len(ime) == 0):
        return "forename"
    if(len(prezime) == 0):
        return "surname"
    if(len(email) == 0):
        return "email"
    if(len(lozinka) == 0):
        return "password"
    return ""

def jmbgInvalidCheck(jmbg):

    if(len(jmbg) != 13):
        return True

    dd = int(jmbg[0:2])
    mm = int(jmbg[2:4])
    yyy = int(jmbg[4:7])
    rr = int(jmbg[7:9])
    bbb = int(jmbg[9:12])
    k = int(jmbg[12])

    check = {
        'a' : int(jmbg[0]),
        'b' : int(jmbg[1]),
        'c' : int(jmbg[2]),
        'd' : int(jmbg[3]),
        'e' : int(jmbg[4]),
        'f' : int(jmbg[5]),
        'g' : int(jmbg[6]),
        'h' : int(jmbg[7]),
        'i' : int(jmbg[8]),
        'j' : int(jmbg[9]),
        'k' : int(jmbg[10]),
        'l' : int(jmbg[11]),
        'm' : int(jmbg[12])
    }

    checksum = 11 - (( 7 * (check['a'] + check['g']) + 6 * (check['b'] + check['h']) + 5 * (check['c'] + check['i']) + 4 * (check['d'] + check['j']) + 3 * (check['e'] + check['k']) + 2 * (check['f'] + check['l']) ) % 11)
    if(checksum == 10 or checksum == 11):
        checksum = 0

    if(1 <= dd <= 31 and 1 <= mm <= 12 and 70 <= rr <= 99 and checksum == k):
        return False
    return True

def emailInvalidCheck(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if (re.fullmatch(regex, email)):
        return False
    else:
        return True

def passwordInvalidCheck(password):
    if( re.search("[a-z]", password) != None and
        re.search("[A-Z]", password) != None and
        re.search("\d", password) != None and
        len(password) >= 8):
        return False
    return True

def emailAlreadyExistsCheck(email):
    korisnikSaIstimMejlom = Korisnik.query.filter(Korisnik.email == email).first()
    if (korisnikSaIstimMejlom != None):
        return True
    return False

@application.route("/register", methods = ["POST"])
def register():
    jmbg = request.json.get("jmbg", "")
    ime = request.json.get("forename", "")
    prezime = request.json.get("surname", "")
    email = request.json.get("email", "")
    lozinka = request.json.get("password", "")

    missingFieldName = missingFieldsCheck(jmbg, ime, prezime, email, lozinka)
    if(missingFieldName != ""):
        return jsonify(message=f"Field {missingFieldName} is missing."), 400

    jmbgInvalid = jmbgInvalidCheck(jmbg)
    if(jmbgInvalid):
        return jsonify(message="Invalid jmbg."), 400

    emailInvalid = emailInvalidCheck(email)
    if(emailInvalid):
        return jsonify(message="Invalid email."), 400

    passwordInvalid = passwordInvalidCheck(lozinka)
    if(passwordInvalid):
        return jsonify(message="Invalid password."), 400

    emailAlreadyExists = emailAlreadyExistsCheck(email)
    if(emailAlreadyExists):
        return jsonify(message="Email already exists."), 400

    noviKorisnik = Korisnik(
        email = email,
        ime = ime,
        prezime = prezime,
        lozinka = lozinka,
        jmbg = jmbg,
    )

    noviKorisnik.ulogaId = UlogaKorisnika.query.filter(UlogaKorisnika.ime == "izborni zvanicnik").first().id

    database.session.add(noviKorisnik)
    database.session.commit()

    return Response(status=200)

@application.route("/login", methods=["POST"])
def login():
    email = request.json.get("email", "")
    password = request.json.get("password", "")

    if(len(email) == 0):
        return jsonify(message = "Field email is missing."), 400
    if(len(password) == 0):
        return jsonify(message = "Field password is missing."), 400

    invalidEmail = emailInvalidCheck(email)
    if(invalidEmail):
        return jsonify(message = "Invalid email."), 400

    korisnik = Korisnik.query.filter(and_(Korisnik.email == email, Korisnik.lozinka == password)).first()
    if(not korisnik):
        return jsonify(message = "Invalid credentials."), 400

    additionalClaims = {
                        "forename": korisnik.ime,
                        "surname": korisnik.prezime,
                        "email": korisnik.email,
                        "password": korisnik.lozinka,
                        "jmbg": korisnik.jmbg,
                        "roles": korisnik.uloga.ime
                        }

    accessToken = create_access_token(identity = korisnik.email, additional_claims = additionalClaims)
    refreshToken = create_refresh_token(identity = korisnik.email, additional_claims = additionalClaims)

    return jsonify(accessToken=accessToken, refreshToken=refreshToken)

@application.route("/refresh", methods = ["POST"])
@jwt_required(refresh = True)
def refresh():
    identity = get_jwt_identity()
    refreshClaims = get_jwt()

    additionalClaims = {
        "email" : refreshClaims["email"],
        "password" : refreshClaims["password"],
        "forename" : refreshClaims["forename"],
        "surname" : refreshClaims["surname"],
        "jmbg" : refreshClaims["jmbg"],
        "roles": refreshClaims["roles"]
    }

    return jsonify(accessToken = create_access_token(identity=identity, additional_claims=additionalClaims)), 200

@application.route("/delete", methods=["POST"])
@jwt_required()
@roleCheck(role ="admin")
def izbrisiKorisnika():
    email = request.json.get("email", "")

    if(len(email) == 0):
        return jsonify(message = "Field email is missing."), 400

    invalidEmail = emailInvalidCheck(email)
    if(invalidEmail):
        return jsonify(message = "Invalid email."), 400

    korisnik = Korisnik.query.filter(Korisnik.email == email).first()
    if not korisnik:
        return jsonify(message = "Unknown user."), 400

    database.session.delete(korisnik)
    database.session.commit()

    return Response(status=200)

@application.route("/test", methods = ["GET"])
def helloWorld():
    return "Hello world"

if(__name__ == "__main__"):
    database.init_app(application)
    os.environ['TZ'] = 'Europe/Belgrade'
    time.tzset()
    application.run(debug = True, host = "0.0.0.0", port = 5002)
    #application.run(debug=True, port=5002) ---- za localhost