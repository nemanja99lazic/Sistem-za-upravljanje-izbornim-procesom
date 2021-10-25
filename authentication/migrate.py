from flask import Flask
from sqlalchemy_utils import database_exists, create_database
from flask_migrate import Migrate, init, migrate, upgrade

from models import database, Korisnik, UlogaKorisnika

from configuration import Configuration

application = Flask(__name__)
application.config.from_object(Configuration)

migrateObject = Migrate(application, database)

done = False

while not done:
    try:
        if(not database_exists(application.config["SQLALCHEMY_DATABASE_URI"])):
            create_database(application.config["SQLALCHEMY_DATABASE_URI"])

        database.init_app(application)

        with application.app_context() as context:
            init()
            migrate(message = "Created database")
            upgrade()

            admin = UlogaKorisnika(ime = "admin")
            izborniZvanicnik = UlogaKorisnika(ime = "izborni zvanicnik")

            database.session.add(admin)
            database.session.add(izborniZvanicnik)
            database.session.commit()

            korisnikAdmin = Korisnik(
                email="admin@admin.com",
                lozinka="1",
                ime="admin",
                prezime="admin",
                jmbg="0000000000000",
                ulogaId=1
            )

            database.session.add(korisnikAdmin)
            database.session.commit()

            done = True
    except Exception as error:
        print(error)
