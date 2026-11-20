"""Tasse partita IVA in cinque domande. Avvio con `streamlit run app.py`."""

from __future__ import annotations

import math
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import pandas as pd
import streamlit as st

from taxcash.ateco import (
    ATTIVITA,
    GRUPPI,
    MOTIVO_CASSA,
    Classificazione,
    classifica,
    classifica_attivita,
    classifica_gruppo,
    costi_impliciti,
)
from taxcash.consigliere import MESI_IT, Richiesta, consiglia, euro, soglia_dipendente
from taxcash.simulazione import PRODOTTI_ESEMPIO, serie_ricavi_mensili

st.set_page_config(
    page_title="Tasse partita IVA 2026: quanto accantonare e cosa fare con i soldi",
    page_icon="🧾",
    layout="centered",
)

GESTIONI = {
    "separata": "Gestione Separata (professionisti senza cassa)",
    "commercianti": "Commercianti (commercio, turismo, servizi)",
    "artigiani": "Artigiani (attività manuali o di produzione)",
}
CRESCITE = {
    "Resta stabile": 0.0,
    "Cresce piano (+1% al mese)": 0.01,
    "Cresce in fretta (+3% al mese)": 0.03,
}
VINCOLI = {
    "Mi servono sempre disponibili": 0,
    "Posso vincolarli fino a 6 mesi": 6,
    "Posso vincolarli fino a 12 mesi": 12,
    "Posso vincolarli fino a 24 mesi": 24,
}
SITUAZIONI = {"Solo la partita IVA": "unica", "Sono dipendente": "dipendente", "Sono pensionato": "pensionato"}


def pct(x: float, dec: int = 0) -> str:
    return f"{x * 100:.{dec}f}%".replace(".", ",")


def eur(x: float) -> str:
    return f"{euro(x)} €"


def n0(v: float) -> str:
    return euro(v)


def n1(v: float) -> str:
    return f"{v:.1f}".replace(".", ",")


st.title("Quante tasse pagherai con la partita IVA?")
st.write(
    "Rispondi a cinque domande. Ti diciamo **quale regime ti conviene**, **quanto mettere da parte ogni mese**, "
    "**quando paghi** e **cosa fare con i soldi** mentre aspetti la scadenza."
)

# ============================================================ 1. Attività
st.subheader("1. Che attività svolgi?")
modo = st.radio(
    "Come vuoi indicarla",
    ["Scegli dall'elenco", "Ho il codice ATECO", "Scegli il settore"],
    horizontal=True,
    label_visibility="collapsed",
)
cl: Classificazione | None = None
if modo == "Scegli dall'elenco":
    nomi = [a.nome for a in ATTIVITA]
    scelto = st.selectbox(
        "Attività", nomi, index=None, placeholder="Cerca la tua attività (es. sviluppatore, e-commerce, parrucchiere)"
    )
    if scelto:
        cl = classifica_attivita(ATTIVITA[nomi.index(scelto)])
elif modo == "Ho il codice ATECO":
    codice = st.text_input("Codice ATECO (bastano le prime 2-4 cifre)", placeholder="es. 62.01.00")
    if codice.strip():
        cl = classifica(codice)
        if cl.serve == "ambulante":
            r = st.radio(
                "Vendi in forma ambulante (mercati, fiere)?",
                ["No: negozio o online", "Sì: alimenti e bevande", "Sì: altri prodotti"],
            )
            cl = classifica(codice, {"No: negozio o online": "no", "Sì: alimenti e bevande": "alimentari"}.get(r, "altri"))
        elif cl.serve == "intermediario":
            r = st.radio(
                "Fai da intermediario (agente, rappresentante, mediatore)?", ["Sì", "No: vendo all'ingrosso in proprio"]
            )
            cl = classifica(codice, "si" if r == "Sì" else "no")
        elif cl.serve == "cassa":
            r = st.radio(
                "Sei iscritto a una cassa previdenziale privata (avvocati, commercialisti, ingegneri, medici...)?",
                ["No", "Sì"],
            )
            cl = classifica(codice, "si" if r == "Sì" else "no")
