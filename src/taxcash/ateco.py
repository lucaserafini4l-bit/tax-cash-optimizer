"""Dal codice ATECO (o dall'attività) al coefficiente di redditività e alla gestione INPS probabile.

Fonte dei coefficienti: Allegato 4 alla L. 190/2014 (come modificato dalla L. 145/2018), controllato su
due fonti indipendenti (Fiscozen, InformazioneFiscale). La tabella è parametrata sui codici ATECO 2007.
Dal 2025 si usano i codici ATECO 2025, ma in attesa di una nuova tabella il coefficiente continua a
seguire la classificazione ATECO 2007 della stessa attività: per questo qui si ragiona per divisione e
gruppo (prime 2-3 cifre) e, nei pochi casi ambigui, si chiede di che attività si tratta.

La gestione INPS dipende dall'attività effettivamente svolta, non dal solo codice: quella restituita è
un'indicazione di partenza, modificabile.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Gruppo:
    chiave: str
    nome: str
    coefficiente: float


GRUPPI: dict[str, Gruppo] = {
    g.chiave: g
    for g in (
        Gruppo("alimentari", "Industrie alimentari e delle bevande", 0.40),
        Gruppo("commercio", "Commercio all'ingrosso e al dettaglio", 0.40),
        Gruppo("ambulante_alimentari", "Commercio ambulante di prodotti alimentari e bevande", 0.40),
        Gruppo("ambulante_altri", "Commercio ambulante di altri prodotti", 0.54),
        Gruppo("costruzioni", "Costruzioni", 0.86),
        Gruppo("immobiliare", "Attività immobiliari", 0.86),
        Gruppo("intermediari", "Intermediari del commercio", 0.62),
        Gruppo("alloggio_ristorazione", "Servizi di alloggio e di ristorazione", 0.40),
        Gruppo("professioni", "Attività professionali, scientifiche, tecniche, sanitarie, di istruzione", 0.78),
        Gruppo("altre", "Altre attività economiche", 0.67),
    )
}

# Divisione ATECO (2 cifre) -> gruppo. 46 e 47 sono trattate a parte (dipendono dal gruppo a 3-4 cifre).
_DIVISIONE_GRUPPO: dict[int, str] = {}
for _d in (10, 11):
    _DIVISIONE_GRUPPO[_d] = "alimentari"
_DIVISIONE_GRUPPO[45] = "commercio"
for _d in (41, 42, 43):
    _DIVISIONE_GRUPPO[_d] = "costruzioni"
_DIVISIONE_GRUPPO[68] = "immobiliare"
for _d in (55, 56):
    _DIVISIONE_GRUPPO[_d] = "alloggio_ristorazione"
for _d in (64, 65, 66, 69, 70, 71, 72, 73, 74, 75, 85, 86, 87, 88):
    _DIVISIONE_GRUPPO[_d] = "professioni"
for _d in (
    1, 2, 3, 5, 6, 7, 8, 9, *range(12, 34), 35, 36, 37, 38, 39, 49, 50, 51, 52, 53,
    58, 59, 60, 61, 62, 63, 77, 78, 79, 80, 81, 82, 84, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99,
):
    _DIVISIONE_GRUPPO[_d] = "altre"

# Gestione INPS probabile per divisione (indicazione di partenza, da confermare).
_GESTIONE_DIVISIONE: dict[int, str] = {}
for _d in (10, 11, *range(12, 34), 41, 42, 43, 49, 95, 96):
    _GESTIONE_DIVISIONE[_d] = "artigiani"
for _d in (45, 46, 47, 55, 56, 68, 35, 36, 37, 38, 39, 50, 51, 52, 53, 77, 78, 79, 80, 81, 82, 92, 93):
    _GESTIONE_DIVISIONE[_d] = "commercianti"
for _d in (58, 59, 60, 61, 62, 63, 70, 72, 73, 74, 85, 86, 87, 88, 90, 91):
    _GESTIONE_DIVISIONE[_d] = "separata"

# Divisioni i cui contributi non sono modellati.
_FUORI_AMBITO: dict[int, str] = {
    1: "Agricoltura, silvicoltura e pesca hanno regole previdenziali e fiscali proprie.",
    2: "Agricoltura, silvicoltura e pesca hanno regole previdenziali e fiscali proprie.",
    3: "Agricoltura, silvicoltura e pesca hanno regole previdenziali e fiscali proprie.",
    64: "Servizi finanziari: i contributi (Enasarco, gestioni dedicate) non sono modellati.",
    65: "Servizi assicurativi: i contributi (Enasarco, gestioni dedicate) non sono modellati.",
    66: "Intermediazione finanziaria e assicurativa: i contributi (Enasarco, gestioni dedicate) non sono modellati.",
    84: "L'amministrazione pubblica non è un'attività da partita IVA.",
    97: "Attività di famiglie e convivenze come datori di lavoro: non applicabile.",
    98: "Attività di famiglie e convivenze: non applicabile.",
    99: "Organizzazioni extraterritoriali: non applicabile.",
}

# Divisioni in cui molti professionisti hanno una cassa previdenziale privata (avvocati, commercialisti,
# consulenti del lavoro, ingegneri, architetti, geometri, medici, psicologi, veterinari...).
_DIVISIONI_CON_CASSA = {69, 71, 75, 86}

MOTIVO_CASSA = (
    "Con una cassa previdenziale privata (avvocati, commercialisti, consulenti del lavoro, ingegneri, "
    "architetti, geometri, medici, psicologi, veterinari...) i contributi si versano alla cassa e hanno "
    "regole proprie: questo strumento non li modella."
)


@dataclass(frozen=True)
class Classificazione:
    divisione: int | None
    gruppo: Gruppo | None = None
    gestione: str | None = None            # separata | commercianti | artigiani
    fuori_ambito: str | None = None        # motivo, se non modellabile
    serve: str | None = None               # chiarimento necessario: "ambulante" | "intermediario" | "cassa"
    errore: str | None = None
    note: tuple[str, ...] = ()

    @property
    def coefficiente(self) -> float | None:
        return self.gruppo.coefficiente if self.gruppo else None

    @property
    def completa(self) -> bool:
        """True se la classificazione è definitiva (anche quando l'esito è «fuori ambito»)."""
        return self.errore is None and self.serve is None and (self.gruppo is not None or bool(self.fuori_ambito))


def solo_cifre(codice: str) -> str:
    return re.sub(r"\D", "", codice or "")


def classifica(codice: str, scelta: str | None = None) -> Classificazione:
    """Classifica un codice ATECO (2007 o 2025, anche parziale: bastano le prime 2-4 cifre).

    `scelta` risponde all'eventuale chiarimento richiesto (`serve`):
      - "ambulante": "no" (negozio o online), "alimentari", "altri"
      - "intermediario": "si" (agente, rappresentante, mediatore del commercio), "no"
      - "cassa": "si" (iscritto a una cassa privata), "no"
    """
    cifre = solo_cifre(codice)
    if len(cifre) < 2:
        return Classificazione(None, errore="Inserisci almeno le prime due cifre del codice ATECO.")
    div = int(cifre[:2])
    terza = cifre[2] if len(cifre) > 2 else ""
    quarta = cifre[3] if len(cifre) > 3 else ""

    if div in _FUORI_AMBITO:
        return Classificazione(div, fuori_ambito=_FUORI_AMBITO[div])
    if div not in _DIVISIONE_GRUPPO and div not in (46, 47):
        return Classificazione(div, errore=f"Divisione ATECO {div:02d} non riconosciuta nella tabella dei coefficienti.")

    gestione = _GESTIONE_DIVISIONE.get(div)

    # --- Commercio all'ingrosso (46) ---
    if div == 46:
        if terza == "1":
            return Classificazione(div, GRUPPI["intermediari"], "commercianti")
        if terza in {"2", "3", "4", "5", "6", "7", "8", "9"}:
            return Classificazione(div, GRUPPI["commercio"], "commercianti")
        if scelta == "si":
            return Classificazione(div, GRUPPI["intermediari"], "commercianti")
        if scelta == "no":
            return Classificazione(div, GRUPPI["commercio"], "commercianti")
        return Classificazione(div, serve="intermediario")

    # --- Commercio al dettaglio (47) ---
    if div == 47:
        if terza in {"1", "2", "3", "4", "5", "6", "7", "9"}:
            return Classificazione(div, GRUPPI["commercio"], "commercianti")
        if terza == "8":
            if quarta == "1":
                return Classificazione(div, GRUPPI["ambulante_alimentari"], "commercianti")
            if quarta in {"2", "9"}:
                return Classificazione(div, GRUPPI["ambulante_altri"], "commercianti")
        if scelta == "no":
            return Classificazione(div, GRUPPI["commercio"], "commercianti")
        if scelta == "alimentari":
            return Classificazione(div, GRUPPI["ambulante_alimentari"], "commercianti")
        if scelta == "altri":
            return Classificazione(div, GRUPPI["ambulante_altri"], "commercianti")
        return Classificazione(div, serve="ambulante")

    # --- Professioni con possibile cassa privata ---
    if div in _DIVISIONI_CON_CASSA:
        if scelta == "si":
            return Classificazione(div, GRUPPI["professioni"], fuori_ambito=MOTIVO_CASSA)
        if scelta != "no":
            return Classificazione(div, serve="cassa")
        # nessuna cassa: Gestione Separata
        return Classificazione(div, GRUPPI["professioni"], "separata")

    note: list[str] = []
    if div == 68 and terza == "2":
        note.append("Gli affitti di immobili propri possono non richiedere iscrizione INPS: verifica con un commercialista.")
    if div in (55, 93):
        note.append("Se l'attività non è svolta in forma imprenditoriale i contributi INPS possono non essere dovuti: verifica.")
    return Classificazione(div, GRUPPI[_DIVISIONE_GRUPPO[div]], gestione, note=tuple(note))


@dataclass(frozen=True)
class Attivita:
    nome: str
    ateco: str                    # codice ATECO 2007 di riferimento (a 2-4 cifre)
    scelta: str | None = None
    gestione: str | None = None   # forza la gestione INPS quando l'attività differisce dal default della divisione


ATTIVITA: tuple[Attivita, ...] = (
    # Digitale, consulenza, creativi
    Attivita("Sviluppatore software / programmatore", "62.01"),
    Attivita("Consulente informatico / sistemista", "62.02"),
    Attivita("Web designer / grafico / designer", "74.10"),
    Attivita("Social media manager / marketing digitale", "73.11"),
    Attivita("Consulente aziendale / di direzione (senza albo)", "70.22"),
    Attivita("Traduttore / interprete", "74.30"),
    Attivita("Fotografo", "74.20"),
    Attivita("Videomaker / produzione video", "59.11"),
    Attivita("Formatore / insegnante privato / ripetizioni", "85.59"),
    Attivita("Istruttore sportivo / personal trainer (corsi)", "85.51"),
    # Commercio e servizi
    Attivita("E-commerce / vendita online", "47.91"),
    Attivita("Negozio al dettaglio", "47.71"),
    Attivita("Venditore ambulante di alimenti e bevande", "47.81"),
    Attivita("Venditore ambulante di altri prodotti", "47.82"),
    Attivita("Agente di commercio / rappresentante", "46.1"),
    Attivita("Bar / ristorante / pizzeria", "56.10"),
    Attivita("B&B / affittacamere", "55.20"),
    Attivita("Agente immobiliare / mediatore", "68.31"),
    # Artigiani
    Attivita("Parrucchiere / estetista", "96.02"),
    Attivita("Elettricista / idraulico / installatore", "43.2"),
    Attivita("Muratore / imbianchino / edilizia", "43.99"),
    Attivita("Autotrasportatore conto terzi", "49.41"),
    Attivita("Meccanico / carrozziere", "45.20", gestione="artigiani"),
    Attivita("Panificatore / pasticcere / produzione alimentare", "10.71"),
    Attivita("Artigiano manifatturiero (falegname, sarto, ceramista...)", "31.09"),
    # Professioni con cassa previdenziale privata: non modellate
    Attivita("Avvocato", "69.10", scelta="si"),
    Attivita("Commercialista / consulente del lavoro", "69.20", scelta="si"),
    Attivita("Ingegnere / architetto / geometra", "71.1", scelta="si"),
    Attivita("Medico / odontoiatra", "86.2", scelta="si"),
    Attivita("Psicologo / infermiere / biologo", "86.9", scelta="si"),
    Attivita("Veterinario", "75.00", scelta="si"),
)


def classifica_attivita(att: Attivita) -> Classificazione:
    cl = classifica(att.ateco, att.scelta)
    if att.gestione and cl.gruppo is not None and cl.fuori_ambito is None:
        cl = Classificazione(cl.divisione, cl.gruppo, att.gestione, cl.fuori_ambito, cl.serve, cl.errore, cl.note)
    return cl


def costi_impliciti(coefficiente: float) -> float:
    """Costi che il forfettario riconosce implicitamente: 100% meno il coefficiente di redditività."""
    return 1.0 - coefficiente


# Gestione INPS di partenza quando si sceglie un intero settore al posto di un'attività.
GESTIONE_GRUPPO: dict[str, str] = {
    "alimentari": "artigiani",
    "commercio": "commercianti",
    "ambulante_alimentari": "commercianti",
    "ambulante_altri": "commercianti",
    "costruzioni": "artigiani",
    "immobiliare": "commercianti",
    "intermediari": "commercianti",
    "alloggio_ristorazione": "commercianti",
    "professioni": "separata",
    "altre": "artigiani",
}


def classifica_gruppo(chiave: str) -> Classificazione:
    """Classificazione di un intero settore della tabella (per chi non trova la propria attività)."""
    g = GRUPPI[chiave]
    return Classificazione(None, g, GESTIONE_GRUPPO[chiave])
