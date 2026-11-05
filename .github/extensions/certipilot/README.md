# Canvas de Certipilot

Extensión de **proyecto** para GitHub Copilot App. Es una entrada al estudio,
no una presentación de diapositivas ni una encuesta: eliges examen, consultas
un plan local y continúas en el chat con el agente.

## Instalar y abrir

1. Conserva esta carpeta completa en `.github/extensions/certipilot/` dentro
   de tu checkout de Certipilot. No requiere `npm install`, `package.json`
   ni una copia del SDK: el runtime proporciona `@github/copilot-sdk`.
2. Abre una sesión **del repositorio** en GitHub Copilot App y confía/habilita
   la extensión de proyecto si el cliente lo solicita. Usa modo Interactive
   (`Shift+Tab`) para estudiar por turnos.
3. En una sesión que ya estaba abierta, recarga las extensiones si tu cliente
   ofrece esa opción; de lo contrario, reinicia esa sesión desde la app.
   En la superficie Agency, el canvas Session Settings ofrece la acción
   `restart_session`. No hace falta reiniciar ni modificar otros repositorios.
4. Pide en ese chat: **«Abre el canvas Certipilot»**. El agente debe descubrir
   `canvasId: certipilot`, comprobar sus capacidades y abrirlo con un
   `instanceId` propio. El proveedor de proyecto es `project:certipilot`.
   Si no aparece, comprueba la habilitación y el log de la extensión; no
   sustituye este paso abrir una página HTML en un navegador.

La extensión se versiona con el repositorio. Antes de que alguien pueda
instalarla desde un clon remoto, sus archivos deben estar incluidos en una
revisión compartida. Crear esta carpeta no publica ni instala nada globalmente.

## Qué hace

- Enumera carpetas de examen que tengan `exam.md`; no usa una lista fija.
- Pide selección explícita. No interpreta fechas de Markdown libre ni afirma
  que un examen esté activo por el nombre, la fecha de modificación o la
  existencia de un checkpoint. La elección se vuelve intención explícita al
  pulsar una acción de estudio.
- Lee planes Markdown de `exams/<id>/assets/study-plans/` y de `assets/`,
  excluyendo `README.md`. Los transversales se identifican como tales, sin
  atribuirlos automáticamente al examen. La vista previa muestra el texto
  literal, nunca ejecuta HTML.
- Permite continuar un checkpoint existente, practicar una pregunta,
  explicar un tema con tutor, crear un plan o seguir el plan seleccionado.
  La existencia de `session.json` no significa que se haya validado: el agente
  aplica el protocolo canónico antes de reanudar.
- Usa `joinSession()` y `session.send()` del SDK. **El receptor es la sesión
  de Certipilot que aloja el canvas**, no un coordinador externo ni una sesión
  nueva. Se envían examen, intención y ruta de plan, no respuestas privadas.
  El prompt pide cargar `AGENTS.md`, `exam.md`, los contratos y la skill
  pertinente. La conversación mantiene la verificación de fuentes,
  persistencia, selección de agentes y preguntas de una en una.
- Comprueba el modo mediante `session.rpc.mode.get()`; fuera de Interactive
  muestra cómo cambiarlo, sin cambiar permisos ni modo silenciosamente.

## Privacidad y límites

Los planes se muestran **solo al abrirlos**: revisa su contenido antes de
compartir pantalla. Los archivos personales permanecen en las ubicaciones
ignoradas existentes. No se copian al código de la extensión ni se escriben
puntuaciones, cobertura o checkpoints desde la interfaz.

Sin archivos locales, muestra su ausencia, no porcentajes cero ni datos de
ejemplo. Un worktree o clon nuevo normalmente no contiene tus archivos
ignorados; la extensión no busca datos en el checkout principal ni en otros
repositorios. Las rutas que salen del repositorio mediante enlaces se rechazan.

La selección del panel es temporal y puede restablecerse al recargar la
extensión; no constituye un nuevo almacén de progreso. Los planes se releen
desde disco. Para refrescar disponibilidad tras estudiar, pulsa **Actualizar**.
El cuerpo de `session.json`, `coverage.json` y `progress.md` no se publica al
iframe; solo se comprueba su presencia. La extensión no calcula métricas.

Cada panel sirve sus recursos en `127.0.0.1`, en un puerto efímero y una ruta
aleatoria. No hay servicios externos, telemetría ni dependencias web.
Los POST requieren origen propio, cabecera explícita y JSON. Se desactiva
la caché; el servidor se cierra al cerrar el canvas.

## Desarrollo y comprobación

Basado en la guía `create-canvas`, el ejemplo oficial de servidor por instancia
y las declaraciones instaladas `canvas.d.ts`, `extension.d.ts`, `types.d.ts`
y `generated/rpc.d.ts`. En el entorno de creación no estaban disponibles las
herramientas `extensions_manage`/`extensions_reload`, tampoco al intentar la
ruta CLI. Por ello no se pudo ejecutar el generador oficial: se utilizó el
patrón documentado de `createCanvas`/`joinSession`, sin inventar una API de
scaffold ni afirmar que se hubiera recargado en la app.

Desde la raíz, con Node.js 22 o posterior:

```powershell
node --test .github\extensions\certipilot\tests\canvas.test.mjs
```

Los tests usan únicamente fixtures sintéticos temporales. Cubren selección,
aislamiento, ausencia de datos, planes, las cinco acciones, errores de envío,
modo Interactive, doble clic concurrente, reinicio de proceso, rutas y HTTP.
No invocan un modelo ni cuentan como evidencia de aprendizaje.

Además se comprobó con el SDK instalado y un runtime CLI aislado, sin invocar
un modelo: descubrimiento de `project:certipilot`, habilitación, apertura,
`refresh`, rechazo de entrada inválida y de la acción reservada `canvas.open`,
recarga, apertura de un panel nuevo y cierre. La ruta soportada encontrada es
`session.rpc.extensions.list()/enable({ id })/reload()` y
`session.rpc.canvas.open()/action.invoke()/close()` del SDK; no es una API
HTTP inventada ni un reemplazo del generador ausente.

La interfaz también se comprobó en un navegador con los exámenes reales del
checkout y el envío bloqueado explícitamente. Eso no activa la extensión en
la sesión de la app que ya estaba abierta ni prueba una respuesta del modelo.
La recuperación automática del panel anterior tras recarga no quedó confirmada
en esta instalación; abre un panel nuevo o reinicia la sesión si queda obsoleto.
La matriz de CI contempla Windows y Linux; la validación local se ejecutó en
Windows, no en runners remotos.

La comprobación final en la app requiere descubrir el canvas y abrirlo en
la sesión del repositorio. Después prueba un botón en modo Interactive, sin una
actividad pendiente que no quieras interrumpir. No se dan por procesadas las
solicitudes solo porque `session.send()` haya devuelto su identificador.
