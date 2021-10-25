from datetime import timedelta
import os

databaseUrl = os.environ["DATABASE_URL"] # za docker
#databaseUrl = 'localhost:6035' # za lokal

class Configuration ( ):
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://root:root@{databaseUrl}/authentication";
    JWT_SECRET_KEY = "Tajni JWT kljuc koji niko ne zna"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours = 1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days = 30)


