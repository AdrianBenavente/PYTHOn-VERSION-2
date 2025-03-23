from flask import Flask
from config import Config
from database import db
from routes import routes

app = Flask(__name__)
app.config.from_object(Config)

# Inicializar la base de datos
db.init_app(app)

# Registrar las rutas
app.register_blueprint(routes)

# Crear las tablas en la base de datos
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
