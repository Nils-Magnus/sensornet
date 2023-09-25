Den Controller mit MicroPython ausstatten und softwareseitig testen
-------------------------------------------------------------------

Den Controller schließen wir über ein USB-C-zu-A-Kabel an einen
USB-Port eines Linux-Rechners an. Bevor wir Kontakt zum Controller
aufnehmen können, gilt es ein paar Vorbereitungen zu treffen. Das
spätere serielle Device ist nur schreibbar für Root und Mitglieder der
Gruppe `dialout`. Daher fügen wir den aktuellen Benutzer dieser Gruppe
hinzu:

  $ sudo usermod -aG dialout $USER

Die Gruppenzugehörigkeit wird erst beim nächsten Login aktiv. Um die
Gruppe zu aktivieren können wir entweder rabiat die Rechner neu
starten, etwas umständlich uns per `ssh localhost` neu einloggen oder
mit `newgrp dialout` die neue Gruppe in der aktuellen Shell
aktivieren. Egal wie, wir verfizieren das Ergebnis mit `id -a`: Dort
sollte nun `dialout` als sekundäre Gruppe gelistet sein.

Nach dieser Vorarbeit können wir uns nun auch auf logischer Ebene mit
dem Controller verbinden. Auf dem kleinen Board ist dazu im
Esspressiv-SoC neben dem Risc-V-Prozessor eine serielle Schnittstelle
(UART, Universal Asynchronous Receiver Transmitter) untergebracht, die
sich um die Verbindung vom USB-Ports des Controllerboards mit dem
eigentlichen ESP32 kümmert. Diese Verbindung besteht nicht automatisch
und wir müssen sie manuell aktivieren.

Dazu verbinden wir also den Controller per USB-Kabel mit unserem
Computer. Dann drücken und halten(!) wir den kleinen Taster, der mit
`0` bezeichnet ist. Nun drücken wir etwa eine Sekunde lang den anderen
Taster, der die Aufschrift `Reset` trägt und lassen diesen zweiten
Taster wieder los. Den ersten Taster lassen wir dann schließlich nach
einer weiteren Sekunde ebenfalls los. Jetzt sollte sich der UART beim
USB-Subsystem des Computers gemeldet haben, was wir im Kernellog
nachsehen:

  $ sudo dmesg -Tw
  [So Sep 24 22:58:28 2023] usb 2-1: new full-speed USB device number 6 using xhci_hcd
  [So Sep 24 22:58:28 2023] usb 2-1: New USB device found, idVendor=303a, idProduct=0002, bcdDevice= 7.23
  [So Sep 24 22:58:28 2023] usb 2-1: New USB device strings: Mfr=1, Product=2, SerialNumber=3
  [So Sep 24 22:58:28 2023] usb 2-1: Product: ESP32-S2
  [So Sep 24 22:58:28 2023] usb 2-1: Manufacturer: Espressif
  [So Sep 24 22:58:28 2023] usb 2-1: SerialNumber: 0
  [So Sep 24 22:58:28 2023] cdc_acm 2-1:1.0: ttyACM1: USB ACM device

Am Hersteller `Espressif` erkennen wir, dass wir es mit unserem
Controller zu tun haben, der nun am Device `/dev/ttyACM1` erreichbar
ist. Ebenfalls kontrollieren lässt sich die Verbindung mit

  $ lsusb | grep ESP32
  Bus 002 Device 006: ID 303a:0002 Espressif ESP32-S2

Nun, da wir die Verbindung zum Controller hergestellt haben, können
wir ihn vorbereiten und mit einer Firmware versehen. In unserem Falle
wird das Micropython werden. Dazu benötigen wir auf dem Computer ein
paar Werkzeuge. Einige davon sind in Python, sodass wir uns dazu ein
Virtualenv anlegen, es aktivieren und in ihm die Pakete `esptool` und
`adafruit-ampy` installieren. Anschließend installieren wir noch das
Terminalprogramm `picocom` über den Paketmanager:

  $ python3 -m venv projekt
  $ . projekt/bin/activate
  $ pip install esptool adafruit-ampy

Es fehlt noch das Image der Firmware. Die können wir unter

  https://micropython.org/download/

