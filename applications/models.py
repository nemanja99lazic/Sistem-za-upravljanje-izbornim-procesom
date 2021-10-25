from flask_sqlalchemy import SQLAlchemy;
import json

database = SQLAlchemy();

class IzboriUcesnik(database.Model):
    __tablename__ = "izboriucesnik"

    id = database.Column(database.Integer, primary_key=True)
    izboriId = database.Column(database.Integer, database.ForeignKey("izbori.id", ondelete="CASCADE"), nullable=False)
    ucesnikId = database.Column(database.Integer, database.ForeignKey("ucesnici.id", ondelete="CASCADE"), nullable=False)
    redniBroj = database.Column(database.Integer, nullable=False) #pollNumber


class Izbori(database.Model):
    __tablename__ = "izbori"

    id = database.Column(database.Integer, primary_key=True)
    pocetak = database.Column(database.DateTime, nullable=False)
    kraj = database.Column(database.DateTime, nullable=False)
    predsednicki = database.Column(database.Boolean, nullable=False)  # true - predsednicki; false - parlamentarni

    glasovi = database.relationship("Glas", back_populates="izbori")
    ucesnici = database.relationship("Ucesnik", secondary = IzboriUcesnik.__table__, back_populates="izbori")


class Ucesnik(database.Model):
    __tablename__ = "ucesnici"

    id = database.Column(database.Integer, primary_key=True)
    ime = database.Column(database.String(256), nullable=False)
    pojedinac = database.Column(database.Boolean, nullable=False)  # true - pojedinac; false - partija

    #glasovi = database.relationship("Glas", back_populates="ucesnik")
    izbori = database.relationship("Izbori", secondary = IzboriUcesnik.__table__, back_populates="ucesnici")

    def __repr__(self):
        return f"{self.ime}, {self.pojedinac} "

class Glas(database.Model):
    __tablename__ = "glasovi"

    id = database.Column(database.Integer, primary_key=True)
    GUID = database.Column(database.String(36), nullable=False)
    jmbgZvanicnika = database.Column(database.String(13), nullable=False)
    izboriId = database.Column(database.Integer, database.ForeignKey("izbori.id", ondelete="CASCADE"), nullable=False)
    rbUcesnika = database.Column(database.Integer)
    validan = database.Column(database.Boolean, nullable=False)
    razlogNevalidnosti = database.Column(database.String(80))

    izbori = database.relationship("Izbori", back_populates="glasovi")
    #ucesnik = database.relationship("Ucesnik", back_populates="glasovi")