else:
    chiavi = list(GRUPPI)
    k = st.selectbox(
        "Settore",
        chiavi,
        index=None,
        format_func=lambda c: f"{GRUPPI[c].nome} (coefficiente {pct(GRUPPI[c].coefficiente)})",
        placeholder="Scegli il settore più vicino alla tua attività",
    )
    if k:
        cl = classifica_gruppo(k)
        if k == "professioni":
            cassa = st.radio("Sei iscritto a una cassa previdenziale privata?", ["No", "Sì"], horizontal=True)
            if cassa == "Sì":
                cl = Classificazione(None, GRUPPI[k], fuori_ambito=MOTIVO_CASSA)

if cl is None:
    st.info("Scegli la tua attività per continuare.")
    st.stop()
if cl.errore:
    st.error(cl.errore)
    st.stop()
if cl.fuori_ambito:
    st.warning(
        f"**Questo caso non è coperto.** {cl.fuori_ambito} "
        "Per le stime rivolgiti a un commercialista o alla tua cassa."
    )
    st.stop()

coef = cl.coefficiente
with st.container(border=True):
    st.markdown(f"**Coefficiente di redditività: {pct(coef)}** · {cl.gruppo.nome}")
    ordine = list(GESTIONI)
    gestione = st.selectbox(
        "Contributi INPS (dedotti dall'attività: correggi se diversi)",
        ordine,
        index=ordine.index(cl.gestione),
        format_func=GESTIONI.get,
        help=(
            "Dipende dall'attività concreta: professionisti senza cassa → Gestione Separata; attività manuali o di "
            "produzione → Artigiani; commercio, turismo e servizi → Commercianti."
        ),
    )
    for nota in cl.note:
        st.caption(nota)
    st.caption(
        "Il coefficiente lo fissa la legge in base all'attività (classificazione ATECO 2007 corrispondente, anche "
        "se il tuo codice è ATECO 2025): non è una scelta. Controllalo nel cassetto fiscale o con un commercialista."
    )

# ============================================================ 2. Inizio e durata
st.subheader("2. Quando parti e per quanto tempo vuoi pianificare?")
oggi = date.today()
prossimo = date(oggi.year + (oggi.month == 12), oggi.month % 12 + 1, 1)
c1, c2, c3 = st.columns(3)
mese_nome = c1.selectbox("Mese di inizio", MESI_IT, index=prossimo.month - 1, format_func=str.capitalize)
anni_opz = [oggi.year, oggi.year + 1, oggi.year + 2]
anno_inizio = c2.selectbox("Anno", anni_opz, index=anni_opz.index(prossimo.year))
anni = c3.slider("Anni da pianificare", 2, 5, 3)
mese_inizio = MESI_IT.index(mese_nome) + 1
nuova = st.radio(
    "È una nuova attività?",
    ["Sì, non ho avuto altre partite IVA negli ultimi 3 anni", "No, ho già o ho avuto una partita IVA"],
    help=(
        "Nel forfettario i primi 5 anni hanno aliquota 5% invece di 15%, ma solo per una vera nuova attività: nessuna "
        "altra attività autonoma negli ultimi 3 anni e nessuna prosecuzione di un'attività precedente o di un lavoro "
        "da dipendente svolto per lo stesso datore di lavoro."
    ),
).startswith("Sì")

# ============================================================ 3. Fatturato
st.subheader("3. Quanto pensi di fatturare?")
c1, c2 = st.columns(2)
iniziale = c1.number_input("Fatturato mensile previsto all'inizio (€)", 0.0, 200_000.0, 2_000.0, 100.0)
crescita_nome = c2.radio("Come cresce nel tempo?", list(CRESCITE))
crescita = CRESCITE[crescita_nome]

