import json
from pathlib import Path

# Each row lists verified connections to the columns in the same pool.
CLUES = {
    "barcelona": ("Barcelona", "برشلونة", "club"),
    "bayern": ("Bayern Munich", "بايرن ميونخ", "club"),
    "inter": ("Inter Milan", "إنتر ميلان", "club"),
    "juventus": ("Juventus", "يوفنتوس", "club"),
    "psg": ("Paris Saint-Germain", "باريس سان جيرمان", "club"),
    "united": ("Manchester United", "مانشستر يونايتد", "club"),
    "chelsea": ("Chelsea", "تشيلسي", "club"),
    "real": ("Real Madrid", "ريال مدريد", "club"),
    "arsenal": ("Arsenal", "أرسنال", "club"),
    "milan": ("AC Milan", "ميلان", "club"),
    "dortmund": ("Borussia Dortmund", "بوروسيا دورتموند", "club"),
    "messi": ("Lionel Messi", "ليونيل ميسي", "player"),
    "mbappe": ("Kylian Mbappé", "كيليان مبابي", "player"),
    "pep": ("Pep Guardiola", "بيب غوارديولا", "coach"),
    "ancelotti": ("Carlo Ancelotti", "كارلو أنشيلوتي", "coach"),
}

POOLS = (
    (("juventus", "psg", "united", "chelsea", "messi"), {
        "barcelona": (
            "Dani Alves|Zlatan Ibrahimović|Arturo Vidal|Miralem Pjanić",
            "Neymar|Ronaldinho|Lionel Messi|Dani Alves|Zlatan Ibrahimović|Maxwell|Ousmane Dembélé",
            "Gerard Piqué|Zlatan Ibrahimović|Alexis Sánchez|Memphis Depay|Henrik Larsson",
            "Cesc Fàbregas|Pedro|Deco|Samuel Eto’o|Eidur Guðjohnsen|Juliano Belletti",
            "Xavi|Andrés Iniesta|Neymar|Luis Suárez|Sergio Busquets|Gerard Piqué|Ronaldinho|Pedro|David Villa",
        ),
        "bayern": (
            "Kingsley Coman|Arturo Vidal|Mario Mandžukić|Medhi Benatia|Matthijs de Ligt|Douglas Costa",
            "Kingsley Coman|Juan Bernat|Eric Maxim Choupo-Moting|Lucas Hernández",
            "Bastian Schweinsteiger|Owen Hargreaves|Marcel Sabitzer|Matthijs de Ligt|Noussair Mazraoui",
            "Arjen Robben|Michael Ballack|Claudio Pizarro",
            'Thiago Alcântara|Arturo Vidal|Philippe Coutinho',
        ),
        "inter": (
            "Zlatan Ibrahimović|Andrea Pirlo|Patrick Vieira|Edgar Davids|Arturo Vidal|Roberto Baggio|Christian Vieri",
            "Achraf Hakimi|Zlatan Ibrahimović|Thiago Motta|Maxwell|Mauro Icardi",
            "Zlatan Ibrahimović|Romelu Lukaku|Alexis Sánchez|Matteo Darmian|André Onana|Ashley Young",
            "Romelu Lukaku|Samuel Eto’o|Hernán Crespo|Juan Sebastián Verón|Ricardo Quaresma",
            "Samuel Eto’o|Zlatan Ibrahimović|Maxwell|Alexis Sánchez|Lautaro Martínez",
        ),
        "pep": (
            "Arturo Vidal|Kingsley Coman|Mario Mandžukić|Dani Alves|Zlatan Ibrahimović|João Cancelo|Douglas Costa",
            "Lionel Messi|Dani Alves|Zlatan Ibrahimović|Maxwell",
            'Gerard Piqué|Zlatan Ibrahimović|Bastian Schweinsteiger',
            "Cesc Fàbregas|Pedro|Raheem Sterling|Cole Palmer|Willy Caballero|Mateo Kovačić",
            "Xavi|Andrés Iniesta|Gerard Piqué|Dani Alves|Sergio Busquets|Pedro|David Villa|Alexis Sánchez",
        ),
    }),
    (("milan", "bayern", "dortmund", "mbappe"), {
        "chelsea": (
            "Olivier Giroud|Andriy Shevchenko|Fernando Torres|Christian Pulisic|Fikayo Tomori|Marcel Desailly|Michael Essien|Ruben Loftus-Cheek|Tiémoué Bakayoko",
            'Arjen Robben|Michael Ballack|Claudio Pizarro',
            "Christian Pulisic|Pierre-Emerick Aubameyang|Michy Batshuayi|Ian Maatsen",
            "Thiago Silva|Olivier Giroud|N’Golo Kanté|Christopher Nkunku",
        ),
        "real": (
            "Kaká|Clarence Seedorf|David Beckham|Ronaldo Nazário|Brahim Díaz|Theo Hernández|Michael Essien",
            "Toni Kroos|David Alaba|James Rodríguez|Xabi Alonso|Arjen Robben|Álvaro Odriozola",
            "Jude Bellingham|Nuri Şahin|Achraf Hakimi|Christoph Metzelder",
            "Vinícius Júnior|Jude Bellingham|Rodrygo|Antonio Rüdiger|Aurélien Tchouaméni|Eduardo Camavinga|Achraf Hakimi",
        ),
        "arsenal": (
            'Olivier Giroud|Mathieu Flamini|Patrick Vieira|Ismaël Bennacer|Philippe Senderos',
            "Serge Gnabry|Lukas Podolski",
            "Pierre-Emerick Aubameyang|Tomáš Rosický|Henrikh Mkhitaryan|Sokratis Papastathopoulos",
            "William Saliba|Olivier Giroud|Mattéo Guendouzi",
        ),
        "ancelotti": (
            "Kaká|Andrea Pirlo|Paolo Maldini|Clarence Seedorf|Andriy Shevchenko|Gennaro Gattuso|Filippo Inzaghi",
            'Robert Lewandowski|Thomas Müller|Manuel Neuer|Arjen Robben|James Rodríguez|Joshua Kimmich|David Alaba',
            'Jude Bellingham',
            "Vinícius Júnior|Jude Bellingham|Rodrygo|Antonio Rüdiger|Aurélien Tchouaméni|Eduardo Camavinga",
        ),
    }),
)

