const formulario =
    document.getElementById("formulario-chat");

const ventanaChat =
    document.querySelector(".ventana-chat");

const estadoCarga =
    document.getElementById("estado-carga");

const botonAbrirGuia =
    document.getElementById("boton-abrir-guia");

const botonCerrarGuia =
    document.getElementById("boton-cerrar-guia");

const panelChecklist =
    document.getElementById("panel-checklist");

/*
 * Abrir guía
 */

botonAbrirGuia.addEventListener(
    "click",
    function () {

        panelChecklist.hidden = false;

        panelChecklist.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }
);


/*
 * Ocultar guía
 */

botonCerrarGuia.addEventListener(
    "click",
    function () {

        panelChecklist.hidden = true;

    }
);


/*
 * Scroll del chat
 */

function bajarAlFinal() {

    ventanaChat.scrollTo({
        top: ventanaChat.scrollHeight,
        behavior: "smooth"
    });

}

window.addEventListener(
    "load",
    bajarAlFinal
);


/*
 * Envío del formulario
 */

formulario.addEventListener(
    "submit",
    function (event) {

        if (
            formulario.dataset.enviando
            === "true"
        ) {

            event.preventDefault();

            return;
        }

        formulario.dataset.enviando =
            "true";

        const botones =
            formulario.querySelectorAll(
                'button[type="submit"]'
            );

        botones.forEach(
            function (boton) {

                boton.disabled = true;

            }
        );

        estadoCarga.hidden = false;

    }
);

/*
 * Empezar actividad guiada
 */

const botonesEmpezarPaso =
    document.querySelectorAll(
        ".boton-empezar-paso"
    );

botonesEmpezarPaso.forEach(
    function (boton) {

        boton.addEventListener(
            "click",
            async function (event) {

                event.preventDefault();

                const pasoId =
                    boton.dataset.pasoId;

                const metodologia =
                    boton.dataset.metodologia;

                boton.disabled = true;
                estadoCarga.hidden = false;

                try {

                    const datos =
                        new URLSearchParams();

                    datos.append(
                        "metodologia",
                        metodologia
                    );

                    datos.append(
                        "paso_id",
                        pasoId
                    );

                    const respuesta =
                        await fetch(
                            "/chat/seleccionar-paso",
                            {
                                method: "POST",
                                headers: {
                                    "Content-Type":
                                        "application/x-www-form-urlencoded"
                                },
                                body: datos
                            }
                        );

                    const resultado =
                        await respuesta.json();

                    if (!respuesta.ok || !resultado.ok) {

                        if (resultado.sesion_cerrada) {

                            alert(
                                resultado.error ||
                                "Tu sesión se ha cerrado."
                            );

                            window.location.href = "/login";

                            return;
                        }

                        throw new Error(
                            resultado.error ||
                            "No se ha podido iniciar la actividad."
                        );
                    }

                    const filaAsistente =
                        document.createElement("div");

                    filaAsistente.className =
                        "fila-mensaje fila-asistente";

                    filaAsistente.innerHTML = `
                        <div class="identificador-mensaje">
                            Asistente
                        </div>

                        <div class="mensaje-chat mensaje-bot">
                            ${resultado.respuesta}
                        </div>
                    `;

                    ventanaChat.appendChild(
                        filaAsistente
                    );

                    // Llevar la página de vuelta al chat
                    ventanaChat.scrollIntoView({
                        behavior: "smooth",
                        block: "start"
                    });

                    // Llevar el chat al último mensaje
                    setTimeout(
                        function () {
                            ventanaChat.scrollTo({
                                top: ventanaChat.scrollHeight,
                                behavior: "smooth"
                            });
                        },
                        400
                    );

                } catch (error) {

                    console.error(error);

                    alert(error.message);

                } finally {

                    boton.disabled = false;
                    estadoCarga.hidden = true;

                }             
            }
        );
    }
);

/*
 * Guardar estado de los checkboxes
 */

const checkboxesPaso =
    document.querySelectorAll(
        ".checkbox-paso"
    );

checkboxesPaso.forEach(
    function (checkbox) {

        checkbox.addEventListener(
            "change",
            async function () {

                console.log("CHECKBOX CAMBIADO", checkbox.dataset.pasoId);

                const pasoId =
                    checkbox.dataset.pasoId;

                const metodologia =
                    checkbox.dataset.metodologia;

                const datos =
                    new URLSearchParams();

                datos.append(
                    "metodologia",
                    metodologia
                );

                datos.append(
                    "paso_id",
                    pasoId
                );

                datos.append(
                    "completado",
                    checkbox.checked
                        ? "true"
                        : "false"
                );

                try {

                    const respuesta =
                        await fetch(
                            "/chat/marcar-paso",
                            {
                                method: "POST",
                                headers: {
                                    "Content-Type":
                                        "application/x-www-form-urlencoded"
                                },
                                body: datos
                            }
                        );

                    const resultado =
                        await respuesta.json();

                    if (
                        !respuesta.ok ||
                        !resultado.ok
                    ) {
                        throw new Error(
                            resultado.error ||
                            "No se ha podido guardar el estado."
                        );
                    }

                } catch (error) {

                    console.error(error);

                    // Si falla el guardado,
                    // devolvemos el checkbox a su estado anterior.
                    checkbox.checked =
                        !checkbox.checked;

                    alert(
                        "No se ha podido guardar el estado."
                    );
                }
            }
        );
    }
);