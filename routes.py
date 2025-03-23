from flask import send_file, Blueprint, request, render_template, redirect, url_for, session, jsonify
from models import Usuario, Ubicacion, Ruta, RutaUbicacion, UbicacionAtendida, db
from functools import wraps
import pandas as pd
import os
import requests
import re
from config import Config
from utils import clean_address, get_coordinates
from datetime import datetime

routes = Blueprint('routes', __name__)

UPLOAD_FOLDER = Config.UPLOAD_FOLDER
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Decorador para requerir login
def login_required(route):
    @wraps(route)
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('routes.login'))
        return route(*args, **kwargs)
    return wrapper

# Ruta de login
@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    usuario = Usuario.query.filter_by(usuario=username).first()

    if usuario and usuario.contraseña == password:
        session.clear()  # 🔹 Asegura que no haya sesiones previas activas
        session['username'] = username
        session['user_id'] = usuario.id
        session.permanent = False  # 🔹 Hace que la sesión expire al cerrar el navegador
        return jsonify({"success": True, "message": "Inicio de sesión exitoso"}), 200
    else:
        return jsonify({"success": False, "message": "Usuario o contraseña incorrectos"}), 401

# Ruta de logout
@routes.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for('routes.login'))

# Página principal
@routes.route('/')
@login_required
def index():
    return render_template('index.html')

# Ruta para visualizar el mapa
@routes.route('/map')
@login_required
def map():
    usuarios = Usuario.query.all()  # 🔹 Obtener todos los usuarios
    return render_template('map.html', usuarios=usuarios)

# Cargar datos desde un archivo Excel
@routes.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No se subió ningún archivo"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "message": "Nombre de archivo inválido"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    df = pd.read_excel(file_path)

    required_columns = ['codcli', 'hora', 'nombre', 'nomcli', 'codsolot', 'direccion', 'distrito', 
                        'plano', 'descripcion', 'telefono', 'tipo_visita', 'referencia', 'operadora']
    
    if not all(col in df.columns for col in required_columns):
        return jsonify({"success": False, "message": "El archivo Excel no contiene las columnas necesarias"}), 400

    registros_guardados = 0
    asignado_id = request.form.get("usuario_asignado")  # Usuario al que se le asignan las ubicaciones

    usuario_asignado = Usuario.query.get(asignado_id)
    if not usuario_asignado:
        return jsonify({"success": False, "message": "El usuario asignado no es válido"}), 400

    for _, row in df.iterrows():
        codsolot = str(row['codsolot']).strip()
        codcli = str(row['codcli']).strip()
        hora = str(row['hora']).strip()
        nombre = str(row['nombre']).strip()
        nomcli = str(row['nomcli']).strip()
        direccion = str(row['direccion']).strip()
        distrito = str(row['distrito']).strip()
        plano = str(row['plano']).strip() if pd.notna(row['plano']) else None
        descripcion = str(row['descripcion']).strip() if pd.notna(row['descripcion']) else None
        telefono = str(row['telefono']).strip() if pd.notna(row['telefono']) else None
        tipo_ubicacion = "coordinada" if "COORDINADA" in str(row['tipo_visita']).upper() else "directa"
        referencia = str(row['referencia']).strip() if pd.notna(row['referencia']) else None
        operadora = str(row['operadora']).strip() if pd.notna(row['operadora']) else None

        print(f"Procesando: codsolot={codsolot}, direccion={direccion}, asignado_id={asignado_id}")

        # 🔹 Verificar si la ubicación ya existe para evitar duplicados
        existe = Ubicacion.query.filter_by(codsolot=codsolot).first()
        
        if not existe:
            print(f"Obteniendo coordenadas para: {direccion}")
            latitud, longitud = get_coordinates(direccion)

            if latitud is None or longitud is None:
                print(f"Saltando ubicación sin coordenadas: {direccion}")
                continue  

            nueva_ubicacion = Ubicacion(
                codcli=codcli,
                hora=hora,
                nombre=nombre,
                nomcli=nomcli,
                codsolot=codsolot,
                direccion=direccion,
                distrito=distrito,
                plano=plano,
                descripcion=descripcion,
                telefono=telefono,
                tipo_ubicacion=tipo_ubicacion,
                referencia=referencia,
                operadora=operadora,
                latitud=latitud,
                longitud=longitud,
                usuario_id=int(asignado_id)  # Se asigna directamente al usuario seleccionado
            )
            db.session.add(nueva_ubicacion)
            registros_guardados += 1

    db.session.commit()

    if registros_guardados > 0:
        return jsonify({"success": True, "message": f"Se guardaron {registros_guardados} ubicaciones correctamente"}), 200
    else:
        return jsonify({"success": False, "message": "No se guardaron ubicaciones"}), 200