suchen. Wenn wir beispielsweise auf `Vendor: Wemos` filtern sehen wir
bereits das Board des ESP-S2-Mini und klicken darauf. Unter den Bild
findet sich der Download der Firmware. Wir benutzen die Version 1.20.0
vom 26. April 2023 im `bin`-Format. Wer das Image direkt herunterladen
will, erreicht dies mit:

  $ curl -O https://micropython.org/resources/firmware/LOLIN_S2_MINI-20230426-v1.20.0.bin

Wir nutzen das ESP-Tool, um über die serielle Schnittstelle vom ESP32
ein paar Information abzufrufen. Hier muss eventuell hinter der Option
`-p` das Device für die serielle Schnittstelle auf den Wert angepasst
werden, den der Kernel im Output von `dmesg` gemeldet hat. Meiner
Erfahrung sind keine Angaben einer seriellen Geschwindigkeit mit `-b`
und auch sonst kein Chip-Typ oder ähnliches nötig. Das Tool findet
alles alleine heraus. Einzig habe ich `--after no_reset` aus
kosmetischen Gründen hinzugefügt, da das ESP-Tool aus dem
Konsolenmodus, in den wir mit der Tasterkombination gelangt sind,
selbst nicht wieder herauskommen kann. Dazu muss ein Hardware-Reset
durchgeführt werden. Dazu aber später mehr. Schauen wir uns erst
einmal die Seriennummern an:

  $ esptool.py -p /dev/ttyACM1 --after no_reset chip_id
  esptool.py v4.6.2
  Serial port /dev/ttyACM1
  Connecting...
  Detecting chip type... Unsupported detection protocol, switching and trying again...
  Detecting chip type... ESP32-S2
  Chip is ESP32-S2FNR2 (revision v0.0)
  Features: WiFi, Embedded Flash 4MB, Embedded PSRAM 2MB, ADC and temperature sensor calibration in BLK2 of efuse V2
  Crystal is 40MHz
  MAC: 48:27:e2:5d:fb:36
  Uploading stub...
  Running stub...
  Stub running...
  Warning: ESP32-S2 has no Chip ID. Reading MAC instead.
  MAC: 48:27:e2:5d:fb:36
  Staying in bootloader.

Anhand der MAC-Adresse, die vermutlich auch für das WLAN genutzt wird,
können wir die einzelnen Devices unterscheiden.

Die Dokumentation schlägt vor, den Controller nun einmal komplett zu
löschen, keine Ahnung, ob das wirklich notwendig ist. Falls vorher
etwas anderes auf dem Controller war, ist es danach weg, also gilt
hier ein wenig Vorsicht:

  $ esptool.py -p /dev/ttyACM1 --after no_reset erase_flash

Das hat bei mir rund 14 Sekunden gedauert. Anschließend übertragen  wir das
heruntergeladene Image auf den Controller, was weitere 10 Sekunden dauert:

  $ esptool.py -p /dev/ttyACM1 write_flash -z 0x1000 LOLIN_S2_MINI-20230426-v1.20.0.bin

Jetzt sollte der Controller bereit sein und eine Python-Console auf
dem seriellen Port anbieten, wenn wir die etwas umständliche
Taster-Kombination nach dem Anstecken der USB-Verbindung
durchführen. Das probieren wir mit dem Terminalprogramm `picocom` aus:

  $ picocom /dev/ttyACM1
  picocom v3.1

  port is        : /dev/ttyACM1
  flowcontrol    : none
  baudrate is    : 9600
  [...]

  Type [C-a] [C-h] to see available commands
  Terminal ready

Ich habe keinerlei Konfiguration hinsichtlich Baudrate, Start- oder
Stoppbits und Flow-Control benötigt. Um in den Kommandomodus von
Picocoom zu kommen ist ähnlich wie bei Screen oder Tmux ein Präfix
nötig, der hier [C-a] ist. Mit [C-a][C-x] verlässt man Picocom wieder,
was wir jetzt aber noch nicht machen, denn wir wollen ja an die
Python-Console zu kommen. Dazu drücken wir ein paar Male [Enter] und
sehen dann bereits den Python-Prompt:

  >>>

Das ist die so genannte REPL (steht für _read, evaluate, print, and
loop_), quasi die interaktive Python-Shell, die wir auch auf unserem
Notebook per `python -i` bekämen. Damit können wir das offenkundige
Hello-World mittels

  >>> print("Hello, World!")
  Hello, World!

