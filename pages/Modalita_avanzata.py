"""Modalità avanzata: tutte le impostazioni fiscali e di scenario in una sola schermata."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pandas as pd
import streamlit as st

from taxcash import PARAMETRI_2026 as P
from taxcash import Profilo, Scenario, calcola_anno, confronta_regimi, simula
from taxcash.deposito import rendimento_netto_annuo, tasso_pareggio
from taxcash.params import COEFFICIENTI_FORFETTARIO
from taxcash.simulazione import PRODOTTI_ESEMPIO

st.set_page_config(page_title="Modalità avanzata - Tasse partita IVA", page_icon="🧾", layout="wide")


def euro(x: float) -> str:
    return f"{x:,.0f} €".replace(",", ".")


def pct(x: float, dec: int = 1) -> str:
    return f"{x * 100:.{dec}f}%".replace(".", ",")


st.page_link("app.py", label="← Torna alla modalità semplice")
st.title("Modalità avanzata")
st.caption(
    "Calcolo di imposte e contributi per regime fiscale, scadenzario dei versamenti e rendimento "
    "della liquidità accantonata su conto deposito. Parametri 2026. Strumento di simulazione: "
    "non sostituisce un commercialista."
)

# ------------------------------------------------------------------ Sidebar
with st.sidebar:
    st.header("1. Profilo fiscale")
    regime = st.radio("Regime", ["forfettario", "ordinario"], format_func=str.capitalize, horizontal=True)
    gestione = st.selectbox(
        "Gestione INPS",
        ["separata", "commercianti", "artigiani"],
        format_func=lambda g: {"separata": "Gestione Separata (professionisti)",
                               "commercianti": "Commercianti", "artigiani": "Artigiani"}[g],
    )
    altra_copertura = st.checkbox("Già assicurato altrove / pensionato (aliquota GS 24%)",
                                  disabled=gestione != "separata")

    coefficiente, startup, riduzione35 = 0.78, True, False
    costi_pct, altri_redditi, add_reg, add_com, isa = 0.0, 0.0, 0.015, 0.005, False
    if regime == "forfettario":
        gruppo = st.selectbox(
            "Attività (coefficiente di redditività)", list(COEFFICIENTI_FORFETTARIO),
            index=len(COEFFICIENTI_FORFETTARIO) - 2,
        )
        coefficiente = st.number_input(
            "Coefficiente di redditività (%)", 0.0, 100.0, COEFFICIENTI_FORFETTARIO[gruppo] * 100, 1.0
        ) / 100
        startup = st.checkbox("Nuova attività: aliquota 5% per i primi 5 anni", value=True)
        riduzione35 = st.checkbox("Riduzione contributiva INPS 35% (su domanda)",
                                  disabled=gestione == "separata")
    else:
        costi_pct = st.slider("Costi deducibili (% dei ricavi)", 0, 90, 20) / 100
        altri_redditi = st.number_input("Altri redditi imponibili IRPEF (euro/anno)", 0.0, 500_000.0, 0.0, 1_000.0)
        add_reg = st.number_input("Addizionale regionale (%)", 0.0, 5.0, 1.5, 0.05) / 100
        add_com = st.number_input("Addizionale comunale (%)", 0.0, 1.0, 0.5, 0.05) / 100
        isa = st.checkbox("Soggetto a ISA (acconti 50% + 50%)")

    st.header("2. Scenario")
    anno_inizio = st.number_input("Anno di inizio attività", 2026, 2040, 2027, 1)
    mese_inizio = st.slider("Mese di inizio", 1, 12, 1)
    anni = st.slider("Anni da simulare", 2, 8, 4)
    ricavi = st.number_input("Fatturato annuo a regime (euro)", 1_000.0, 500_000.0, 30_000.0, 1_000.0)
    crescita = st.slider("Crescita annua del fatturato (%)", -30, 50, 0) / 100
    modo_acc = st.radio("Accantonamento mensile", ["Automatico (aliquota effettiva)", "Percentuale fissa"])
    acc_pct = None
    if modo_acc == "Percentuale fissa":
        acc_pct = st.slider("% dell'incasso accantonata", 0, 60, 25) / 100

    st.header("3. Conto deposito")
    st.caption("Offerte di esempio (giugno-luglio 2026): sostituirle con quelle reali.")
    prodotti_df = st.data_editor(
        pd.DataFrame(
            {"Mesi di vincolo (0 = libero)": list(PRODOTTI_ESEMPIO),
             "Tasso lordo annuo (%)": [v * 100 for v in PRODOTTI_ESEMPIO.values()]}
        ),
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
    )
    tasso_cc = st.number_input("Tasso lordo conto corrente (%)", 0.0, 5.0, 0.0, 0.05) / 100

prodotti = {
    int(r.iloc[0]): float(r.iloc[1]) / 100
    for _, r in prodotti_df.dropna().iterrows()
    if r.iloc[0] >= 0
}
if not prodotti:
    prodotti = {0: 0.0}

profilo = Profilo(
    regime=regime, gestione=gestione, coefficiente=coefficiente, costi_pct=costi_pct,
    startup=startup, riduzione_inps_35=riduzione35, altra_copertura=altra_copertura,
    altri_redditi=altri_redditi, addizionale_regionale=add_reg, addizionale_comunale=add_com, isa=isa,
)
scenario = Scenario(
    anno_inizio=int(anno_inizio), mese_inizio=mese_inizio, anni=anni, ricavi_annui_regime=ricavi,
    crescita_annua=crescita, accantonamento_pct=acc_pct, prodotti=prodotti, tasso_conto_corrente=tasso_cc,
)
ris = simula(profilo, scenario)
k = ris.kpi

for avviso in ris.avvisi:
    st.warning(avviso)

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Riepilogo", "Scadenzario", "Liquidità e conto deposito", "Confronto regimi", "Note e limiti"]
)

# ------------------------------------------------------------------ Riepilogo
with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Imposte + contributi (orizzonte)", euro(k["carico_totale"]))
    c2.metric("Pressione effettiva", pct(k["pressione_effettiva"]))
    c3.metric("Interessi netti sul conto deposito", euro(k["interessi_netti"]))
    c4.metric("Interessi netti / carico totale", pct(k["beneficio_su_carico_totale"], 2))

    versato_primo = sum(pg.importo for pg in ris.pagamenti if pg.anno == scenario.anno_inizio)
    versato_secondo = sum(pg.importo for pg in ris.pagamenti if pg.anno == scenario.anno_inizio + 1)
    st.info(
        f"**Primo anno:** versi {euro(versato_primo)} contro un carico di competenza di "
        f"{euro(ris.esiti[0].carico_totale)}. Nel **secondo anno** versi {euro(versato_secondo)}: "
        "saldo del primo anno, acconti del secondo e quota restante dei contributi. "
        "La differenza resta in cassa e può essere tenuta su un conto deposito."
    )

    righe = []
    for e in ris.esiti:
        righe.append({
            "Anno attività": e.anno_attivita,
            "Ricavi": e.ricavi,
            "Reddito": e.reddito,
            "Aliquota sost.": e.aliquota_forfettaria if regime == "forfettario" else None,
            "Imposta": e.imposta,
            "INPS fissi": e.inps_fissi,
            "INPS variabili": e.inps_variabili,
            "Carico totale": e.carico_totale,
            "Pressione": e.pressione,
            "Netto dopo carico": e.netto_dopo_carico,
        })
    df = pd.DataFrame(righe)
    st.dataframe(
        df.style.format({
            "Ricavi": "{:,.0f}", "Reddito": "{:,.0f}", "Imposta": "{:,.0f}", "INPS fissi": "{:,.0f}",
            "INPS variabili": "{:,.0f}", "Carico totale": "{:,.0f}", "Netto dopo carico": "{:,.0f}",
            "Aliquota sost.": "{:.0%}", "Pressione": "{:.1%}",
        }, na_rep="-"),
        hide_index=True, width="stretch",
    )

# ------------------------------------------------------------------ Scadenzario
with tab2:
    pag = pd.DataFrame(
        [{"Periodo": pg.periodo, "Voce": pg.voce, "Categoria": pg.categoria, "Importo": pg.importo}
         for pg in ris.pagamenti]
    )
    if pag.empty:
        st.write("Nessun versamento nell'orizzonte simulato.")
    else:
        mensile = pag.pivot_table(index="Periodo", columns="Categoria", values="Importo", aggfunc="sum").fillna(0)
        st.bar_chart(mensile)
        st.dataframe(pag.style.format({"Importo": "{:,.2f}"}), hide_index=True, width="stretch")
    st.caption(
        "Le date indicate sono mensili (30 giugno e 30 novembre per saldo e acconti; maggio, agosto, novembre e "
        "febbraio per le rate fisse INPS). Il calendario reale può slittare per weekend o proroghe."
    )

# ------------------------------------------------------------------ Liquidità
with tab3:
    st.subheader("Riserva accantonata")
    tl = ris.timeline.set_index("periodo")
    st.line_chart(tl[["riserva"]])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Riserva massima", euro(k["riserva_massima"]))
    c2.metric("Riserva media", euro(k["riserva_media"]))
    c3.metric("Interessi netti (dopo 26% e bollo)", euro(k["interessi_netti"]))
    c4.metric("Vantaggio vs conto corrente", euro(k["beneficio_vs_conto_corrente"]))

    st.markdown(
        f"- Interessi lordi: **{euro(k['interessi_lordi'])}**, imposta sostitutiva 26%: **{euro(k['imposta_sugli_interessi'])}**, "
        f"bollo 0,20%: **{euro(k['bollo_deposito'])}**.\n"
        f"- Rendimento netto medio annuo sulla riserva: **{pct(k['rendimento_netto_medio_annuo'], 2)}**.\n"
        f"- Tasso lordo di pareggio (sotto il quale il deposito non conviene): **{pct(tasso_pareggio(tasso_cc), 2)}**.\n"
        f"- Esempio: un deposito al 4% lordo rende **{pct(rendimento_netto_annuo(0.04), 2)}** netto annuo."
    )
    st.caption(
        "Gli interessi non riducono l'imposta dovuta: la compensano in parte. Ogni versamento accantonato viene "
        "abbinato alla scadenza che lo userà (criterio FIFO) e collocato sul prodotto con il tasso più alto "
        "il cui vincolo non supera il tempo disponibile."
    )
    with st.expander("Dettaglio degli abbinamenti"):
        if not ris.allocazioni.empty:
            st.dataframe(
                ris.allocazioni.style.format({
                    "importo": "{:,.2f}", "tasso_lordo": "{:.2%}", "interessi_lordi": "{:,.2f}",
                    "imposta_26": "{:,.2f}", "bollo": "{:,.2f}", "interessi_netti": "{:,.2f}",
                    "beneficio_vs_conto_corrente": "{:,.2f}",
                }),
                hide_index=True, width="stretch",
            )
    with st.expander("Timeline mensile"):
        st.dataframe(ris.timeline.style.format({c: "{:,.0f}" for c in ris.timeline.columns[1:]}),
                     hide_index=True, width="stretch")

# ------------------------------------------------------------------ Confronto regimi
with tab4:
    st.subheader("Forfettario o ordinario? Stesso fatturato, anno 1 a 12 mesi")
    costi_confronto = st.slider("Costi reali per il regime ordinario (% dei ricavi)", 0, 90,
                                int(costi_pct * 100) if regime == "ordinario" else 20) / 100
    base = replace(profilo, costi_pct=costi_confronto)
    livelli = list(range(10_000, 100_001, 10_000))
    tabella = []
    for r_ in livelli:
        esiti = confronta_regimi(r_, base, costi_pct_ordinario=costi_confronto)
        tabella.append({
            "Ricavi": r_,
            "Forfettario: carico": esiti["forfettario"].carico_totale,
            "Ordinario: carico": esiti["ordinario"].carico_totale,
            "Forfettario: netto": esiti["forfettario"].netto_dopo_carico,
            "Ordinario: netto": esiti["ordinario"].netto_dopo_carico,
        })
    conf = pd.DataFrame(tabella)
    st.line_chart(conf.set_index("Ricavi")[["Forfettario: carico", "Ordinario: carico"]])
    st.dataframe(conf.style.format("{:,.0f}"), hide_index=True, width="stretch")
    st.caption(
        "Il forfettario richiede ricavi sotto 85.000 euro (uscita immediata sopra 100.000) e l'assenza di cause "
        "di esclusione. Sopra tali soglie la colonna forfettario è solo indicativa."
    )

# ------------------------------------------------------------------ Note
with tab5:
    st.markdown(
        """
**Cosa modella**
- Imposta sostitutiva (5% o 15%) con coefficiente di redditività, oppure IRPEF 2026 (23/33/43%) con detrazione da lavoro autonomo e addizionali.
- Contributi INPS: Gestione Separata, Artigiani, Commercianti (minimale, rate fisse, quota variabile, riduzione 35% per forfettari).
- Saldo e acconti con metodo storico; nel primo anno nessun acconto.
- Rendimento dei soldi accantonati su conto deposito, al netto del 26% sugli interessi e del bollo 0,20%.

**Semplificazioni**
- Parametri 2026 applicati a tutti gli anni; contributi dedotti per competenza e non per cassa.
- Nessun massimale INPS, nessuna aliquota aggiuntiva oltre la prima fascia, nessuna IRAP.
- Addizionali regionale e comunale inserite come valori medi: personalizzarle.
- Interesse semplice sul periodo di permanenza; vincolo dimensionato sulla scadenza del versamento.
- Bollo del conto corrente (34,20 euro) uguale nei due scenari, quindi escluso dal confronto.

Dettagli e fonti in `docs/PARAMETRI.md` e `docs/METODO.md`.
        """
    )
