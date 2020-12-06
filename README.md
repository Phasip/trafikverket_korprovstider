# Övervaka trafikverkets lediga uppkörningstider
Fult script som övervakar trafikverket för lediga teoriprov & uppkörningstider.
Utnyttjar att man kan se lediga tider mha sitt personnummer - utan att logga in.

Just nu övervakar den uppkörningar i järfälla för Klass B - Automat samt teoripro för dito i Sollentuna, Järfälla & Stockholm.
## Howto
Ändra i .py för att matcha dina preferenser (främst mellan <config></config>)

```apt install swaks python3```

Lägg till cron-jobb för att köra scriptet regelbundet
```crontab -e
*/5 * *  *  *   python3 /home/MYUSER/korprov_monitor.py &> /home/MYUSER/korprov_monitor.log
```

## TODO
  -  Beskriv hur man får reda på platskoderna som behövs
  -  Använd configfil istället
  -  Mejla python med pythonkod istället
  -  Skapa en huginn agent / scenario istället
    