# Gestión de ubicaciones
@routes.route('/ubicaciones', methods=['GET'])
@login_required
def listar_ubicaciones():
    user_id = session["user_id"]
    usuario_actual = Usuario.query.get(user_id)

    # Obtener usuario_id desde la URL para filtrar en el mapa
    usuario_id = request.args.get("usuario_id")

    if usuario_id:  
        # 🔹 Filtrar ubicaciones de un usuario específico (para el mapa)
        ubicaciones = Ubicacion.query.filter(Ubicacion.usuario_id == usuario_id, Ubicacion.estado == True).all()
    elif usuario_actual.rol_id == 1:  
        # 🔹 Si es administrador, ve todas las ubicaciones
        ubicaciones = Ubicacion.query.filter(Ubicacion.estado == True).all()
    else:
        # 🔹 Usuarios normales solo ven sus ubicaciones asignadas
        ubicaciones = Ubicacion.query.filter((Ubicacion.usuario_id == user_id) | (Ubicacion.asignado_id == user_id), Ubicacion.estado == True).all()
    
    data = []
    
    for ubicacion in ubicaciones:
        data.append({
            "id": ubicacion.id,
            "nombre": ubicacion.nombre or "No disponible",
            "codcli": ubicacion.codcli or "No disponible",
            "hora": ubicacion.hora or "No disponible",
            "nomcli": ubicacion.nomcli or "No disponible",
            "codsolot": ubicacion.codsolot or "No disponible",
            "direccion": ubicacion.direccion or "No disponible",
            "telefono": ubicacion.telefono or "No disponible",
            "tipo_ubicacion": ubicacion.tipo_ubicacion or "No disponible",
            "referencia": ubicacion.referencia or "No disponible",
            "latitud": float(ubicacion.latitud) if ubicacion.latitud else None,
            "longitud": float(ubicacion.longitud) if ubicacion.longitud else None,
        })
        

    return jsonify(data), 200




@routes.route('/usuarios', methods=['GET'])
@login_required
def listar_usuarios():
    usuarios = Usuario.query.filter_by(rol_id=2).all()  # Solo usuarios, excluyendo administradores
    return jsonify([
        {
            "id": u.id,
            "nombre": u.nombre,
            "usuario": u.usuario,
            "placa": getattr(u, "placa", None),
            "telefono": getattr(u, "telefono", None),
            "rol": u.rol_id,
            "activo": True  # Si tienes un campo activo/inactivo, úsalo aquí
        }
        for u in usuarios
    ])

@routes.route('/usuarios_tabla', methods=['GET'])
@login_required
def obtener_usuarios_tabla():
    usuarios = Usuario.query.all()
    usuarios_data = [{
        "id": usuario.id,
        "nombre": usuario.nombre,
        "usuario": usuario.usuario,
        "placa": usuario.placa if usuario.placa else "No disponible",
        "telefono": usuario.telefono if usuario.telefono else "No disponible",
        "rol": "Administrador" if usuario.rol_id == 1 else "Usuario",
        "activo": "Sí" if usuario.rol_id == 2 else "No"
    } for usuario in usuarios]

    return jsonify(usuarios_data), 200










@routes.route('/usuarios/agregar', methods=['POST'])
@login_required
def agregar_usuario():
    data = request.get_json()

    # Verificar si el usuario, email o teléfono ya existen
    if Usuario.query.filter_by(usuario=data["usuario"]).first():
        return jsonify({"success": False, "mensaje": "El nombre de usuario ya está en uso."}), 400

    if Usuario.query.filter_by(placa=data["placa"]).first():
        return jsonify({"success": False, "mensaje": "La placa ya está registrado."}), 400

    if Usuario.query.filter_by(telefono=data["telefono"]).first():
        return jsonify({"success": False, "mensaje": "El número de teléfono ya está registrado."}), 400

    nuevo_usuario = Usuario(
        nombre=data["nombre"],
        usuario=data["usuario"],
        placa=data["placa"],
        telefono=data["telefono"],
        contraseña=data["contraseña"],  # Asegúrate de usar hashing en producción
        rol_id=data["rol_id"],
        activo=True
    )

    db.session.add(nuevo_usuario)
    db.session.commit()

    return jsonify({"success": True, "mensaje": "Usuario agregado correctamente."}), 201



