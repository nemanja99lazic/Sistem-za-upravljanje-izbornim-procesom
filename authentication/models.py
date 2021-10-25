from flask_sqlalchemy import SQLAlchemy;

database = SQLAlchemy()

class UlogaKorisnika(database.Model):
    __tablename__ = "ulogekorisnika"

    id = database.Column(database.Integer, primary_key = True)
    ime = database.Column(database.String(256), nullable = False)

    korisnici = database.relationship("Korisnik", back_populates = "uloga")

    def __repr__(self):
        return self.ime

class Korisnik(database.Model):
    __tablename__ = "korisnici"

    id = database.Column(database.Integer, primary_key = True)
    email = database.Column(database.String(256), nullable = False, unique = True)
    lozinka = database.Column(database.String(256), nullable = False)
    ime = database.Column(database.String(256), nullable = False)
    prezime = database.Column(database.String(256), nullable = False)
    jmbg = database.Column(database.String(13), nullable = False, unique = True)
    ulogaId = database.Column(database.Integer, database.ForeignKey("ulogekorisnika.id"), nullable = False)

    uloga = database.relationship("UlogaKorisnika", back_populates = "korisnici")