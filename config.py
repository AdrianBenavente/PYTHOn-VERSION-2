import os

class Config:
    SECRET_KEY = 'tu_clave_secreta_aqui'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:5432@localhost/DBCOMM'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads'
    SESSION_PERMANENT = False
    SESSION_TYPE = "filesystem"
    
    # Clave de la API de Google Maps
    GOOGLE_MAPS_API_KEY = "AIzaSyDkIJue197TWs72TyCTWSlgArnmj-Z3Qh0"