CLUES.update({
    "city": ("Manchester City", "مانشستر سيتي", "club"),
    "liverpool": ("Liverpool", "ليفربول", "club"),
    "tottenham": ("Tottenham Hotspur", "توتنهام هوتسبير", "club"),
    "monaco": ("Monaco", "موناكو", "club"),
    "roma": ("Roma", "روما", "club"),
    "atletico": ("Atlético Madrid", "أتلتيكو مدريد", "club"),
    "marseille": ("Marseille", "مارسيليا", "club"),
    "lyon": ("Lyon", "ليون", "club"),
    "ronaldo": ("Cristiano Ronaldo", "كريستيانو رونالدو", "player"),
    "neymar": ("Neymar", "نيمار", "player"),
    "salah": ("Mohamed Salah", "محمد صلاح", "player"),
    "klopp": ("Jürgen Klopp", "يورغن كلوب", "coach"),
    "mourinho": ("José Mourinho", "جوزيه مورينيو", "coach"),
    "zidane": ("Zinédine Zidane", "زين الدين زيدان", "coach"),
})

# The pooled columns below have a club or senior national-team connection
# with each named answer. An empty field excludes that pairing from boards.
EXTRA_COLUMNS = ("mbappe", "liverpool", "ronaldo", "neymar", "salah")
EXTRA_ANSWERS = {
    "barcelona": ("Ousmane Dembélé|Antoine Griezmann|Jules Koundé", "Luis Suárez|Philippe Coutinho|Javier Mascherano|Bolo Zenden", "Gerard Piqué|Deco|André Gomes", "Lionel Messi|Luis Suárez|Dani Alves|Andrés Iniesta", "Philippe Coutinho"),
    "bayern": ("Lucas Hernández|Dayot Upamecano|Kingsley Coman|Benjamin Pavard", "Sadio Mané|Xabi Alonso|Thiago Alcântara|Philippe Coutinho", 'James Rodríguez|João Cancelo|Renato Sanches', 'Philippe Coutinho', "Sadio Mané|Thiago Alcântara|Xherdan Shaqiri|Ryan Gravenberch"),
    "inter": ("Marcus Thuram|Benjamin Pavard|Achraf Hakimi", "Philippe Coutinho|Xherdan Shaqiri|Robbie Keane|Mario Balotelli", "Ricardo Quaresma|Luís Figo|João Cancelo", 'Thiago Motta|Achraf Hakimi|Gabriel Barbosa', 'Xherdan Shaqiri'),
    "pep": ('Benjamin Mendy', 'Thiago Alcântara|Raheem Sterling', 'João Cancelo|Bernardo Silva|Gerard Piqué', "Lionel Messi|Dani Alves|Andrés Iniesta|Gabriel Jesus", "Thiago Alcântara"),
}

