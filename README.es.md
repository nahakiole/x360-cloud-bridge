# X360 Cloud Bridge

Usa tu **control inalámbrico de Xbox 360** (con su receptor USB) para jugar
**Xbox Cloud Gaming**, **GeForce NOW** y juegos de navegador en Chrome, en un Mac
moderno, incluso con Apple Silicon.

No necesitas extensiones de kernel ni drivers, y no hay que tocar SIP, AMFI ni la NVRAM.

> Este es un fork de [Maverserker/x360-cloud-bridge](https://github.com/Maverserker/x360-cloud-bridge)
> que corrige los controles que se desconectan unos segundos mientras juegas, y
> añade una instalación con un solo comando. Ver [Cambios en este fork](#cambios-en-este-fork).

[Read in English](README.md)

## Inicio rápido

Necesitas un Mac con [Homebrew](https://brew.sh), Google Chrome y el receptor
inalámbrico de Xbox 360 conectado.

```bash
git clone https://github.com/nahakiole/x360-cloud-bridge.git
cd x360-cloud-bridge
./install.sh
```

`install.sh` instala `libusb` con Homebrew si falta, prepara el entorno de Python en
`.venv` y te muestra la carpeta de la extensión. Después carga la extensión en
Chrome, una sola vez:

1. Abre `chrome://extensions`
2. Activa el **Modo de desarrollador**, arriba a la derecha
3. Haz clic en **Cargar descomprimida** y elige la carpeta `extension`. La ruta ya está
   en tu portapapeles: en el diálogo presiona `Cmd+Shift+G` y pégala.

Cada vez que quieras jugar:

```bash
./start.sh
```

Enciende el control con el botón Guide y abre [xbox.com/play](https://www.xbox.com/play)
o [play.geforcenow.com](https://play.geforcenow.com). Deja la terminal abierta mientras
juegas y presiona `Ctrl+C` para detenerlo. Si la página ya estaba abierta, recárgala.
**Cierra Steam** antes de jugar: acapara el receptor mientras está abierto.

## Cambios en este fork

Versión 0.1.1. La lista completa está en el [changelog](CHANGELOG.md) (en inglés).

Antes, un solo error de lectura USB (`[Errno 5] Input/Output Error`) hacía que el
helper diera el receptor por desconectado: lo cerraba, borraba todos los controles y
lo volvía a abrir, y los controles desaparecían unos segundos. El log del kernel de
macOS mostró que el receptor en realidad nunca se desconectaba del bus USB.

- **Las lecturas fallidas se reintentan** hasta 5 veces. El receptor solo se da por
  perdido si de verdad ya no está en el bus o si los errores no paran.
- **Timeout de lectura más largo**: 1 s en vez de 250 ms, con muchos menos abortos de
  transferencias USB.
- **Sin controles fantasma**: después de perder el receptor, ya no puede aparecer un
  control conectado que no existe.
- **Instalación con un comando**: `./install.sh`, y `./start.sh` lo ejecuta solo la
  primera vez.

Si un *solo* control se desconecta de vez en cuando, es su conexión inalámbrica:
prueba con pilas nuevas y acerca el receptor.

## Cómo funciona

macOS nunca ha soportado el receptor inalámbrico de Xbox 360. Para que un control
aparezca a nivel de sistema hace falta un permiso restringido de Apple. Pero el juego
en la nube corre en el navegador, así que basta con que el control exista **dentro de la
página**:

```
Receptor 360 ──USB──▶ helper (Python + libusb) ──WebSocket 127.0.0.1:8360──▶ extensión de Chrome
                                                                                 │
                         navigator.getGamepads() en xbox.com / GeForce NOW ◀─────┘
```

## Opciones

```bash
./start.sh --deadzone 0.2   # súbelo si los sticks se mueven solos (por defecto 0.15)
./start.sh --simulate       # control falso, sin receptor (para desarrollo)
./start.sh -v               # log detallado
```

## Problemas comunes

| Síntoma | Solución |
|---|---|
| El popup dice *Helper: not running* | Ejecuta `./start.sh` y deja la terminal abierta |
| *Receiver is in use by another program* | **Steam** acapara el receptor mientras está abierto. Ciérralo |
| El control no aparece en el juego | Recarga la pestaña del juego |
| El control no se empareja | Presiona el botón del receptor y luego el botón de conexión en la parte de arriba del control |
| Un solo control se desconecta a veces | Pilas nuevas, menos distancia, nada en medio |

## Limitaciones

- Solo funciona en el navegador. **No** funciona con la app nativa de GeForce NOW, con
  juegos nativos de Mac ni con Steam.
- El helper tiene que estar corriendo mientras juegas.
- No hay soporte para el puerto de audífonos ni para el chatpad.

## Contribuir

Los issues y pull requests son bienvenidos. Con `./start.sh --simulate` y la página
`test/gamepad-test.html` puedes trabajar sin hardware, y
`.venv/bin/python test/test_read_retries.py` prueba el manejo de errores USB. Los
detalles están en el [README en inglés](README.md#contributing).

## Créditos

El proyecto original es de [Maverserker](https://github.com/Maverserker/x360-cloud-bridge).
El protocolo inalámbrico de Xbox 360 está documentado en el driver
[`xpad`](https://github.com/torvalds/linux/blob/master/drivers/input/joystick/xpad.c) del kernel de Linux.

## Licencia

[GPL-3.0-or-later](LICENSE), igual que el original. Puedes usar, estudiar, compartir y
modificar este proyecto; si distribuyes una versión modificada, también debe publicarse
bajo la GPL junto con su código fuente.
