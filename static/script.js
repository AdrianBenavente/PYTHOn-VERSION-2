const icon = document.getElementById("main-icon");
const barraLateral = document.querySelector(".barra-lateral");
const menu = document.querySelector(".menu");
const main = document.querySelector("main");
const logout = document.getElementById("boton-nav");

logout.addEventListener("click", () => {
    window.location.href = "/";
});

menu.addEventListener("click", () => {
    barraLateral.classList.toggle("max-barra-lateral");
});

icon.addEventListener("click", () => {
    barraLateral.classList.toggle("mini-barra-lateral");
    main.classList.toggle("min-main");
});

let map;
let directionsService;
let directionsRenderer;
let infoWindow;  // Solo se permitirá una abierta a la vez

function initMap() {
    map = new google.maps.Map(document.getElementById("map"), {
        center: { lat: -12.0464, lng: -77.0428 },
        zoom: 12
    });

    directionsService = new google.maps.DirectionsService();
    directionsRenderer = new google.maps.DirectionsRenderer({ suppressMarkers: false });
    directionsRenderer.setMap(map);

    infoWindow = new google.maps.InfoWindow(); // Para asegurar una sola ventana abierta
    cargarUbicaciones();
    mostrarRutasEnMapa();
}

// 🔹 Cargar ubicaciones en los select y mapa con información detallada
function cargarUbicaciones() {
    fetch("/ubicaciones")
        .then(response => response.json())
        .then(ubicaciones => {
            ubicaciones.forEach(ubicacion => {
                if (!ubicacion.latitud || !ubicacion.longitud) {
                    console.warn("Ubicación sin coordenadas:", ubicacion);
                    return;
                }

                // Cambiar el ícono según el tipo de ubicación
                var color = ubicacion.tipo_ubicacion.toLowerCase() === "coordinada"
                    ? "http://maps.google.com/mapfiles/ms/icons/green-dot.png"
                    : "http://maps.google.com/mapfiles/ms/icons/red-dot.png";

                var marker = new google.maps.Marker({
                    position: { lat: parseFloat(ubicacion.latitud), lng: parseFloat(ubicacion.longitud) },
                    map: map,
                    title: ubicacion.nombre,
                    icon: color
                });

                var infoWindow = new google.maps.InfoWindow({
                    content: `
                        <b>CodCliente:</b> ${ubicacion.codcli || "No disponible"}<br>
                        <b>Hora:</b> ${ubicacion.hora || "No disponible"}<br>
                        <b>Nombre Cliente:</b> ${ubicacion.nomcli || "No disponible"}<br>
                        <b>CodSolot:</b> ${ubicacion.codsolot || "No disponible"}<br>
                        <b>Dirección:</b> ${ubicacion.direccion || "No disponible"}<br>
                        <b>Teléfono:</b> ${ubicacion.telefono || "No disponible"}<br>
                        <b>Tipo Visita:</b> ${ubicacion.tipo_ubicacion || "No disponible"}<br>
                        <b>Referencia:</b> ${ubicacion.referencia || "No disponible"}<br>
                        <button onclick="marcarComoRevisado(${ubicacion.id})">Marcar como Revisado</button>
                    `
                });

                marker.addListener("click", function () {
                    if (infoWindowActual) {
                        infoWindowActual.close();
                    }
                    infoWindowActual = infoWindow;
                    infoWindow.open(map, marker);
                });
            });
        })
        .catch(error => console.error("Error cargando ubicaciones:", error));
}

// 🔹 Mostrar TODAS las rutas guardadas en el mapa
function mostrarRutasEnMapa() {
    fetch("/rutas")
        .then(response => response.json())
        .then(data => {
            let rutasContainer = document.getElementById("rutasGuardadas");
            rutasContainer.innerHTML = ""; // 🔹 Limpiar contenido previo

            data.forEach(ruta => {
                let rutaDiv = document.createElement("div");
                rutaDiv.classList.add("ruta-item");

                let rutaNombre = document.createElement("p");
                rutaNombre.innerText = `Ruta: ${ruta.nombre_ruta} (Creador: ${ruta.creador})`;

                let btnMostrar = document.createElement("button");
                btnMostrar.innerText = "Mostrar Ruta";
                btnMostrar.onclick = () => trazarRutaEnMapa(ruta);

                let btnEliminar = document.createElement("button");
                btnEliminar.innerText = "Eliminar Ruta";
                btnEliminar.onclick = () => eliminarRuta(ruta.id);

                //let btnDetalles = document.createElement("button");
                //btnDetalles.innerText = "Ver Detalles de la Ruta";
                //btnDetalles.onclick = () => mostrarDetallesRuta(ruta);

                rutaDiv.appendChild(rutaNombre);
                rutaDiv.appendChild(btnMostrar);
                rutaDiv.appendChild(btnEliminar);
                //rutaDiv.appendChild(btnDetalles);

                rutasContainer.appendChild(rutaDiv);
            });
        })
        .catch(error => console.error("Error cargando rutas:", error));
}