CORE_COLUMNS = ("juventus", "psg", "united", "chelsea", "messi")
CORE_ANSWERS = {
    "city": ("João Cancelo|Carlos Tevez|Danilo|Patrick Vieira", 'Nicolas Anelka|George Weah', "Carlos Tevez|Peter Schmeichel|Owen Hargreaves|Andy Cole", "Raheem Sterling|Nicolas Anelka|Kevin De Bruyne|Cole Palmer|Mateo Kovačić", "Sergio Agüero|Julián Álvarez|Nicolás Otamendi"),
    "arsenal": ("Thierry Henry|Patrick Vieira|Aaron Ramsey|Wojciech Szczęsny", "Nicolas Anelka|Mikel Arteta|David Luiz|Lassana Diarra", "Robin van Persie|Alexis Sánchez|Danny Welbeck", "Cesc Fàbregas|Olivier Giroud|Ashley Cole|Petr Čech|Kai Havertz|Jorginho", "Thierry Henry|Alexis Sánchez|Cesc Fàbregas|Emiliano Martínez"),
    "real": ("Cristiano Ronaldo|Zinédine Zidane|Álvaro Morata|Fabio Cannavaro", "Ángel Di María|Sergio Ramos|Keylor Navas|David Beckham|Kylian Mbappé", "Cristiano Ronaldo|David Beckham|Raphaël Varane|Casemiro|Ángel Di María", "Eden Hazard|Thibaut Courtois|Claude Makélélé|Ricardo Carvalho|Álvaro Morata", "Ángel Di María|Sergio Ramos|Achraf Hakimi|Keylor Navas"),
    "milan": ("Andrea Pirlo|Filippo Inzaghi|Zlatan Ibrahimović|Leonardo Bonucci", "Zlatan Ibrahimović|Thiago Silva|David Beckham|Ronaldinho|Gianluigi Donnarumma", "Zlatan Ibrahimović|David Beckham|Jaap Stam|Diogo Dalot", "Olivier Giroud|Andriy Shevchenko|Christian Pulisic|Fikayo Tomori", 'Ronaldinho|Zlatan Ibrahimović|Gianluigi Donnarumma'),
    "tottenham": ("Dejan Kulusevski|Rodrigo Bentancur|Edgar Davids", 'Lucas Moura|Serge Aurier|David Ginola', "Dimitar Berbatov|Michael Carrick|Teddy Sheringham|Christian Eriksen", "William Gallas|Gus Poyet|Carlo Cudicini|Timo Werner", "Cristian Romero|Giovani dos Santos|Erik Lamela"),
    "monaco": ("Thierry Henry|Patrice Evra|David Trezeguet|Denis Zakaria", "Kylian Mbappé|Layvin Kurzawa|Jérémy Ménez|Ludovic Giuly", "Patrice Evra|Anthony Martial|Dimitar Berbatov|Radamel Falcao", "Cesc Fàbregas|Radamel Falcao|Tiémoué Bakayoko|Eiður Guðjohnsen", "Thierry Henry|Ludovic Giuly|Javier Saviola|Éric Abidal"),
    "roma": ("Miralem Pjanić|Paulo Dybala|Wojciech Szczęsny|Medhi Benatia", "Jérémy Ménez|Lucas Digne|Georginio Wijnaldum", "Chris Smalling|Romelu Lukaku|Nemanja Matić|Henrikh Mkhitaryan", "Mohamed Salah|Antonio Rüdiger|Romelu Lukaku|Tammy Abraham", 'Paulo Dybala|Lucas Digne|Bojan Krkić'),
    "atletico": ("Álvaro Morata|Mario Mandžukić|Tiago Mendes|Diego Ribas", "Kévin Gameiro|Lucas Hernández|Thiago Motta", 'David de Gea|Radamel Falcao|Diego Forlán', "Fernando Torres|Diego Costa|Álvaro Morata|Thibaut Courtois|João Félix", "Luis Suárez|Antoine Griezmann|Rodrigo De Paul|Julián Álvarez"),
    "marseille": ("Patrice Evra|Didier Deschamps|Fabrizio Ravanelli|Arkadiusz Milik", "Gabriel Heinze|George Weah|Lorik Cana", "Patrice Evra|Gabriel Heinze|Alexis Sánchez|Fabien Barthez", "Didier Drogba|César Azpilicueta|Michy Batshuayi|Bolo Zenden", 'Gabriel Heinze|Alexis Sánchez'),
    "lyon": ("Miralem Pjanić|Fabio Grosso|Tiago Mendes|Mattia De Sciglio", "Bradley Barcola|Hatem Ben Arfa|Grégory Coupet|Ludovic Giuly", "Memphis Depay|Anthony Martial|Rafael da Silva", "Michael Essien|Florent Malouda|Bertrand Traoré", "Memphis Depay|Ludovic Giuly|Éric Abidal"),
    "mourinho": ('Zlatan Ibrahimović|Álvaro Morata|Paulo Dybala', 'Zlatan Ibrahimović|Lassana Diarra', "Wayne Rooney|Zlatan Ibrahimović|Paul Pogba|Marcus Rashford", "Didier Drogba|Frank Lampard|John Terry|Petr Čech|Eden Hazard", "Samuel Eto’o|Zlatan Ibrahimović|Alexis Sánchez|Cesc Fàbregas"),
    "klopp": ('Emre Can|Arthur Melo', 'Georginio Wijnaldum', "Shinji Kagawa", 'Mohamed Salah|Christian Pulisic', "Luis Suárez|Philippe Coutinho|Alexis Mac Allister"),
    "zidane": ('Álvaro Morata|Cristiano Ronaldo', "Sergio Ramos|Keylor Navas", "Raphaël Varane|Casemiro|Cristiano Ronaldo", "Eden Hazard|Thibaut Courtois|Álvaro Morata", "Sergio Ramos|Keylor Navas|Achraf Hakimi"),
}

