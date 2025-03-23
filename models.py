from database import db
from datetime import datetime

class Rol(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(30), unique=True, nullable=False)

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(50), nullable=False)
    usuario = db.Column(db.String(30), unique=True, nullable=False)
    placa = db.Column(db.String(100), unique=True, nullable=False)
    telefono = db.Column(db.String(20), unique=True, nullable=True)
    contraseña = db.Column(db.String(100), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False) 
    fecha_creacion = db.Column(db.DateTime, default=db.func.current_timestamp()) 


    ubicaciones = db.relationship('Ubicacion', backref='usuario', lazy=True)

    # 🔹 Relación con las rutas creadas por el usuario
    rutas_creadas = db.relationship('Ruta', foreign_keys='Ruta.creador_id', backref='usuario_creador', lazy=True, overlaps="rutas_creadas, creador")

    # 🔹 Relación con las rutas asignadas al usuario
    rutas_asignadas = db.relationship('Ruta', foreign_keys='Ruta.asignado_id', backref='usuario_asignado', lazy=True, overlaps="rutas_asignadas, asignado")


class Ubicacion(db.Model):
    __tablename__ = 'ubicaciones'
    id = db.Column(db.Integer, primary_key=True)
    codcli = db.Column(db.String(20), nullable=False)  
    hora = db.Column(db.String(20), nullable=False)  
    nombre = db.Column(db.String(100), nullable=False)  
    nomcli = db.Column(db.String(100), nullable=False)  
    codsolot = db.Column(db.String(20), nullable=False)  
    direccion = db.Column(db.String(200), nullable=False)  
    distrito = db.Column(db.String(100), nullable=False)  
    plano = db.Column(db.String(50), nullable=True)  
    descripcion = db.Column(db.String(200), nullable=True)  
    telefono = db.Column(db.String(20), nullable=True)  
    tipo_ubicacion = db.Column(db.String(20), nullable=True)  
    referencia = db.Column(db.String(200), nullable=True)  
    operadora = db.Column(db.String(50), nullable=True)  
    latitud = db.Column(db.Float, nullable=True)  
    longitud = db.Column(db.Float, nullable=True) 
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)  

    estado = db.Column(db.Boolean, default=True, nullable=False)


class UbicacionAtendida(db.Model):
    __tablename__ = 'ubicaciones_atendidas'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ubicacion_id = db.Column(db.Integer, db.ForeignKey('ubicaciones.id'), nullable=False)  # Relación con Ubicación
    atendido_por = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)  # Usuario que atendió
    fecha_hora_atencion = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)  # Fecha y hora de atención
    tipo_atencion = db.Column(db.String(20), nullable=False)  # "Efectiva" o "No efectiva"
    comentario = db.Column(db.String(300), nullable=True)

    # Relación con la ubicación
    ubicacion = db.relationship('Ubicacion', backref='atenciones')

    # Relación con el usuario que atendió
    usuario = db.relationship('Usuario', backref='atenciones_realizadas')



class Ruta(db.Model):
    __tablename__ = 'rutas'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_ruta = db.Column(db.String(40), nullable=False)
    fecha_creacion = db.Column(db.Date, default=datetime.utcnow)

    # 🔹 Usuario que creó la ruta
    creador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    creador = db.relationship('Usuario', foreign_keys=[creador_id], overlaps="rutas_creadas, usuario_creador")

    # 🔹 Usuario al que se le asigna la ruta (puede ser nulo hasta que se asigne)
    asignado_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    asignado = db.relationship('Usuario', foreign_keys=[asignado_id], overlaps="rutas_asignadas, usuario_asignado")

    # 🔹 Relación con las ubicaciones dentro de la ruta
    rutas_ubicaciones = db.relationship('RutaUbicacion', backref='ruta', lazy=True)


class RutaUbicacion(db.Model):
    __tablename__ = 'rutas_ubicaciones'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ruta_id = db.Column(db.Integer, db.ForeignKey('rutas.id'), nullable=False)
    ubicacion_id = db.Column(db.Integer, db.ForeignKey('ubicaciones.id'), nullable=False)
    orden = db.Column(db.Integer, nullable=False)

    ubicacion = db.relationship('Ubicacion', backref='ruta_ubicaciones')