function mostrarDetallesRuta(ruta) {
    let detallesContainer = document.getElementById("detalles-ruta");
    detallesContainer.innerHTML = ""; // Limpiar detalles previos

    let titulo = document.createElement("h3");
    titulo.innerText = `Detalles de la Ruta: ${ruta.nombre_ruta}`;
    detallesContainer.appendChild(titulo);

    let lista = document.createElement("ul");

    ruta.ubicaciones.forEach(ubicacion => {
        let item = document.createElement("li");
        item.innerHTML = `<b>Dirección:</b> ${ubicacion.direccion && ubicacion.direccion !== "No disponible" ? ubicacion.direccion : "No registrada"} 
                          <br><b>CodCliente:</b> ${ubicacion.codcli ? ubicacion.codcli : "No disponible"} 
                          <br><b>Hora:</b> ${ubicacion.hora ? ubicacion.hora : "No disponible"} 
                          <br><b>Telefono del cliente:</b> ${ubicacion.telefono ? ubicacion.telefono : "No disponible"}
                          <br><b>Tipo Visita:</b> ${ubicacion.tipo_ubicacion ? ubicacion.tipo_ubicacion : "No disponible"}`;
                          
        lista.appendChild(item);
    });

    detallesContainer.appendChild(lista);
}

// 🔹 Dibujar rutas en el mapa
function dibujarRutaEnMapa(ubicaciones) {
    console.log("Dibujando ruta en mapa:", ubicaciones);

    if (!ubicaciones || ubicaciones.length < 2) {
        console.error("No hay suficientes ubicaciones para trazar la ruta.");
        return;
    }

    let waypoints = ubicaciones.slice(1, -1).map(ubicacion => ({
        location: new google.maps.LatLng(ubicacion.latitud, ubicacion.longitud),
        stopover: true
    }));

    let request = {
        origin: new google.maps.LatLng(ubicaciones[0].latitud, ubicaciones[0].longitud),
        destination: new google.maps.LatLng(ubicaciones[ubicaciones.length - 1].latitud, ubicaciones[ubicaciones.length - 1].longitud),
        waypoints: waypoints,
        travelMode: google.maps.TravelMode.DRIVING
    };

    directionsService.route(request, function (response, status) {
        if (status === google.maps.DirectionsStatus.OK) {
            console.log("Ruta generada correctamente:", response);
            directionsRenderer.setDirections(response);
        } else {
            console.error("Error al obtener la ruta:", status);
        }
    });
}

function calcularRuta() {
    let inicioSelect = document.getElementById("inicio");
    let finSelect = document.getElementById("fin");
    let usuarioAsignadoSelect = document.getElementById("usuarioAsignado");

    let inicio = inicioSelect.value;
    let fin = finSelect.value;
    let usuarioAsignado = usuarioAsignadoSelect.value;

    let nombreUsuario = usuarioAsignadoSelect.options[usuarioAsignadoSelect.selectedIndex].text;
    let fechaHoy = new Date().toISOString().split("T")[0]; // Formato YYYY-MM-DD

    if (inicio === "" || fin === "" || usuarioAsignado === "") {
        alert("Debes seleccionar inicio, fin y usuario asignado.");
        return;
    }

    let ruta = {
        nombre_ruta: `${fechaHoy} - ${nombreUsuario}`,
        inicio: inicio,
        fin: fin,
        ubicaciones: paradas,
        usuario_asignado: usuarioAsignado
    };

    fetch("/rutas/agregar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(ruta)
    })
    .then(response => response.json())
    .then(result => {
        alert(result.mensaje);
        location.reload();
    })
    .catch(error => console.error("Error al guardar la ruta:", error));
}


// 🔹 Eliminar ruta y recargar el mapa
function eliminarRuta(rutaId) {
    fetch(`/rutas/eliminar/${rutaId}`, { method: "DELETE" })
        .then(response => response.json())
        .then(data => {
            console.log(data.mensaje);
            directionsRenderer.setDirections({ routes: [] }); // 🔹 Borra la ruta actual
            mostrarRutasEnMapa(); // 🔹 Recargar rutas después de eliminar
        })
        .catch(error => console.error("Error al eliminar la ruta:", error));
}