CLUB_AND_PLAYER_ANSWERS = {
    "city": ('Benjamin Mendy|Bernardo Silva', "Raheem Sterling|James Milner|Mario Balotelli|Robbie Fowler", 'Bernardo Silva|João Cancelo|Rúben Dias', 'Gabriel Jesus|Fernandinho', 'James Milner'),
    "arsenal": ("William Saliba|Olivier Giroud|Mattéo Guendouzi", "Alex Oxlade-Chamberlain|Yossi Benayoun|Jermaine Pennant|Nicolas Anelka", "Cédric Soares", "Gabriel Jesus|David Luiz|Gabriel Martinelli", "Alex Oxlade-Chamberlain"),
    "real": ("Jude Bellingham|Vinícius Júnior|Rodrygo|Aurélien Tchouaméni", "Xabi Alonso|Michael Owen|Álvaro Arbeloa|Fernando Morientes|Steve McManaman", "Karim Benzema|Sergio Ramos|Pepe|Marcelo|Luka Modrić", "Sergio Ramos|Casemiro|Keylor Navas|Éder Militão", ''),
    "milan": ("Olivier Giroud|Theo Hernández|Mike Maignan|Gianluigi Donnarumma", "Mario Balotelli|Fernando Torres|Alberto Aquilani|Suso", 'Kaká|David Beckham', 'Thiago Silva|Gianluigi Donnarumma', ""),
    "tottenham": ("Hugo Lloris|Moussa Sissoko|Tanguy Ndombele", "Robbie Keane|Peter Crouch|Danny Murphy|Neil Ruddock", 'Gareth Bale|Luka Modrić', 'Lucas Moura|Richarlison', 'Dominic Solanke'),
    "monaco": ("Bernardo Silva|Benjamin Mendy|Thomas Lemar|Fabinho", "Fabinho|Takumi Minamino|Fernando Morientes", 'Patrice Evra|Bernardo Silva|João Moutinho', 'Fabinho|Layvin Kurzawa', "Fabinho|Takumi Minamino"),
    "roma": ('Lucas Digne|Georginio Wijnaldum', "Mohamed Salah|Alisson|Fabio Borini|John Arne Riise|Georginio Wijnaldum", 'Paulo Dybala|Nemanja Matić', "Georginio Wijnaldum|Marquinhos", "Edin Džeko|Radja Nainggolan|Alisson|Antonio Rüdiger"),
    "atletico": ('Antoine Griezmann|Thomas Lemar|Lucas Hernández', 'Fernando Torres|Luis Suárez', "João Félix|Álvaro Morata|Tiago Mendes", 'Luis Suárez', ""),
    "marseille": ("Jonathan Clauss|Mattéo Guendouzi|Steve Mandanda|Jordan Veretout", 'Djibril Cissé|Bolo Zenden', 'Patrice Evra', 'Renan Lodi', ""),
    "lyon": ('Bradley Barcola|Corentin Tolisso', "Dejan Lovren|Milan Baroš|Xherdan Shaqiri", 'Karim Benzema', 'Bradley Barcola', "Xherdan Shaqiri|Dejan Lovren"),
    "mourinho": ("Paul Pogba|Raphaël Varane|Hugo Lloris|Karim Benzema", "Mohamed Salah|Glen Johnson|Daniel Sturridge|Joe Cole", "Karim Benzema|Mesut Özil|Ángel Di María|Paul Pogba", "Ángel Di María|Ander Herrera|Leandro Paredes", 'Didier Drogba|Eden Hazard'),
    "klopp": ("Ibrahima Konaté|Georginio Wijnaldum|Ousmane Dembélé", "Mohamed Salah|Virgil van Dijk|Sadio Mané|Trent Alexander-Arnold", 'Diogo Jota', "Philippe Coutinho|Alisson|Roberto Firmino|Fabinho", "Sadio Mané|Roberto Firmino|Virgil van Dijk|Trent Alexander-Arnold"),
    "zidane": ("Sergio Ramos|Raphaël Varane|Karim Benzema|Vinícius Júnior", "", "Karim Benzema|Sergio Ramos|Marcelo|Luka Modrić", "Sergio Ramos|Casemiro|Keylor Navas", ""),
}