ausprobieren. Spannender ist jedoch, die Hardware in Aktion zu
sehen. Auf dem Controller-Board ist eine winzige LED versteckt und an
Pin 15 neben dem einen Taster angebracht. Mit dem Python-Package
`machine` haben wir Zugriff auf die Hardware, darunter auf die
einzelnen programierbaren, digitalen Pins. Wenn wir Pin 15 als
Output-Pin definieren (`Pin(15, Pin.OUT)`), können wir mit `value(1)`
die LED einschalten:

  >>> from machine import Pin
  >>> Pin(15, Pin.OUT).value(1)

Das ist doch schonmal sehr nett. Mit diesem Wissen lassen sich jetzt
die Objekte und Methoden von `machine` erkunden oder auf der Website
von Micropython nachlesen. Es gibt dort zu jedem Hardware-Feature eine
Entsprechung.

Jetzt bleibt noch die Frage offen, wie sich Programme auf dem ESP32
persistieren lassen, damit sie auch ohne die Verbindung mit dem
Computer laufen. Der Trick besteht darin, dass der Controller ein
kleines Dateisystem verwaltet, dort nach der Datei `/boot.py` sucht
und dessen Inhalt ausführt.

Zum Experimentieren implementieren wir kurz eine minimalistische
Version von `ls` und `cat`:

  >>> import os
  >>> def ls():
  ...     for file in os.listdir("/"):
  ...         print(file)
  ...
  >>> def cat(file):
  ...     print(open(file).read())
  ...     
  >>> ls()
  boot.py
  >>> cat("/boot.py")
  # This file is executed on every boot (including wake-boot from deepsleep)
  #import esp
  #esp.osdebug(None)
  #import webrepl
  #webrepl.start()

Bleibt die Frage, wie sich Dateien vom Computer zum Controller
übertragen lassen. Dafür ist das Werkzeug `ampy` gedacht. Wir
verlassen also das Terminalprogramm mit [C-a][C-x] und sehen uns die
eben entdeckte Datei vom Computer aus an:

  $ ampy -p /dev/ttyACM1 ls
  /boot.py
  $ ampy -p /dev/ttyACM1 get /boot.py
  # This file is executed on every boot (including wake-boot from deepsleep)
  #import esp
  #esp.osdebug(None)
  #import webrepl
  #webrepl.start()

Nun können wir mit einem Editor oder einem IDE unserer Wahl auf dem
Computer beispielsweise ein Blink-Script schreiben und hochladen:

  $ cat boot.py
  #
  # upload with ampy -p /dev/ttyACM1 put boot.py
  #

  import os, machine, math, time

  print("This is the pulse flasher.")

  def cat(file):
       print(open(file).read())

  def ls():
      for file in os.listdir("/"):
          print(file)

  led = machine.PWM(machine.Pin(15), freq=1000)

  def pulse(l, t):
      for i in list(range(90)) + list(range(90, -1, -1)):
          l.duty(int(math.sin(i / 20 * math.pi) * 500 + 500))
          time.sleep_ms(t)

  while True:
      pulse(led, 50)

Das Skript verwendet bereits einige fortgeschrittene Features, aber
letztlich lässt es die LED sanft blinkn, sobald wir es mit

 $ ampy -p /dev/ttyACM1 put boot.py

hochgeladen haben. Zum Start drücken wir den Reset-Knopf. Alternativ
lassen sich Skripte auch unter anderem Namen hochladen und mit dem
`run`-Kommando von `ampy` starten.

Zum Abschluss dieses Abschnitts noch ein Hinweis auf eine Funktion der
Console: Sie versteht die Tasten [C-d] und [C-c] und reagiert darauf
sehr ähnlich wie dies eine Bash unter Linux täte: Die erste
Kombination erzeugt ein EOF. In einer REPL-Console bedeutet dies, dass
ein Soft-Reset durchgeführt wird. Die zweite Kombination schickt einen
Keyboard-Interrupt und bringt uns zurück in die REPL-Shell. Das ist
nützlich, wenn Skripte in einer Endlosschleife laufen.

Viel Spaß mit den ersten Schritten mit Python auf dem ESP32!