@routes.route('/usuarios/editar/<int:id>', methods=['PUT'])
@login_required
def editar_usuario(id):
    usuario = Usuario.query.get(id)
    if not usuario:
        return jsonify({"success": False, "message": "Usuario no encontrado."}), 404

    try:
        data = request.get_json()

        # Verificar que los campos existen en el JSON antes de acceder a ellos
        nombre = data.get("nombre", usuario.nombre)  # Si no está en la petición, usa el valor actual
        usuario_nuevo = data.get("usuario", usuario.usuario)
        placa = data.get("placa", usuario.placa)
        telefono = data.get("telefono", usuario.telefono)
        contraseña = data.get("contraseña", None)  # Puede ser None si el usuario no la cambia
        rol_id = data.get("rol_id", usuario.rol_id)

        # Evitar duplicados en usuario, email y teléfono
        if Usuario.query.filter(Usuario.usuario == usuario_nuevo, Usuario.id != id).first():
            return jsonify({"success": False, "message": "El nombre de usuario ya está en uso."}), 400
        if Usuario.query.filter(Usuario.placa == placa, Usuario.id != id).first():
            return jsonify({"success": False, "message": "La placa ya está registrado."}), 400
        if Usuario.query.filter(Usuario.telefono == telefono, Usuario.id != id).first():
            return jsonify({"success": False, "message": "El teléfono ya está registrado."}), 400

        # Actualizar los datos del usuario
        usuario.nombre = nombre
        usuario.usuario = usuario_nuevo
        usuario.placa = placa
        usuario.telefono = telefono
        usuario.rol_id = rol_id

        # Solo actualizar la contraseña si el usuario ingresó una nueva
        if contraseña:
            usuario.contraseña = contraseña  # Usa hashing en producción

        db.session.commit()
        return jsonify({"success": True, "message": "Usuario actualizado correctamente."}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Error al actualizar usuario.", "error": str(e)}), 500



@routes.route('/usuarios/eliminar/<int:id>', methods=['DELETE'])
@login_required
def eliminar_usuario(id):
    usuario = Usuario.query.get(id)

    if not usuario:
        return jsonify({"success": False, "message": "Usuario no encontrado."}), 404

    try:
        db.session.delete(usuario)
        db.session.commit()
        return jsonify({"success": True, "message": "Usuario eliminado correctamente."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Error al eliminar usuario.", "error": str(e)}), 500



@routes.route('/gestion_usuarios', methods=['GET'])
@login_required
def gestion_usuarios():
    return render_template('usuarios.html')









@routes.route('/ubicaciones/agregar', methods=['POST'])
@login_required
def agregar_ubicacion():
    data = request.json
    user_id = session["user_id"]

    nueva_ubicacion = Ubicacion(
        codsolot=data["codsolot"],
        nombre=data["nombre"],
        direccion=data["direccion"],
        latitud=data["latitud"],
        longitud=data["longitud"],
        tipo_ubicacion=data.get("tipo_ubicacion", "coordinada"),
        usuario_id=user_id
    )
    db.session.add(nueva_ubicacion)
    db.session.commit()
    return jsonify({"mensaje": "Ubicación agregada"}), 201

@routes.route('/ubicaciones/eliminar/<int:id>', methods=['DELETE'])
@login_required
def eliminar_ubicacion(id):
    ubicacion = Ubicacion.query.get(id)
    if ubicacion:
        db.session.delete(ubicacion)
        db.session.commit()
        return jsonify({"mensaje": "Ubicación eliminada"}), 200
    return jsonify({"error": "Ubicación no encontrada"}), 404

# Gestión de rutas
@routes.route('/rutas', methods=['GET'])
@login_required
def listar_rutas():
    user_id = session["user_id"]
    rutas = Ruta.query.filter((Ruta.asignado_id == user_id) | (Ruta.creador_id == user_id)).all()

    rutas_json = []
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")

    for r in rutas:
        fecha_asignacion = r.nombre_ruta.split(" - ")[0]  # Extraer la fecha de la ruta
        estado = "Asignada" if fecha_asignacion >= fecha_hoy else "Pendiente"  # Determinar estado
        todas_atendidas = True

        ubicaciones = []
        for ru in r.rutas_ubicaciones:
            ubicacion = ru.ubicacion
            atendida = not ubicacion.estado

            ubicaciones.append({
                "id": ubicacion.id,
                "latitud": ubicacion.latitud,
                "longitud": ubicacion.longitud,
                "direccion": ubicacion.direccion,
                "codcli": ubicacion.codcli,
                "hora": ubicacion.hora,
                "tipo_ubicacion": ubicacion.tipo_ubicacion,
                "nombre": ubicacion.nombre,
                "nomcli": ubicacion.nomcli,
                "codsolot": ubicacion.codsolot,
                "telefono": ubicacion.telefono,
                "referencia": ubicacion.referencia,
                "atendida": atendida
            })

            if not atendida:  # 🔹 Si hay alguna ubicación NO atendida, la ruta NO puede eliminarse
                todas_atendidas = False

        rutas_json.append({
            "id": r.id,
            "nombre_ruta": f"{fecha_asignacion} - {estado}",
            "asignado": r.usuario_asignado.nombre if r.usuario_asignado else "No asignado",
            "ubicaciones": ubicaciones,
            "todas_atendidas": todas_atendidas
        })

    return jsonify(rutas_json)

@routes.route('/rutas/agregar', methods=['POST'])
@login_required
def agregar_ruta():
    data = request.json

    # Validar que inicio y fin existen en el request
    inicio = data.get("inicio")
    fin = data.get("fin")
    ubicaciones = data.get("ubicaciones", [])

    if not inicio or not fin:
        return jsonify({"mensaje": "Debes seleccionar un punto de inicio y un punto de fin."}), 400

    user_id = session["user_id"]
    usuario_asignado_id = data.get("usuario_asignado")

    usuario_asignado = Usuario.query.filter_by(id=usuario_asignado_id, rol_id=2).first()
    if not usuario_asignado:
        return jsonify({"mensaje": "El usuario asignado no es válido."}), 400

    fecha_actual = datetime.now().strftime("%Y-%m-%d")
    nombre_ruta = f"{fecha_actual} - {usuario_asignado.nombre}"

    nueva_ruta = Ruta(
        nombre_ruta=nombre_ruta,
        creador_id=user_id,
        asignado_id=usuario_asignado_id
    )
    db.session.add(nueva_ruta)
    db.session.commit()

    # Agregar inicio, paradas intermedias y fin
    ubicaciones_seleccionadas = [inicio] + ubicaciones + [fin]

    for i, ubicacion_id in enumerate(ubicaciones_seleccionadas):
        nueva_asignacion = RutaUbicacion(
            ruta_id=nueva_ruta.id,
            ubicacion_id=ubicacion_id,
            orden=i
        )
        db.session.add(nueva_asignacion)

    db.session.commit()
    return jsonify({"mensaje": "Ruta agregada correctamente", "nombre_ruta": nombre_ruta}), 201

@routes.route('/rutas/generar', methods=['POST'])
@login_required
def generar_ruta():
    data = request.json
    inicio_id = data["inicio"]
    fin_id = data["fin"]
    user_id = session["user_id"]

    # Obtener ubicaciones coordinadas y ordenarlas por proximidad al inicio
    ubicaciones_coordinadas = Ubicacion.query.filter_by(usuario_id=user_id, tipo_ubicacion="coordinada").all()
    ubicaciones_coordinadas = sorted(ubicaciones_coordinadas, key=lambda u: (
        abs(u.latitud - Ubicacion.query.get(inicio_id).latitud) + abs(u.longitud - Ubicacion.query.get(inicio_id).longitud)
    ))

    nueva_ruta = Ruta(nombre_ruta=f"Ruta de {inicio_id} a {fin_id}", usuario_id=user_id)
    db.session.add(nueva_ruta)
    db.session.commit()

    # Agregar ubicaciones coordinadas primero
    for i, ubicacion in enumerate(ubicaciones_coordinadas):
        nueva_asignacion = RutaUbicacion(
            ruta_id=nueva_ruta.id,
            ubicacion_id=ubicacion.id,
            orden=i
        )
        db.session.add(nueva_asignacion)

    # Obtener ubicaciones directas y agregar las que están cerca de la ruta
    ubicaciones_directas = Ubicacion.query.filter_by(usuario_id=user_id, tipo_ubicacion="directa").all()
    for ubicacion in ubicaciones_directas:
        for ru in nueva_ruta.rutas_ubicaciones:
            distancia = abs(ubicacion.latitud - ru.ubicacion.latitud) + abs(ubicacion.longitud - ru.ubicacion.longitud)
            if distancia < 0.01:  # Definir qué tan cerca debe estar (ajustar según necesidad)
                nueva_asignacion = RutaUbicacion(
                    ruta_id=nueva_ruta.id,
                    ubicacion_id=ubicacion.id,
                    orden=len(nueva_ruta.rutas_ubicaciones)
                )
                db.session.add(nueva_asignacion)

    db.session.commit()
    return jsonify({"mensaje": "Ruta generada correctamente"}), 201

@routes.route('/rutas/editar_asignado/<int:ruta_id>', methods=['PUT'])
@login_required
def editar_usuario_asignado(ruta_id):
    data = request.get_json()
    nuevo_usuario_id = data.get("nuevo_usuario_id")

    ruta = Ruta.query.get(ruta_id)
    if not ruta:
        return jsonify({"success": False, "message": "Ruta no encontrada."}), 404

    usuario_nuevo = Usuario.query.get(nuevo_usuario_id)
    if not usuario_nuevo:
        return jsonify({"success": False, "message": "Usuario no encontrado."}), 404

    ruta.asignado_id = nuevo_usuario_id
    ruta.nombre_ruta = f"{ruta.fecha_creacion} - {usuario_nuevo.nombre}"  # **Actualizar nombre**

    try:
        db.session.commit()
        return jsonify({"success": True, "message": "Usuario asignado actualizado correctamente."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "Error al actualizar usuario.", "error": str(e)}), 500



@routes.route('/rutas/eliminar/<int:id>', methods=['DELETE'])
@login_required
def eliminar_ruta(id):
    ruta = Ruta.query.get(id)
    
    if not ruta:
        return jsonify({"error": "Ruta no encontrada"}), 404

    # Obtener todas las ubicaciones asociadas a la ruta
    ubicaciones_asociadas = [ru.ubicacion for ru in ruta.rutas_ubicaciones]

    # Cambiar estado de las ubicaciones a "Revisada"
    for ubicacion in ubicaciones_asociadas:
        ubicacion.estado = False  # False significa "Revisada"

    # Eliminar asignaciones de ubicaciones a la ruta
    RutaUbicacion.query.filter_by(ruta_id=id).delete()

    # Eliminar la ruta
    db.session.delete(ruta)
    db.session.commit()

    return jsonify({"mensaje": "Ruta eliminada y ubicaciones movidas a Revisadas"}), 200

@routes.route('/rutas/cancelar/<int:id>', methods=['DELETE'])
@login_required
def cancelar_ruta(id):
    ruta = Ruta.query.get(id)

    if not ruta:
        return jsonify({"success": False, "mensaje": "Ruta no encontrada"}), 404

    try:
        # Solo eliminar la ruta sin cambiar el estado de las ubicaciones
        db.session.delete(ruta)
        db.session.commit()

        return jsonify({"success": True, "mensaje": "Ruta cancelada correctamente."}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "mensaje": "Error al cancelar ruta.", "error": str(e)}), 500







@routes.route("/todas_ubicaciones", methods=["GET"])
def listar_todas_ubicaciones():
    ubicaciones = Ubicacion.query.all()
    return jsonify([
        {
            "id": u.id,
            "latitud": u.latitud,
            "longitud": u.longitud,
            "direccion": u.direccion,
            "codcli": u.codcli,
            "hora": u.hora,
            "tipo_ubicacion": u.tipo_ubicacion,
            "nombre": u.nombre,
            "nomcli": u.nomcli,
            "codsolot": u.codsolot,
            "telefono": u.telefono,
            "referencia": u.referencia,
            "estado": u.estado if u.estado is not None else True,  # 🔹 Evita errores con None
            "descripcion": u.descripcion  # 🔹 Asegura que el comentario se muestre en la tabla de revisadas
        }
        for u in ubicaciones
    ])



@routes.route("/ubicaciones/revisar/<int:id>", methods=["POST"])
def marcar_ubicacion_revisada(id):
    ubicacion = Ubicacion.query.get(id)
    if not ubicacion:
        return jsonify({"mensaje": "Ubicación no encontrada"}), 404

    data = request.get_json()
    comentario = data.get("comentario", "")

    # 🔹 Cambia el estado a 'False' para marcarla como revisada
    ubicacion.estado = False
    ubicacion.descripcion = comentario  # Guardamos el comentario de revisión

    db.session.commit()
    return jsonify({"mensaje": "Ubicación marcada como revisada"})


@routes.route('/restaurar_ubicacion/<int:ubicacion_id>', methods=['POST'])
@login_required
def restaurar_ubicacion_revisada(ubicacion_id):
    ubicacion = Ubicacion.query.get(ubicacion_id)
    if not ubicacion:
        return jsonify({"mensaje": "Ubicación no encontrada."}), 404

    # Buscar y eliminar la entrada de UbicacionAtendida
    atencion = UbicacionAtendida.query.filter_by(ubicacion_id=ubicacion_id).first()
    if atencion:
        db.session.delete(atencion)

    # Restaurar el estado de la ubicación a activa
    ubicacion.estado = True
    db.session.commit()

    return jsonify({"mensaje": "Ubicación restaurada correctamente y eliminada de las atendidas."})


@routes.route('/eliminar_ubicacion/<int:ubicacion_id>', methods=['DELETE'])
def eliminar_ubicacion_definitiva(ubicacion_id):
    ubicacion = Ubicacion.query.get_or_404(ubicacion_id)
    db.session.delete(ubicacion)
    db.session.commit()
    return jsonify({"mensaje": "Ubicación eliminada correctamente."})

@routes.route('/listado_ubicaciones', methods=['GET'])
def listado_ubicaciones():
    return render_template('listado_ubicaciones.html')




@routes.route("/ubicaciones_activas", methods=["GET"])
def listar_ubicaciones_activas():
    ubicaciones = Ubicacion.query.filter_by(estado=True).all()
    return jsonify([
        {
            "id": u.id,
            "latitud": u.latitud,
            "longitud": u.longitud,
            "direccion": u.direccion,
            "codcli": u.codcli,
            "hora": u.hora,
            "tipo_ubicacion": u.tipo_ubicacion,
            "nombre": u.nombre,
            "nomcli": u.nomcli,
            "codsolot": u.codsolot,
            "telefono": u.telefono,
            "referencia": u.referencia,
            "estado": u.estado  # 🔹 Se incluye el estado en la respuesta
        }
        for u in ubicaciones
    ])

@routes.route("/ubicaciones_atendidas", methods=["GET"])
@login_required
def listar_ubicaciones_atendidas():
    atenciones = UbicacionAtendida.query.all()

    data = []
    for atencion in atenciones:
        data.append({
            "id": atencion.ubicacion.id,
            "codsolot": atencion.ubicacion.codsolot,
            "direccion": atencion.ubicacion.direccion,
            "atendido_por": atencion.usuario.nombre,
            "fecha_hora_atencion": atencion.fecha_hora_atencion.strftime("%Y-%m-%d %H:%M:%S"),
            "tipo_atencion": atencion.tipo_atencion,
            "comentario": atencion.comentario or "Sin comentario"
        })

    return jsonify(data), 200

@routes.route("/ubicaciones/atender/<int:id>", methods=["POST"])
@login_required
def marcar_ubicacion_atendida(id):
    ubicacion = Ubicacion.query.get(id)
    if not ubicacion:
        return jsonify({"mensaje": "Ubicación no encontrada"}), 404

    data = request.get_json()
    comentario = data.get("comentario", "").strip()
    tipo_atencion = str(data.get("tipo_atencion", "Efectiva")).strip()  # Convertirlo en texto

    usuario_actual = session.get("user_id")  
    if not usuario_actual:
        return jsonify({"mensaje": "Error: Usuario no autenticado"}), 401

    # Guardar en la tabla UbicacionAtendida con el tipo de atención como texto
    atencion = UbicacionAtendida(
        ubicacion_id=id,
        atendido_por=usuario_actual,
        fecha_hora_atencion=datetime.utcnow(),
        tipo_atencion=tipo_atencion,  # Asegurar que sea un string
        comentario=comentario
    )
    db.session.add(atencion)

    # Desactivar la ubicación en la tabla Ubicaciones
    ubicacion.estado = False
    db.session.commit()

    return jsonify({"mensaje": f"Ubicación marcada como '{tipo_atencion}' por el usuario {usuario_actual}"}), 200


@routes.route("/usuarios/lista", methods=["GET"])
@login_required
def obtener_usuarios():
    usuarios = Usuario.query.filter_by(activo=True).all()
    
    data = [{"id": usuario.id, "nombre": usuario.nombre} for usuario in usuarios]

    return jsonify(data), 200


@routes.route("/ubicaciones_filtradas", methods=["GET"])
@login_required
def ubicaciones_filtradas():
    usuario_id = request.args.get("usuario_id")
    
    if not usuario_id:
        return jsonify({"error": "Usuario no especificado"}), 400
    
    ubicaciones = Ubicacion.query.filter_by(usuario_id=usuario_id, estado=True).all()
    
    data = [{
        "id": ubicacion.id,
        "nombre": ubicacion.nombre or "No disponible",
        "direccion": ubicacion.direccion or "No disponible",
        "latitud": ubicacion.latitud,
        "longitud": ubicacion.longitud
    } for ubicacion in ubicaciones]

    return jsonify(data), 200


@routes.route('/exportar_ubicaciones', methods=['GET'])
@login_required
def exportar_ubicaciones():
    """Exporta las ubicaciones activas y atendidas a un archivo Excel"""

    # 🔹 Consultar ubicaciones activas
    ubicaciones_activas = Ubicacion.query.filter_by(estado=True).all()

    data_activas = [{
        "ID": u.id,
        "CodCliente": u.codcli,
        "Hora": u.hora,
        "Nombre Cliente": u.nomcli,
        "SOT": u.codsolot,
        "Dirección": u.direccion,
        "Teléfono": u.telefono,
        "Tipo Visita": u.tipo_ubicacion,
        "Referencia": u.referencia,
        "Latitud": u.latitud,
        "Longitud": u.longitud,
        "Usuario Asignado": Usuario.query.get(u.usuario_id).nombre if u.usuario_id else "N/A"
    } for u in ubicaciones_activas]

    # 🔹 Consultar ubicaciones atendidas
    ubicaciones_atendidas = UbicacionAtendida.query.all()

    data_atendidas = [{
        "ID": ua.id,
        "CodCliente": ua.ubicacion.codcli,
        "Hora": ua.ubicacion.hora,
        "Nombre Cliente": ua.ubicacion.nomcli,
        "SOT": ua.ubicacion.codsolot,
        "Dirección": ua.ubicacion.direccion,
        "Teléfono": ua.ubicacion.telefono,
        "Tipo Visita": ua.ubicacion.tipo_ubicacion,
        "Referencia": ua.ubicacion.referencia,
        "Latitud": ua.ubicacion.latitud,
        "Longitud": ua.ubicacion.longitud,
        "Atendido Por": Usuario.query.get(ua.atendido_por).nombre if ua.atendido_por else "N/A",
        "Fecha Atención": ua.fecha_hora_atencion.strftime("%Y-%m-%d %H:%M:%S"),
        "Tipo Atención": ua.tipo_atencion,
        "Comentario": ua.comentario
    } for ua in ubicaciones_atendidas]

    # 🔹 Convertir los datos en DataFrames de Pandas
    df_activas = pd.DataFrame(data_activas)
    df_atendidas = pd.DataFrame(data_atendidas)

    # 🔹 Crear un archivo Excel con ambas hojas
    excel_filename = "Ubicaciones.xlsx"
    excel_path = os.path.join("uploads", excel_filename)

    with pd.ExcelWriter(excel_path, engine="xlsxwriter") as writer:
        df_activas.to_excel(writer, sheet_name="Ubicaciones Activas", index=False)
        df_atendidas.to_excel(writer, sheet_name="Ubicaciones Atendidas", index=False)

    # 🔹 Descargar el archivo
    return send_file(excel_path, as_attachment=True, download_name=excel_filename)