base_rows = POOLS[0][1]
POOLS = (*POOLS, (CORE_COLUMNS + EXTRA_COLUMNS, {
    **{key: answers + EXTRA_ANSWERS[key] for key, answers in base_rows.items()},
    **{key: answers + CLUB_AND_PLAYER_ANSWERS[key] for key, answers in CORE_ANSWERS.items()},
}))

CLUES.update({
    "napoli": ("Napoli", "نابولي", "club"),
    "sevilla": ("Sevilla", "إشبيلية", "club"),
    "valencia": ("Valencia", "فالنسيا", "club"),
    "leverkusen": ("Bayer Leverkusen", "باير ليفركوزن", "club"),
    "luis-enrique": ("Luis Enrique", "لويس إنريكي", "coach"),
    "deschamps": ("Didier Deschamps", "ديدييه ديشان", "coach"),
    "flick": ("Hansi Flick", "هانزي فليك", "coach"),
    "beckham": ("David Beckham", "ديفيد بيكهام", "player"),
    "ronaldinho": ("Ronaldinho", "رونالدينيو", "player"),
    "henry": ("Thierry Henry", "تييري هنري", "player"),
    "pirlo": ("Andrea Pirlo", "أندريا بيرلو", "player"),
    "zlatan": ("Zlatan Ibrahimović", "زلاتان إبراهيموفيتش", "player"),
    "cruyff": ("Johan Cruyff", "يوهان كرويف", "player"),
    "maradona": ("Diego Maradona", "دييغو مارادونا", "player"),
})

CLUE_IMAGES = {
    "luis-enrique": "players/wiki-luis_enrique.jpg",
    "deschamps": "players/wiki-didier_deschamps.jpg",
    "flick": "players/wiki-hansi_flick.jpg",
    "beckham": "players/wiki-david_beckham.jpg",
    "ronaldinho": "players/wiki-ronaldinho.jpg",
    "henry": "players/wiki-thierry_henry.jpg",
    "pirlo": "players/wiki-andrea_pirlo.jpg",
    "zlatan": "players/wiki-zlatan_ibrahimovi.jpg",
    "cruyff": "players/wiki-johan_cruyff.jpg",
    "maradona": "players/wiki-diego_maradona.jpg",
}


EXPANSION = json.loads(Path(__file__).with_name("xo-expansion.json").read_text(encoding="utf-8"))
for key, entry in EXPANSION.items():
    if "name" in entry:
        CLUES[key] = (entry["name"], entry["ar"], entry["kind"])
        CLUE_IMAGES[key] = entry["image"]


def clue_image(key):
    if key in CLUE_IMAGES:
        return CLUE_IMAGES[key]
    extension = "jpg" if key in ("mbappe", "ronaldo", "neymar", "salah") or CLUES[key][2] == "coach" else "png"
    return f"clues/{key}.{extension}"
