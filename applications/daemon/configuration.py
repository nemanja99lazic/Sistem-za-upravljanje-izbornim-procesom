import os

databaseUrl = os.environ["IZBORI_DATABASE_URL"]
#databaseUrl = "localhost:6036"   ---------- ovo je za localhost
databaseUrl="izboridb" #---- ovo je za docker

#databaseUrl = "localhost:6036"

class Configuration ( ):
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://root:root@{databaseUrl}/izbori_database";
    JWT_SECRET_KEY = "Tajni JWT kljuc koji niko ne zna"
    REDIS_HOST = "daemon";
    REDIS_VOTES_LIST = "votes";

