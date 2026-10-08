# Precios Yango · Dashboard

Dashboard local en español para la pestaña **Questions** de la hoja solicitada. Incluye calendario de inicio y fin (ambos inclusive), conteo total y por Moto/Economy/Confort, las 11 columnas de detalle seleccionadas y descarga CSV del período filtrado. Logo y colores de Yango. La tabla y el CSV incluyen fecha/hora, correo, origen, destino, tarifa, precios de Yummy/Ridery/Yango, negociación, precio final en USD y comentarios.

## Abrir

Necesitas Python 3.10 o superior. Desde esta carpeta:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Abre **http://127.0.0.1:8765** en el navegador. Usa “Actualizar datos” para volver a consultar Google Sheets. Detén el servidor con Ctrl+C.

En Windows, activa el entorno con `.venv\Scripts\activate`.

## Acceso a Google

En el equipo usado para preparar este dashboard, la aplicación detecta las cuentas ya configuradas en `~/.config/google-sheets/accounts/`. No se incluyen claves, tokens ni datos personales en este código.

En otro equipo, configura una de estas opciones:

- **Cuenta de servicio:** activa Google Sheets API en tu proyecto de Google Cloud, genera su archivo de credenciales y comparte la hoja con el correo de esa cuenta como lector. Indica la ubicación del archivo:
  ```sh
  export GOOGLE_APPLICATION_CREDENTIALS="/ruta/credenciales.json"
  python app.py
  ```
- **OAuth de usuario:** usa un archivo de credenciales de usuario autorizado que tenga acceso a la hoja y permiso de lectura de Google Sheets:
  ```sh
  export GOOGLE_TOKEN_FILE="/ruta/token.json"
  python app.py
  ```

Guarda los archivos de credenciales fuera de esta carpeta. No los compartas ni los subas a un repositorio. No es necesario hacer pública la hoja.

## Criterios

- Fuente exacta: `Questions`, hoja `1RgmSfh7CrYIGdUGmKTznljJzl90f_Fw_5n2W9otxR_0`.
- Se leen fechas numéricas de Sheets, con el calendario local de la hoja (verificado: America/Caracas). No se convierten como si fueran UTC.
- Una fila con Timestamp válido equivale a un registro. No se deduplican filas ni se verifica que el viaje haya finalizado.
- “Económico” y “Economy” cuentan como Economy; “Comfort” y “Confort” cuentan como Confort.
- Filas vacías se ignoran. Fechas inválidas se excluyen y se informa cuántas hay. Otras tarifas se incluyen en el total y se avisa; no se asignan a una de las tres categorías.
- No se modifica ningún dato de la hoja. Los precios se muestran tal como están registrados, sin conversiones.
- Los archivos enlazados requieren los permisos de Google Drive del usuario.
- El servidor escucha únicamente en tu equipo. Para publicarlo para un equipo de trabajo hace falta añadir autenticación y un despliegue seguro; esta versión no está publicada.

## Facturas y comprobantes

La sección permite guardar PDF, PNG y JPG (máximo 10 MB por archivo) en la carpeta **Boost** de Drive. Selecciona tipo, persona, mes y referencia opcional. El nombre se genera como `2026-10 · María Pérez · Factura · Primera quincena.pdf`. El listado se puede filtrar por mes; usa la misma persona y período en facturas y comprobantes. Cada carga crea un archivo nuevo, sin reemplazar los anteriores.

La cuenta usada por el servidor requiere permiso Editor en esa carpeta y autorización de Google Drive. Los permisos existentes de la carpeta se conservan. En esta versión local cualquier usuario del dashboard puede subir ambos tipos de archivo; no hay un rol exclusivo de administradora.

**GitHub Pages:** subir estos archivos a GitHub Pages no basta para habilitar las cargas ni la lectura privada de Sheets. El servidor Python necesita ejecutarse en un servicio de backend. Antes de exponerlo a Internet, añade autenticación, permisos por rol, protección de las cargas y HTTPS. Las credenciales deben permanecer exclusivamente en el servidor. No publiques tokens, facturas ni comprobantes en el repositorio.

## Contraseña de acceso

La aplicación incluye la contraseña solicitada en `auth.py`. Puedes cambiarla con `DASHBOARD_PASSWORD` sin editar el código. Quien pueda leer el repositorio podrá ver la contraseña incorporada. La contraseña se valida en el servidor; no se incluye en HTML ni JavaScript. La sesión dura 8 horas y la cookie es HttpOnly. Hay un límite de 10 intentos fallidos por dirección IP en 5 minutos. Todos usan la misma contraseña y tienen acceso a la misma información y cargas.

Inicio local después de instalar las dependencias:

```sh
read -s -p "Contraseña del dashboard: " DASHBOARD_PASSWORD
export DASHBOARD_PASSWORD
python app.py
```

El comando `read -p` es para bash. En zsh/macOS puedes usar `read -s 'DASHBOARD_PASSWORD?Contraseña del dashboard: '` y luego `export DASHBOARD_PASSWORD`.

La carpeta de Drive conserva sus propios permisos: quien tenga su enlace y acceso puede abrirla sin la contraseña del dashboard. Si el acceso general es Editor, también puede modificar archivos directamente en Drive.

## Subir el código a GitHub y alojarlo

1. Crea un repositorio y sube el contenido de esta carpeta, incluyendo `.gitignore`. No subas credenciales, claves, facturas ni comprobantes.
2. Conecta el repositorio a un alojamiento que ejecute Python o Docker. GitHub Pages por sí solo no ejecuta este servidor.
3. Instala `requirements.txt` y usa `python app.py` como comando de inicio, o usa el Dockerfile.
4. Configura como secretos del alojamiento: `DASHBOARD_PASSWORD`, `SESSION_SECRET` (aleatorio y estable) y las credenciales de Google en un archivo privado señalado por `GOOGLE_TOKEN_FILE` o `GOOGLE_APPLICATION_CREDENTIALS`.
5. Configura `HOST=0.0.0.0`, el puerto que indique el alojamiento, `COOKIE_SECURE=1` y `APP_ORIGIN` con la URL HTTPS exacta, sin barra final.
6. La cuenta de Google del servidor debe poder leer la hoja y añadir archivos a la carpeta de Drive. Si usas una cuenta de servicio, comparte ambos recursos con ella y comprueba que tenga almacenamiento/cuota para subir a esa carpeta; algunas requieren una unidad compartida o delegación. OAuth de usuario aprovecha el almacenamiento de esa cuenta.

El Dockerfile es una alternativa de despliegue, no una publicación ya realizada. Mantén una sola instancia de esta versión: el límite de intentos está en memoria; un reinicio lo restablece.
