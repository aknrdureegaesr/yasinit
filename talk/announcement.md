# Ein Python init für Docker (und Kubernetes).

Der "init"-Prozess eines Linuxsystems oder eines Dockercontainers oder
eines Kubernetes-PODs hat besondere Aufgaben und wird vom Kernel
besonders behandelt.

Wenn man es falsch macht

* müllen längst beendete Prozesse die Prozesstabelle voll, übrigens
  auch die des Hosts, bis im Extremfall keine neuen Prozesse mehr
  gestartet werden können,

* dauert es (bei üblichem Setup) endlose lange (z.B. 10 Sekunden), bis
  der Container endlich heruntergefahren ist,

* und trotz dieser langen Gnadenfrist wird die Anwendung ohne
  Vorwarnung "hart" heruntergefahren (das moralische Äquivalent eines
  "Crashs").

In einem Vortrag mit Experimenten wird vorgestellt, welche Ausnahmen
der Kernel bei "init" macht und was passiert, wenn man Programme als
"init" nutzt, die das nicht berücksichtigen.

Eine minimalistische Python-Lösung bietet mein "yet another simple
init" https://github.com/aknrdureegaesr/yasinit . Man könnte sagen,
der Vortrag sei eine Langversion der "README.md" von
yasinit. Inhaltlich werden einige Linux-Grundlagen vermittelt:
Boot+Shutdown, Signale, exec vs. system und Prozessverwaltung.

 