function mostrarUbicacionesRuta(ruta) {
    let detallesContainer = document.getElementById("detalles-ruta");
    detallesContainer.innerHTML = ""; // 🔹 Limpiar contenido previo

    if (!ruta.ubicaciones || ruta.ubicaciones.length === 0) {
        detallesContainer.innerHTML = "<p>No hay ubicaciones en esta ruta.</p>";
        return;
    }

    let rutaDiv = document.createElement("div");
    rutaDiv.classList.add("detalle-ruta-item");

    let tituloRuta = document.createElement("h3");
    tituloRuta.innerText = `Ruta: ${ruta.nombre_ruta}`;

    let listaUbicaciones = document.createElement("ul");

    ruta.ubicaciones.forEach(ubicacion => {
        let li = document.createElement("li");
        li.innerHTML = `<b>Dirección:</b> ${ubicacion.direccion || "No disponible"}<br>
                        <b>CodCliente:</b> ${ubicacion.codcli || "No disponible"}<br>
                        <b>Hora:</b> ${ubicacion.hora || "No disponible"}<br>
                        <b>Nombre Cliente:</b> ${ubicacion.nomcli || "No disponible"}<br>
                        <b>Tipo Visita:</b> ${ubicacion.tipo_ubicacion || "No disponible"}`;
        listaUbicaciones.appendChild(li);
    });

    rutaDiv.appendChild(tituloRuta);
    rutaDiv.appendChild(listaUbicaciones);
    detallesContainer.appendChild(rutaDiv);
}

function trazarRutaEnMapa(ruta) {
    if (!ruta.ubicaciones || ruta.ubicaciones.length < 2) {
        alert("Se necesitan al menos 2 ubicaciones para trazar la ruta.");
        return;
    }

    // Limpiar cualquier ruta anterior
    if (directionsRenderer) {
        directionsRenderer.setMap(null);
    }

    directionsRenderer = new google.maps.DirectionsRenderer({ map: map });

    let waypoints = ruta.ubicaciones.slice(1, -1).map(ubicacion => ({
        location: new google.maps.LatLng(ubicacion.latitud, ubicacion.longitud),
        stopover: true
    }));

    let request = {
        origin: new google.maps.LatLng(ruta.ubicaciones[0].latitud, ruta.ubicaciones[0].longitud),
        destination: new google.maps.LatLng(ruta.ubicaciones[ruta.ubicaciones.length - 1].latitud, ruta.ubicaciones[ruta.ubicaciones.length - 1].longitud),
        waypoints: waypoints,
        travelMode: google.maps.TravelMode.DRIVING
    };

    directionsService.route(request, function (response, status) {
        if (status === google.maps.DirectionsStatus.OK) {
            directionsRenderer.setDirections(response);
        } else {
            console.error("Error al trazar la ruta:", status);
            alert("No se pudo calcular la ruta: " + status);
        }
    });

    // Mostrar detalles de la ruta
    mostrarDetallesRuta(ruta);
}



// 🔹 Cargar Ubicaciones en la Tabla (activas y revisadas)
// 🔹 Cargar Ubicaciones en la Tabla
function cargarListadoUbicaciones() {
    fetch("/ubicaciones_activas")
        .then(response => response.json())
        .then(data => {
            let activas = document.getElementById("tablaActivas");
            activas.innerHTML = "";

            data.forEach(ubicacion => {
                let fila = document.createElement("tr");
                fila.innerHTML = `
                    <td>${ubicacion.codsolot}</td>
                    <td>${ubicacion.direccion || "No disponible"}</td>
                    <td>Asignado</td>
                    <button onclick="marcarComoAtendido(${ubicacion.id}, 'efectiva')">Atendido Efectivo</button>
                    <button onclick="marcarComoAtendido(${ubicacion.id}, 'no efectiva')">Atendido No Efectivo</button>
                `;
                activas.appendChild(fila);
            });
        })
        .catch(error => console.error("Error cargando ubicaciones activas:", error));
    
        fetch("/ubicaciones_atendidas")
        .then(response => response.json())
        .then(data => {
            let atendidas = document.getElementById("tablaAtendidas");
            atendidas.innerHTML = "";

            data.forEach(ubicacion => {
                let fila = document.createElement("tr");
                fila.innerHTML = `
                    <td>${ubicacion.codsolot}</td>
                    <td>${ubicacion.direccion || "No disponible"}</td>
                    <td>${ubicacion.atendido_por}</td>
                    <td>${ubicacion.fecha_hora_atencion}</td>
                    <td>${ubicacion.tipo_atencion}</td>
                    <td>${ubicacion.comentario || "Sin comentario"}</td>
                    <td>
                        <button onclick="restaurarUbicacionRevisada(${ubicacion.id})">Restaurar</button>
                    </td>
                `;
                atendidas.appendChild(fila);
            });
        })
        .catch(error => console.error("Error cargando ubicaciones atendidas:", error));
   
}