# ============================================================ 4. Altri redditi
st.subheader("4. Hai altri redditi?")
situazione = SITUAZIONI[st.radio("Situazione", list(SITUAZIONI), horizontal=True, label_visibility="collapsed")]
reddito_altro = 0.0
if situazione != "unica":
    reddito_altro = st.number_input(
        "Reddito lordo annuo da lavoro dipendente o pensione (€)", 0.0, 500_000.0, 25_000.0, 1_000.0,
        help=f"Oltre {euro(soglia_dipendente(int(anno_inizio)))} euro nell'anno precedente il forfettario non è accessibile.",
    )

# ============================================================ 5. Liquidità
st.subheader("5. Per quanto tempo puoi lasciare i soldi fermi?")
vincolo_nome = st.selectbox("Soldi messi da parte per le tasse", list(VINCOLI), index=2, label_visibility="collapsed")
max_vincolo = VINCOLI[vincolo_nome]

# ============================================================ Opzioni avanzate
riduzione35 = False
with st.expander("Opzioni avanzate (facoltative)"):
    costi = st.slider(
        "Costi reali stimati (% del fatturato)", 0, 90, int(round(costi_impliciti(coef) * 100)),
        help=(
            "Per il confronto con l'ordinario. Di partenza usiamo i costi che il forfettario riconosce in modo forfettario "
            "(100% meno il coefficiente): modificali se sai di averne di più o di meno."
        ),
    ) / 100
    tetto = st.number_input("Fatturato mensile massimo (€, 0 = nessun limite)", 0.0, 500_000.0, 0.0, 500.0)
    g1, g2 = st.columns(2)
    gest_forf = g1.number_input(
        "Commercialista all'anno, forfettario (€)", 0.0, 20_000.0, 600.0, 50.0,
        help="Ipotesi: da fonti commerciali 2026 il forfettario costa tra 400 e 1.100 euro l'anno.",
    )
    gest_ord = g2.number_input(
        "Commercialista all'anno, ordinario (€)", 0.0, 20_000.0, 1_200.0, 50.0,
        help="Ipotesi: da fonti commerciali 2026 il semplificato costa tra 950 e 2.800 euro l'anno.",
    )
    if gestione != "separata":
        riduzione35 = st.checkbox("Ho chiesto la riduzione contributiva INPS del 35% (solo forfettario)")
    cc1, cc2 = st.columns(2)
    add_reg = cc1.number_input("Addizionale regionale (%)", 0.0, 5.0, 1.5, 0.05) / 100
    add_com = cc2.number_input("Addizionale comunale (%)", 0.0, 1.0, 0.5, 0.05) / 100
    st.caption("Offerte di conto deposito di esempio (giugno-luglio 2026): sostituiscile con quelle reali.")
    prodotti_df = st.data_editor(
        pd.DataFrame(
            {
                "Mesi di vincolo (0 = libero)": list(PRODOTTI_ESEMPIO),
                "Tasso lordo annuo (%)": [v * 100 for v in PRODOTTI_ESEMPIO.values()],
            }
        ),
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
    )
    tasso_cc = st.number_input("Tasso lordo del conto corrente (%)", 0.0, 5.0, 0.0, 0.05) / 100

prodotti = {
    int(r.iloc[0]): float(r.iloc[1]) / 100 for _, r in prodotti_df.dropna().iterrows() if r.iloc[0] >= 0
} or {0: 0.0}

# ------------------------------------------------------------ anteprima fatturato
mesi_tot = (13 - mese_inizio) + 12 * (anni - 1)
serie = serie_ricavi_mensili(iniziale, crescita, mesi_tot, tetto or None)
per_anno, pos = [], 0
for k in range(anni):
    n_mesi = (13 - mese_inizio) if k == 0 else 12
    per_anno.append(sum(serie[pos : pos + n_mesi]))
    pos += n_mesi
if iniziale <= 0:
    st.info("Inserisci un fatturato mensile maggiore di zero per vedere la risposta.")
    st.stop()
st.caption(
    "Fatturato stimato: " + " · ".join(f"{int(anno_inizio) + k}: {eur(v)}" for k, v in enumerate(per_anno))
)

