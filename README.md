# Subkultur teilwas Bot
Der subkultur teilwas Telegram Bot ermöglicht den einfachen Austausch von Essen, Sachen oder Fähigkeiten. Man kann mit ihm Angebote oder Gesuche aufgeben, die von anderen Benutzern leicht gefunden werden können.  
Er wird (vorherige Installation von Telegram selbst natürlich vorausgesetzt) in Telegram installiert durch Besuch der Seite [t.me/teilwas_bot](https://t.me/teilwas_bot).  

_Wichtig:_ Bevor man eigene Angebote oder Gesuche aufgibt, muss man einen Telegram-Benutzernamen einstellen, sonst können anderen Benutzer keinen Kontakt aufnehmen.  

### Benutzung des Bots
In Telegram werden Bots durch Kommandos gesteuert, die man wie „normale“ Chatnachrichten schreibt. 
Der teilwas Bot versteht folgende Kommandos:
#### /add oder /a
Hiermit werden neue Einträge angelegt. 
Nach Eingabe des Kommandos wird man vom Bot durch eine Unterhaltung geführt, durch die alle wichtigen Informationen zum Angebot oder Gesuch erhoben werden. Dies sind nacheinander:
* Kategorie des Eintrags: Essen, Sache oder Fähigkeit
* Art des Eintrags: Angebot an andere oder Gesuch von anderen 
* Ort des Eintrags. Dies ist nötig, damit in Abhängigkeit einer Entfernung gesucht werden kann.
* Eine Beschreibung des Eintrags 
* Ein (optionales) Ablaufdatum des Eintrags. Hier kann entweder ein konkretes in der Zukunft liegendes Datum eingeheben werden (in der Form „3.4.2022“) oder eine Anzahl von Tagen, die der Eintrag gültig sein soll (einfach als Zahl, z.B. „30“).

#### /search oder /s
Hiermit werden vorhandene Einträge anderer Benutzer gesucht.  
Wie beim Anlegen von Einträgen fragt der Bot verschiedene Informationen zum Gesuchten ab:
* Kategorie des Eintrags: Essen, Sache oder Fähigkeit. Auch die Wahl von Alles ist möglich, wenn die Kategorie egal ist. 
* Art des Eintrags: Angebot an andere oder Gesuch von anderen. Auch die Wahl von Alles ist möglich, wenn die Art egal ist. 
* Entfernung des Eintrags: Hier kann man verschiedene Entfernen in Kilometern auswählen, die der Eintrag entfernt sein darf. 
Man kann auch entweder eine beliebige Entfernung (in Kilometern) eintragen. Oder man kann "überall" wählen, dann wird die Abfrage des eigenen Ortes übersprungen.
* Ort des Eintrags: Anzugeben, um nur in einer bestimmten Entfernung zu suchen.  

Wenn etwas mit den gewählten Einschränkungen gefunden werden konnte, wird eine Liste und eine Kartenansicht der Ergebnisse zurück gegeben.  
Den Listeneinträgen ist eine Zahl vorangestellt. Durch Eingabe dieser Zahl wird der Ersteller des Eintrags darüber informiert, dass Du daran Interesse hast, und hat dann die 
Möglichkeit Dich zu kontaktieren.

#### /list oder /l
Hiermit kann man eigene Einträge auflisten. 

#### /delete oder /d
Hiermit können eigene Einträge gelöscht werden.  
Nach Eingabe des Befehls werden alle eigenen Einträge aufgelistet. Durch folgende Eingabe der vorangestellten Zahl im nächsten Schritt, wird der entsprechende Eintrag aus dem Liste insgesamt vorhandener Einträge gelöscht. 

##### Weitere Ideen:
* Sollte es möglich sein Suchen abonnieren zu können? Dass man also automatisch benachrichtigt wird, wenn neue Einträge einer gewählten Kategorie angelegt werden?