// 🔹 Marcar Ubicación como Revisada
function marcarComoRevisado(ubicacionId) {
    let comentario = prompt("Ingrese un comentario para la revisión:");

    if (comentario === null || comentario.trim() === "") {
        alert("Debe ingresar un comentario.");
        return;
    }

    fetch(`/ubicaciones/revisar/${ubicacionId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comentario: comentario })
    })
    .then(response => response.json())
    .then(data => {
        alert(data.mensaje);
        cargarListadoUbicaciones();  // 🔹 Ahora actualiza la tabla
        location.reload(); // 🔹 Y recarga el mapa
    })
    .catch(error => console.error("Error al marcar como revisado:", error));
}

function marcarComoAtendido(ubicacionId, tipoAtencion) {
    let comentario = prompt("Ingrese un comentario sobre la atención:");

    if (!comentario || comentario.trim() === "") {
        alert("Debe ingresar un comentario para validar la atención.");
        return;
    }

    fetch(`/ubicaciones/atender/${ubicacionId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tipo_atencion: tipoAtencion, comentario: comentario })
    })
    .then(response => response.json())
    .then(data => {
        alert(data.mensaje);
        location.reload();
    })
    .catch(error => console.error("Error al marcar como atendido:", error));
}



function restaurarUbicacionRevisada(id) {
    fetch(`/restaurar_ubicacion/${id}`, { method: "POST" })
        .then(response => response.json())
        .then(result => {
            alert(result.mensaje);
            cargarListadoUbicaciones();
        })
        .catch(error => console.error("Error al restaurar la ubicación:", error));
}

function eliminarUbicacionDefinitiva(id) {
    if (!confirm("¿Seguro que deseas eliminar esta ubicación?")) return;

    fetch(`/eliminar_ubicacion/${id}`, { method: "DELETE" })
        .then(response => response.json())
        .then(result => {
            alert(result.mensaje);
            cargarListadoUbicaciones();
        })
        .catch(error => console.error("Error al eliminar la ubicación:", error));
}

function buscarUbicacion() {
    let filtro = document.getElementById("buscador").value.toLowerCase();
    let filas = document.querySelectorAll("tbody tr");

    filas.forEach(fila => {
        let codsolot = fila.cells[0].textContent.toLowerCase();
        fila.style.display = codsolot.includes(filtro) ? "" : "none";
    });
}