req = Richiesta(
    coefficiente=coef,
    gestione=gestione,
    anno_inizio=int(anno_inizio),
    mese_inizio=mese_inizio,
    anni=anni,
    ricavo_mensile_iniziale=iniziale,
    crescita_mensile=crescita,
    tetto_mensile=tetto or None,
    nuova_attivita=nuova,
    situazione=situazione,
    reddito_altro=reddito_altro,
    costi_pct=costi,
    riduzione_inps_35=riduzione35,
    addizionale_regionale=add_reg,
    addizionale_comunale=add_com,
    max_vincolo_mesi=max_vincolo,
    prodotti=prodotti,
    tasso_conto_corrente=tasso_cc,
    costo_gestione_forfettario=gest_forf,
    costo_gestione_ordinario=gest_ord,
)
c = consiglia(req)
k_ = c.ris.kpi
nome_regime = "forfettario" if c.regime == "forfettario" else "ordinario semplificato"

# ============================================================ La risposta
st.divider()
st.header("La tua risposta")

with st.container(border=True):
    st.markdown(f"### Ti conviene il regime {nome_regime}")
    if not c.forfettario_disponibile:
        st.write("Il regime forfettario non è disponibile nel tuo caso: la stima usa l'ordinario.")
    else:
        alt = "ordinario" if c.regime == "forfettario" else "forfettario"
        if c.regime == "forfettario":
            tot_reg, tot_alt = c.carico_forfettario + c.gestione_forfettario, c.carico_ordinario + c.gestione_ordinario
        else:
            tot_reg, tot_alt = c.carico_ordinario + c.gestione_ordinario, c.carico_forfettario + c.gestione_forfettario
        st.write(
            f"In {c.anni_confronto} anni spendi circa **{eur(c.risparmio)} in meno** rispetto al regime {alt}: "
            f"{eur(tot_reg)} contro {eur(tot_alt)} fra imposte, contributi INPS e commercialista stimato."
        )
        if c.costi_pareggio is not None:
            if math.isinf(c.costi_pareggio):
                st.caption("Il forfettario conviene qualunque sia la quota di costi che sostieni.")
            elif c.regime == "forfettario":
                st.caption(
                    f"Il forfettario costa meno finché i tuoi costi reali restano sotto il {pct(c.costi_pareggio)} del "
                    f"fatturato (hai ipotizzato {pct(costi)})."
                )
            else:
                st.caption(
                    f"L'ordinario conviene perché i tuoi costi ({pct(costi)} del fatturato) superano il "
                    f"{pct(c.costi_pareggio)} oltre il quale batte il forfettario."
                )

st.caption("Il confronto non considera l'IVA, che dipende da chi sono i tuoi clienti e da quanto acquisti.")
for a in c.avvisi:
    st.warning(a)

# ---- Tre numeri
minimo, massimo = min(c.accantonamento_pct), max(c.accantonamento_pct)
quota = pct(minimo, 1) if massimo - minimo < 0.005 else f"{pct(minimo)}-{pct(massimo)}"
riga0 = c.calendario.iloc[0] if not c.calendario.empty else None
m1, m2, m3 = st.columns(3)
m1.metric("Da mettere da parte", quota, help="Percentuale di ogni incasso da accantonare per imposte e contributi.")
m1.caption(f"≈ {eur(c.accantonamento_mensile[0])} al mese nel primo anno, {eur(c.accantonamento_mensile[-1])} nell'ultimo")
if riga0 is not None:
    m2.metric("Primo versamento", riga0["quando"].capitalize())
    m2.caption(f"{eur(riga0['importo'])}: {riga0['voci'].lower()}")
m3.metric("Interessi netti stimati", eur(k_["interessi_netti"]))
m3.caption(f"su conto deposito in {anni} anni, dopo imposta 26% e bollo")

saldi = c.calendario[c.calendario["voci"].str.contains("Saldo")] if not c.calendario.empty else c.calendario
if not saldi.empty:
    s0 = saldi.iloc[0]
    if "acconto" in s0["voci"]:
        st.info(
            f"**Il primo anno non paghi imposte, ma a {s0['quando']} arrivano {eur(s0['importo'])}**: il saldo del primo "
            "anno e il primo acconto del secondo insieme. Se spendi tutto quello che incassi, quel giorno i soldi non ci sono."
        )

