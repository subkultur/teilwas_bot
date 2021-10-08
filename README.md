# Subkultur teilwas Bot
Der subkultur teilwas Telegram Bot ermöglicht den einfachen Austausch von Essen, Sachen oder Fähigkeiten. Man kann mit ihm Angebote oder Gesuche aufgeben, die von anderen Benutzern leicht gefunden werden können.  
Er wird (vorherige Installation von Telegram selbst natürlich vorausgesetzt) in Telegram installiert durch Besuch der Seite [t.me/teilwas_bot](https://t.me/teilwas_bot).  

_Wichtig:_ Bevor man Angebote oder Gesuche anderer annimmt, muss man einen Telegram-Benutzernamen einstellen, sonst kann kein Kontakt hergestellt werden.  

### Benutzung des Bots
In Telegram werden Bots durch Kommandos gesteuert, die man wie „normale“ Chatnachrichten schreibt.  
Der teilwas Bot versteht folgende Kommandos:

#### /cancel oder /c
Jederzeit kann man ein Hinzufügen, Suchen oder Löschen abbrechen, wenn man dieses Kommando eingibt.
#### /add oder /a
Hiermit werden neue Einträge angelegt. 
Nach Eingabe des Kommandos wird man vom Bot durch eine Unterhaltung geführt, durch die alle wichtigen Informationen zum Angebot oder Gesuch erhoben werden. Dies sind nacheinander:
* Kategorie des Eintrags: Essen, Sache, Kleidung oder Fähigkeit.
* Art des Eintrags: Angebot an andere oder Gesuch von anderen.
* Ort des Eintrags. Dies ist nötig, damit in Abhängigkeit einer Entfernung gesucht werden kann.
* Eine Beschreibung des Eintrags.
* Ein (optionales) Ablaufdatum des Eintrags. Hier kann entweder ein konkretes in der Zukunft liegendes Datum eingeheben werden (in der Form „3.4.2022“) oder eine Anzahl von Tagen, die der Eintrag gültig sein soll (einfach als Zahl, z.B. „30“).

#### /search oder /s
Hiermit werden vorhandene Einträge anderer Benutzer gesucht.  
Wie beim Anlegen von Einträgen fragt der Bot verschiedene Informationen zum Gesuchten ab:
* Kategorie des Eintrags: Essen, Sache, Kleidung oder Fähigkeit. Auch die Wahl von Alles ist möglich, wenn die Kategorie egal ist. 
* Art des Eintrags: Angebot an andere oder Gesuch von anderen. Auch die Wahl von Alles ist möglich, wenn die Art egal ist. 
* Entfernung des Eintrags: Hier kann man verschiedene Entfernen in Kilometern auswählen, die der Eintrag entfernt sein darf. 
Man kann auch entweder eine beliebige Entfernung (in Kilometern) eintragen. Oder man kann "überall" wählen, dann wird die Abfrage des eigenen Ortes übersprungen.
* Ort des Eintrags: Anzugeben, um nur in einer bestimmten Entfernung zu suchen. Wurde "überall" gewählt wird dies nicht abgefragt.  

Wenn etwas mit den gewählten Einschränkungen gefunden werden konnte, wird eine Liste und eine Kartenansicht der Ergebnisse zurückgegeben.  
Den Listeneinträgen ist eine Zahl vorangestellt. Durch Eingabe dieser Zahl wird der Ersteller des Eintrags darüber informiert, dass Du daran Interesse hast, und hat dann die 
Möglichkeit Dich zu kontaktieren.

#### /list oder /l
Hiermit können eigene Einträge aufgelistet werden. 

#### /delete oder /d
Hiermit können eigene Einträge gelöscht werden.  
Nach Eingabe des Befehls werden alle eigenen Einträge aufgelistet. Durch folgende Eingabe der vorangestellten Zahl im nächsten Schritt, wird der entsprechende Eintrag aus der Liste insgesamt vorhandener Einträge gelöscht.  

### Abonnements
Der Bot unterstützt das Abonnieren von Eintragungen: Wenn ein anderer Benutzer einen passenden Eintrag anlegt, erhält man automatisch eine entsprechende Benachrichtigung.  

#### /subscribe oder /sub oder /add_subscription oder /as
Hiermit kann man ein Abonnement anlegen.  
Nach Eingabe des Kommandos fragt der Bot (analog zur Suche) Eigenschaften des gewünschten Abos ab:
* Kategorie des Eintrags: Essen, Sache, Kleidung oder Fähigkeit. Auch die Wahl von Alles ist möglich, wenn die Kategorie egal ist. 
* Art des Eintrags: Angebot an andere oder Gesuch von anderen. Auch die Wahl von Alles ist möglich, wenn die Art egal ist. 
* Entfernung des Eintrags: Hier kann man verschiedene Entfernen in Kilometern auswählen, die der Eintrag entfernt sein darf. 
Man kann auch entweder eine beliebige Entfernung (in Kilometern) eintragen. Oder man kann "überall" wählen, dann wird die Abfrage des eigenen Ortes übersprungen.
* Ort des Eintrags: Anzugeben, um nur in einer bestimmten Entfernung zu suchen. Wurde "überall" gewählt wird dies nicht abgefragt.  

#### /list_subscriptions oder /ls
Hiermit können eigene Abonnements aufgelistet werden.

#### /delete_subscription oder /ds
Hiermit können eigene Abonnements gelöscht werden.  
Nach Eingabe des Befehls werden alle eigenen Abonnements aufgelistet. Durch folgende Eingabe der vorangestellten Zahl im nächsten Schritt, wird das entsprechende Abonnements gelöscht und man erhält keine weiteren Benachrichtigungen dazu.  