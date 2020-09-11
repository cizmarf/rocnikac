## Projekt zpracování a vizualizaci dat o vozidlech MHD v Praze a Středočeském kraji

### Vlastnosti

Stav k 11. 9. 2020

Aplikace umí stahovat realtime data z platformy Golemio a ukládat je do databáze.

K těmto datům stahuje všechna nezbytná statická data tzn. jízdní řády, trasu jízdy. 

Tato data jsou obohacena odhadem zpoždění, který je lepší než lineární (mezi vybranými zastávkami, modely nejsou součástí repozitáře). Množina vybraných zastávek se může rozšířit po stažení dostatečného množství historických dat. Avšak v rámci testování je demonstrováno, na příkladu jednoho modelu, že odhady zpoždění jsou lepší. 

Dále aplikace implementuje server, který zprostředkovává získaná data a ta je následně možné zobrazit v [interaktivní mapě](./index.html).

Vše zmíněné je možné vyzkoušet na demo datech, které jsou součástí repozitáře, ale jsou poměrně prostorově náročné.

### Nasazení

#### Databáze

Nejprve je nutné vytvořit databázi tak, jak je popsána v souboru [database_setup.sql](./database_setup.sql).

Jedná se o MySQL databázi.

#### Python

Aplikace vyžaduje Python 3 prostředí. Navíc využívá nestandardních knihoven [NumPy](https://numpy.org) a [scikit-learn](https://scikit-learn.org/stable/).
 
V souboru [file_system.py](./file_system.py) je nutné specifikovat projektový adresář.

V souboru [network.py](./file_system.py) je nutné použít vlastní přístupový token k databé platformě.

#### Spuštění

##### Main 

Hlavní program se spouští skriptem [download_and_process.py](./download_and_process.py). Při spustění je možné nastavit požadované přepínače.

Tento skript běží v nekonečné smyčce a pro ukončení je nutné jej ručně přerušit.

##### Web

Dále je nutné spustit server, který čte data z databáze.

Může být požádováno změnit číslo portu v konstruktoru serverové třídy. 

Ale jinak stačí spustit skript [server.py](./server.py).

Nyní je vše připraveno k otevření webové stránky pro vizualizaci.

### Testování

Součástí aplikace jsou testy, které ověřují funkčnost téměř každé části kodu.

Testy jsou uloženy v adresáři [tests](./tests/).

Některé testy ovšem vyžadují mít v provozu testovací databázi, aby se zamezilo přepsání drahocených historických dat. Ta se vytvoří stejně jako hlavní databáze podle dotazů v souboru [database_setup.sql](./database_setup.sql).

Dále jeden test `test_save_specify_model` v souboru [test_build_models.py](./tests/unit/test_build_models.py) vyžaduje naplněnou hlavní databázi historickými daty. 

Stějně tak testování serveru vyžaduje mít testovací databázi naplněnou testovacími daty.

#### Plnění databáze

Testovací databáze se naplním spuštím testovacího skriptu [test_database.py](./tests/integration/test_database.py), který testuje celou databázi.

Hlavní databáze se naplní funkcí `FillDatabase.testInsertData` ve [stejném souboru](./tests/integration/test_database.py). Ale tato operace trvá neúměrně dlouho a silně nedoporučiji ji spouštět.

#### Demo

Součástí skupiny integračních testů je i [skript](./tests/integration/test_main.py) na jednoduché demo. Kdy se vizualizují testovací data. Jen kvůli posunu časů spuštění dema a pořízení dat nemusí spravně fungovat zobrazení odjezdů ze zastávky.

Pokud by se zdálo že autobusy jezdí příliš pomalu je možné zrychlit čtení statických souborů parametrem `update_time`.

Stejného výsledku je možné dosáhnout i spuštěním hlavní aplikace, ale ta je primárně určena k zápisu do hlavní databáze a je nutné změnit přepínače.
 
Pro vizualici se využívá zmíněná mapa. Tato mapa zobrazuje všechny autobusy. Po klinutí jejich trasu, zastávky a jízdní řád. Dále po kliknutí na zastávku zobrazí všechna projíždějící vozidla a tabulku budoucích odjezdů z vybrané zastávky. Jak je možné vidět na obrázcích [vybraného vozidla](./docs/pictures/map_basic.png) nebo [vybrané zastávky](./docs/pictures/stop_selected.png).



 