"""Consigliere: dalle poche risposte dell'utente a regime, accantonamento, scadenze e uso della liquidità.

Non aggiunge logica fiscale: orchestra il motore già testato (`calcola_anno`, `simula`) su due scenari
(forfettario e ordinario) e confronta i risultati sugli stessi anni.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import pandas as pd

from .params import PARAMETRI_2026, Parametri
from .scadenzario import Pagamento
from .simulazione import PRODOTTI_ESEMPIO, Risultato, Scenario, serie_ricavi_mensili, simula
from .tasse import Profilo

SITUAZIONI = ("unica", "dipendente", "pensionato")

MESI_IT = (
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
)

# Soglia di reddito da lavoro dipendente o pensione (anno precedente) oltre la quale non si accede al
# forfettario: 35.000 euro per il 2026 (Legge di Bilancio 2026), 30.000 euro di regola negli anni successivi.
SOGLIA_DIPENDENTE_2026 = 35_000.0
SOGLIA_DIPENDENTE_ORDINARIA = 30_000.0


def soglia_dipendente(anno_inizio: int) -> float:
    return SOGLIA_DIPENDENTE_2026 if anno_inizio <= 2026 else SOGLIA_DIPENDENTE_ORDINARIA


def euro(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def nome_mese(anno: int, mese: int) -> str:
    return f"{MESI_IT[mese - 1]} {anno}"


@dataclass(frozen=True)
class Richiesta:
    coefficiente: float
    gestione: str                              # separata | commercianti | artigiani
    anno_inizio: int
    mese_inizio: int
    anni: int
    ricavo_mensile_iniziale: float
    crescita_mensile: float = 0.0
    tetto_mensile: float | None = None
    nuova_attivita: bool = True                # aliquota 5% per i primi 5 anni
    situazione: str = "unica"                  # unica | dipendente | pensionato
    reddito_altro: float = 0.0                 # lordo annuo da lavoro dipendente o pensione
    costi_pct: float | None = None             # None = costi impliciti del forfettario (1 - coefficiente)
    riduzione_inps_35: bool = False
    addizionale_regionale: float = 0.015
    addizionale_comunale: float = 0.005
    max_vincolo_mesi: int = 12                 # per quanto tempo si accetta di vincolare i soldi
    prodotti: dict[int, float] = field(default_factory=lambda: dict(PRODOTTI_ESEMPIO))
    tasso_conto_corrente: float = 0.0
    # Costo annuo stimato del commercialista (tenuta contabilità e dichiarazioni). Ipotesi modificabile:
    # intervalli rilevati da fonti commerciali 2026 (forfettario 400-1.100 euro, semplificato 950-2.800 euro).
    costo_gestione_forfettario: float = 600.0
    costo_gestione_ordinario: float = 1_200.0

    @property
    def costi(self) -> float:
        return (1.0 - self.coefficiente) if self.costi_pct is None else self.costi_pct


@dataclass
class Consiglio:
    regime: str                                # regime consigliato
    ris: Risultato                             # simulazione del regime consigliato
    ris_alternativa: Risultato | None          # simulazione dell'altro regime (None se non disponibile)
    forfettario_disponibile: bool
    anni_forfettario: int                      # anni in cui il forfettario resta applicabile
    anni_confronto: int
    carico_forfettario: float | None           # imposte + contributi sugli anni di confronto
    carico_ordinario: float
    gestione_forfettario: float                # commercialista stimato sugli anni di confronto
    gestione_ordinario: float
    risparmio: float                           # differenza di costo totale fra i due regimi (>= 0)
    costi_pareggio: float | None               # costi (% fatturato) oltre i quali l'ordinario conviene (inf = mai)
    ricavi_annui: list[float]
    accantonamento_pct: list[float]            # quota di ogni incasso da mettere da parte, per anno
    accantonamento_mensile: list[float]        # euro medi al mese da mettere da parte, per anno
    prima_scadenza: Pagamento | None
    prima_scadenza_imposte: Pagamento | None
    calendario: pd.DataFrame
    destinazioni: pd.DataFrame
    suggerimenti: list[str]
    avvisi: list[str]


# ---------------------------------------------------------------------------------------- costruzione
def _profilo(req: Richiesta, regime: str, *, costi: float | None = None, **modifiche) -> Profilo:
    altra_copertura = req.situazione in ("dipendente", "pensionato")
    base = Profilo(
        regime=regime,
        gestione=req.gestione,
        coefficiente=req.coefficiente,
        costi_pct=req.costi if costi is None else costi,
        startup=req.nuova_attivita,
        riduzione_inps_35=req.riduzione_inps_35,
        altra_copertura=altra_copertura,
        altri_redditi=req.reddito_altro if altra_copertura else 0.0,
        addizionale_regionale=req.addizionale_regionale,
        addizionale_comunale=req.addizionale_comunale,
    )
    return replace(base, **modifiche) if modifiche else base


def _scenario(req: Richiesta) -> Scenario:
    mesi_primo_anno = 13 - req.mese_inizio
    mesi = mesi_primo_anno + 12 * (req.anni - 1)
    prodotti = {m: t for m, t in req.prodotti.items() if m <= req.max_vincolo_mesi}
    if 0 not in prodotti:
        prodotti[0] = req.tasso_conto_corrente   # senza deposito libero resta il conto corrente
    return Scenario(
        anno_inizio=req.anno_inizio,
        mese_inizio=req.mese_inizio,
        anni=req.anni,
        ricavi_mensili=serie_ricavi_mensili(
            req.ricavo_mensile_iniziale, req.crescita_mensile, mesi, req.tetto_mensile
        ),
        prodotti=prodotti,
        tasso_conto_corrente=req.tasso_conto_corrente,
    )


def anni_forfettario(ricavi_annui: list[float], mesi_attivi: list[int], p: Parametri = PARAMETRI_2026) -> int:
    """Quanti anni, dal primo, il forfettario resta applicabile con i ricavi previsti.

    Sopra 85.000 euro (ragguagliati ad anno) si esce dall'anno successivo; sopra 100.000 euro dall'anno stesso.
    """
    n = 0
    for r, m in zip(ricavi_annui, mesi_attivi):
        annualizzato = r * 12.0 / m if m else 0.0
        if annualizzato > p.soglia_uscita_immediata:
            break
        n += 1
        if annualizzato > p.soglia_ricavi_forfettario:
            break
    return n


def _carico(ris: Risultato, anni: int) -> float:
    return sum(e.carico_totale for e in ris.esiti[:anni])


def _costi_pareggio(req: Richiesta, scenario: Scenario, soglia: float, anni: int, p: Parametri) -> float | None:
    """Costi (% fatturato) per cui imposte e contributi dell'ordinario eguagliano `soglia`.

    Restituisce 0.0 se l'ordinario costa meno già senza costi, `math.inf` se non conviene nemmeno con costi
    altissimi (95% del fatturato).
    """

    def carico_ord(c: float) -> float:
        return _carico(simula(_profilo(req, "ordinario", costi=c), scenario, p), anni)

    if carico_ord(0.0) <= soglia:
        return 0.0
    if carico_ord(0.95) > soglia:
        return math.inf
    lo, hi = 0.0, 0.95
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if carico_ord(mid) > soglia:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def _calendario(pagamenti: list[Pagamento]) -> pd.DataFrame:
    righe: dict[str, dict] = {}
    for pg in sorted(pagamenti, key=lambda x: x.t):
        r = righe.setdefault(
            pg.periodo, {"periodo": pg.periodo, "quando": nome_mese(pg.anno, pg.mese), "importo": 0.0, "voci": []}
        )
        r["importo"] += pg.importo
        voce = pg.voce.split(" (anno")[0]
        if voce not in r["voci"]:
            r["voci"].append(voce)
    df = pd.DataFrame(list(righe.values()))
    if df.empty:
        return pd.DataFrame(columns=["periodo", "quando", "importo", "voci"])
    df["voci"] = df["voci"].map(lambda v: ", ".join(v))
    return df


def _destinazioni(ris: Risultato) -> pd.DataFrame:
    a = ris.allocazioni
    if a.empty:
        return pd.DataFrame(columns=["dove", "importo", "mesi_medi", "interessi_netti"])
    g = a.assign(peso=a["importo"] * a["mesi_fermi"]).groupby("prodotto", sort=False).agg(
        importo=("importo", "sum"), peso=("peso", "sum"), interessi_netti=("interessi_netti", "sum"),
    )
    g["mesi_medi"] = g["peso"] / g["importo"]
    g = g.reset_index().rename(columns={"prodotto": "dove"})
    ordine = {"libero": 0}
    g["_o"] = g["dove"].map(lambda d: ordine.get(d, 1 + int("".join(c for c in d if c.isdigit()) or 0)))
    return g.sort_values("_o")[["dove", "importo", "mesi_medi", "interessi_netti"]].reset_index(drop=True)


def _accantonamento_mensile(ris: Risultato, anni: int, anno_inizio: int) -> list[float]:
    tl = ris.timeline
    out = []
    for k in range(anni):
        sel = tl[tl["periodo"].str.startswith(str(anno_inizio + k)) & (tl["incassi"] > 0)]
        out.append(float(sel["accantonato"].mean()) if len(sel) else 0.0)
    return out


# ---------------------------------------------------------------------------------------- consiglio
def consiglia(req: Richiesta, p: Parametri = PARAMETRI_2026) -> Consiglio:
    if req.situazione not in SITUAZIONI:
        raise ValueError(f"Situazione non valida: {req.situazione}")
    scenario = _scenario(req)
    avvisi: list[str] = []
    suggerimenti: list[str] = []

    ris_ord = simula(_profilo(req, "ordinario"), scenario, p)
    ris_forf = simula(_profilo(req, "forfettario"), scenario, p)
    ricavi = [e.ricavi for e in ris_ord.esiti]
    mesi = [scenario.mesi_attivi(k) for k in range(req.anni)]

    # --- Il forfettario è disponibile? ---
    m_forf = anni_forfettario(ricavi, mesi, p)
    escluso_dipendente = req.situazione != "unica" and req.reddito_altro > soglia_dipendente(req.anno_inizio)
    if escluso_dipendente:
        m_forf = 0
        avvisi.append(
            f"Con redditi da lavoro dipendente o pensione sopra {euro(soglia_dipendente(req.anno_inizio))} euro "
            "nell'anno precedente il forfettario non è accessibile (salvo cessazione del rapporto di lavoro)."
        )
    forf_disponibile = m_forf > 0
    if forf_disponibile and m_forf < req.anni:
        avvisi.append(
            f"Con la crescita prevista superi 85.000 euro di ricavi: il forfettario vale fino al "
            f"{req.anno_inizio + m_forf - 1}. Dall'anno dopo si passa all'ordinario: i numeri degli anni "
            "successivi, se scegli il forfettario, sono solo indicativi."
        )

    # --- Confronto sugli stessi anni ---
    anni_conf = min(m_forf, req.anni) if forf_disponibile else req.anni
    carico_ord = _carico(ris_ord, anni_conf)
    carico_forf = _carico(ris_forf, anni_conf) if forf_disponibile else None
    gest_ord = req.costo_gestione_ordinario * anni_conf
    gest_forf = req.costo_gestione_forfettario * anni_conf
    totale_ord = carico_ord + gest_ord
    totale_forf = carico_forf + gest_forf if forf_disponibile else None
    if forf_disponibile and totale_forf <= totale_ord:
        regime, ris, alt = "forfettario", ris_forf, ris_ord
    elif forf_disponibile:
        regime, ris, alt = "ordinario", ris_ord, ris_forf
    else:
        regime, ris, alt = "ordinario", ris_ord, None
    risparmio = abs(totale_ord - totale_forf) if forf_disponibile else 0.0
    # l'ordinario pareggia quando imposte+contributi ordinari = totale forfettario - commercialista ordinario
    costi_pareggio = (
        _costi_pareggio(req, scenario, totale_forf - gest_ord, anni_conf, p) if forf_disponibile else None
    )

    # --- Suggerimenti calcolati ---
    if regime == "forfettario" and req.gestione in ("artigiani", "commercianti") and not req.riduzione_inps_35:
        ris_rid = simula(_profilo(req, "forfettario", riduzione_inps_35=True), scenario, p)
        risp = (_carico(ris_forf, req.anni) - _carico(ris_rid, req.anni)) / req.anni
        if risp > 1:
            suggerimenti.append(
                f"Puoi chiedere all'INPS la riduzione del 35% sui contributi: risparmieresti circa "
                f"{euro(risp)} euro l'anno (in cambio di una pensione futura più bassa)."
            )
    if regime == "forfettario" and not req.nuova_attivita:
        ris_nuova = simula(_profilo(req, "forfettario", startup=True), scenario, p)
        risp = (_carico(ris_forf, req.anni) - _carico(ris_nuova, req.anni)) / req.anni
        if risp > 1:
            suggerimenti.append(
                f"Se è davvero una nuova attività (nessuna altra partita IVA negli ultimi 3 anni e nessuna "
                f"prosecuzione di un'attività precedente) l'aliquota è 5% e non 15%: circa "
                f"{euro(risp)} euro l'anno in meno."
            )

    # --- Avvisi del motore, senza duplicati ---
    for a in ris.avvisi:
        if a not in avvisi:
            avvisi.append(a)

    pagamenti = sorted(ris.pagamenti, key=lambda x: x.t)
    return Consiglio(
        regime=regime,
        ris=ris,
        ris_alternativa=alt,
        forfettario_disponibile=forf_disponibile,
        anni_forfettario=m_forf,
        anni_confronto=anni_conf,
        carico_forfettario=carico_forf,
        carico_ordinario=carico_ord,
        gestione_forfettario=gest_forf,
        gestione_ordinario=gest_ord,
        risparmio=risparmio,
        costi_pareggio=costi_pareggio,
        ricavi_annui=ricavi,
        accantonamento_pct=[e.pressione for e in ris.esiti],
        accantonamento_mensile=_accantonamento_mensile(ris, req.anni, req.anno_inizio),
        prima_scadenza=pagamenti[0] if pagamenti else None,
        prima_scadenza_imposte=next((x for x in pagamenti if x.categoria == "imposta"), None),
        calendario=_calendario(pagamenti),
        destinazioni=_destinazioni(ris),
        suggerimenti=suggerimenti,
        avvisi=avvisi,
    )