// 🔹 Marcar Ubicación como Revisada
function marcarUbicacionRevisada(id) {
    let comentario = prompt("Ingrese una descripción para marcar como revisado:");
    if (!comentario) {
        alert("Debe ingresar una descripción.");
        return;
    }

    fetch(`/ubicaciones/revisar/${id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comentario })
    })
    .then(response => response.json())
    .then(result => {
        alert(result.mensaje);
        cargarListadoUbicaciones();  // 🔹 Recargar la lista después de actualizar
    })
    .catch(error => console.error("Error al marcar como revisado:", error));
}



function inicializarSelectsBusqueda() {
    // Aplica Select2 para búsqueda en los selects sin afectar su funcionalidad previa
    ["#inicio", "#fin", "#paradas"].forEach(id => {
        $(id).select2({
            placeholder: "Escribe para buscar...",
            allowClear: true
        });
    });
}







function cargarUsuarios() {
    fetch("/usuarios_tabla")
        .then(response => response.json())
        .then(data => {
            let usuariosTabla = document.getElementById("tablaUsuarios");
            usuariosTabla.innerHTML = ""; 

            data.forEach(usuario => {
                let fila = document.createElement("tr");
                fila.innerHTML = `
                    <td>${usuario.nombre}</td>
                    <td>${usuario.usuario}</td>
                    <td>${usuario.placa || "No disponible"}</td>  
                    <td>${usuario.telefono || "No disponible"}</td>  
                    <td>${usuario.rol}</td>
                    <td>${usuario.activo}</td>
                    <td>
                        <button onclick="editarUsuario(${usuario.id}, '${usuario.nombre}', '${usuario.usuario}', '${usuario.placa || ''}', '${usuario.telefono || ''}', '${usuario.rol}')">Editar</button>
                        <button onclick="eliminarUsuario(${usuario.id})">Eliminar</button>
                    </td>
                `;
                usuariosTabla.appendChild(fila);
            });
        })
        .catch(error => console.error("Error cargando usuarios:", error));
}


function guardarUsuario() {
    let nombre = document.getElementById("nombre").value.trim();
    let usuario = document.getElementById("usuario").value.trim();
    let placa = document.getElementById("placa").value.trim();  // 🛠 Corregido aquí
    let telefono = document.getElementById("telefono").value.trim();
    let contraseña = document.getElementById("contraseña").value.trim();
    let rol_id = document.getElementById("rol").value;

    if (!nombre || !usuario || !placa || !telefono || !contraseña || !rol_id) {
        alert("Todos los campos son obligatorios.");
        return;
    }

    // Validar formato de email
    let placaRegex = /^[A-Z]{2,3}-\d{2,4}$/;
    if (!placaRegex.test(placa)) {
        alert("Por favor, ingresa un correo electrónico válido.");
        return;
    }

    fetch("/usuarios/agregar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nombre, usuario, placa, telefono, contraseña, rol_id })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.mensaje);
            cargarUsuarios();
            setTimeout(() => location.reload(), 500); // Pequeña espera antes de recargar
        } else {
            alert(data.mensaje);
        }
    })
    .catch(error => console.error("Error guardando usuario:", error));
}



function eliminarUsuario(id) {
    if (!confirm("¿Estás seguro de que deseas eliminar este usuario?")) return;

    fetch(`/usuarios/eliminar/${id}`, {
        method: "DELETE"
    })
    .then(response => response.json())
    .then(result => {
        alert(result.message);
        cargarUsuarios(); // 🔹 Recargar la tabla después de eliminar
    })
    .catch(error => console.error("Error al eliminar usuario:", error));
}

function editarUsuario(id, nombre, usuario, placa, telefono, rol) {
    document.getElementById("nombre").value = nombre || "";
    document.getElementById("usuario").value = usuario || "";
    document.getElementById("placa").value = placa || "";
    document.getElementById("telefono").value = telefono || "";
    document.getElementById("contraseña").value = "";
    document.getElementById("rol").value = (rol === "Administrador") ? 1 : 2;

    let botonGuardar = document.querySelector("button[onclick='guardarUsuario()']");
    botonGuardar.textContent = "Actualizar Usuario";
    botonGuardar.setAttribute("onclick", `actualizarUsuario(${id})`);
}


function actualizarUsuario(id) {
    let nombre = document.getElementById("nombre").value.trim();
    let usuario = document.getElementById("usuario").value.trim();
    let placa = document.getElementById("placa").value.trim();
    let telefono = document.getElementById("telefono").value.trim();
    let contraseña = document.getElementById("contraseña").value.trim();
    let rol_id = document.getElementById("rol").value;

    if (!nombre || !usuario || !placa || !telefono || !rol_id) {
        alert("Todos los campos son obligatorios, excepto la contraseña.");
        return;
    }

    // Validar formato de email
    let placaRegex = /^[A-Z]{2,3}-\d{2,4}$/;
    if (!placaRegex.test(placa)) {
        alert("Por favor, ingresa un correo electrónico válido.");
        return;
    }

    // Validar teléfono
    let telefonoRegex = /^[0-9]{7,15}$/;
    if (!telefonoRegex.test(telefono)) {
        alert("El número de teléfono debe contener entre 7 y 15 dígitos numéricos.");
        return;
    }

    let datos = { nombre, usuario, placa, telefono, rol_id };
    if (contraseña) {
        datos.contraseña = contraseña;
    }

    fetch(`/usuarios/editar/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(datos)
    })
    .then(response => response.json())
    .then(result => {
        alert(result.message);
        cargarUsuarios();
        setTimeout(() => location.reload(), 500);
    })
    .catch(error => console.error("Error al editar usuario:", error));
}





// ⏩ Cargar ubicaciones y rutas al cargar la página
document.addEventListener("DOMContentLoaded", () => {
    initMap();
    cargarListadoUbicaciones();
    cargarUsuarios();
    setTimeout(() => {
        mostrarRutasEnMapa();
        inicializarSelectsBusqueda();
    }, 500); // Se da un pequeño tiempo para asegurar la inicialización
});



function descargarExcel() {
    window.location.href = "/exportar_ubicaciones";
}