for sugg in c.suggerimenti:
    st.success(sugg)

# ---- Cosa fare con i soldi
st.subheader("Cosa fare con i soldi mentre aspetti la scadenza")
st.markdown(
    f"- **Ogni volta che incassi, sposta subito il {quota} su un conto separato**: quei soldi non sono tuoi, sono dell'erario e dell'INPS.\n"
    "- Quello che serve a breve tienilo su un conto deposito **libero**; quello che resterà fermo più a lungo puoi "
    "**vincolarlo** fino alla data della scadenza che lo userà.\n"
    f"- Gli interessi netti ({eur(k_['interessi_netti'])}) compensano solo lo {pct(k_['beneficio_su_carico_totale'], 1)} del carico fiscale: "
    "a pesare davvero sono la scelta del regime e le agevolazioni, non il conto deposito."
)
if not c.destinazioni.empty:
    d = c.destinazioni.copy()
    d["Dove"] = d["dove"].map(
        lambda x: "Conto deposito libero (sempre svincolabile)"
        if x == "libero"
        else x.replace("vincolato", "Deposito vincolato")
    )
    d = d.rename(columns={"importo": "Soldi (€)", "mesi_medi": "Tempo medio fermi (mesi)", "interessi_netti": "Interessi netti (€)"})
    st.dataframe(
        d[["Dove", "Soldi (€)", "Tempo medio fermi (mesi)", "Interessi netti (€)"]].style.format(
            {"Soldi (€)": n0, "Tempo medio fermi (mesi)": n1, "Interessi netti (€)": n0}
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption(
        "Ogni euro accantonato è abbinato alla scadenza che lo userà ed è collocato sul prodotto con il tasso più alto "
        "il cui vincolo scade prima di quella data."
    )

# ---- Calendario
st.subheader("Quando paghi")
if c.calendario.empty:
    st.write("Nessun versamento nell'orizzonte simulato.")
else:
    cal = c.calendario[["quando", "importo", "voci"]].rename(
        columns={"quando": "Quando", "importo": "Quanto (€)", "voci": "Cosa"}
    )
    cal["Quando"] = cal["Quando"].str.capitalize()
    st.dataframe(cal.style.format({"Quanto (€)": n0}), hide_index=True, width="stretch")
    st.caption(
        "Date mensili indicative (30 giugno e 30 novembre per saldo e acconti; maggio, agosto, novembre e febbraio per le "
        "rate fisse INPS di artigiani e commercianti): il calendario reale può slittare per weekend o proroghe."
    )

# ---- Anno per anno
with st.expander("Vedi i numeri anno per anno"):
    righe = []
    for i, e in enumerate(c.ris.esiti):
        riga = {
            "Anno": int(anno_inizio) + i,
            "Fatturato": e.ricavi,
            "Imposte": e.imposta,
            "Contributi INPS": e.inps_totale,
            "Totale": e.carico_totale,
            "% sul fatturato": e.pressione * 100,
        }
        if c.ris_alternativa is not None:
            riga["Totale altro regime"] = c.ris_alternativa.esiti[i].carico_totale
        righe.append(riga)
    tab = pd.DataFrame(righe)
    formati = {col: n0 for col in ("Fatturato", "Imposte", "Contributi INPS", "Totale", "Totale altro regime") if col in tab}
    formati["% sul fatturato"] = n1
    st.dataframe(tab.style.format(formati), hide_index=True, width="stretch")

st.divider()
st.page_link("pages/Modalita_avanzata.py", label="Apri la modalità avanzata (tutte le impostazioni)")
st.caption(
    "Simulazione a scopo informativo su parametri 2026 applicati a tutti gli anni; non è consulenza fiscale: verifica i "
    "risultati con un commercialista. Non modella IRAP, casse professionali private né tutte le cause di esclusione dal "
    "forfettario. Codice e fonti: github.com/lucaserafini4l-bit/tax-cash-optimizer"
)
