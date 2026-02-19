import streamlit as st
import pandas as pd
import math
import io

# --- NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Stavinvest Konfigurátor", page_icon="✂️", layout="wide")
st.title("✂️ Stavinvest Konfigurátor a Spotřeba Svitků")

# --- KONSTANTY ---
CENA_OHYB = 10  # Cena za jeden ohyb v Kč
MAX_DELKA_STROJE = 4000  # Maximální délka ohýbačky v mm
PRESAH = 40  # Přesah při spojování plechů v mm

# --- PAMĚŤ PRO DATA (VÝCHOZÍ CENÍK) ---
# Tady si můžete v kódu přepsat názvy a hodnoty, aby tam byly po spuštění hned správně
if 'materialy_df' not in st.session_state:
    st.session_state.materialy_df = pd.DataFrame([
        {"Materiál": "FeZn svitek 0,55 mm", "Šířka svitku (mm)": 1250, "Cena za m2 (Kč)": 200},
        {"Materiál": "FeZn svitek lak PES 0,5 mm", "Šířka svitku (mm)": 1250, "Cena za m2 (Kč)": 270},
        {"Materiál": "Comax FALC 0,7mm PES", "Šířka svitku (mm)": 1250, "Cena za m2 (Kč)": 550},
        {"Materiál": "Al přírodní 0,6 mm", "Šířka svitku (mm)": 1000, "Cena za m2 (Kč)": 320},
        {"Materiál": "Měď 0,55 mm", "Šířka svitku (mm)": 670, "Cena za m2 (Kč)": 1200},
        {"Materiál": "Titanzinek 0,6 mm", "Šířka svitku (mm)": 1000, "Cena za m2 (Kč)": 650}
    ])

if 'prvky_df' not in st.session_state:
    st.session_state.prvky_df = pd.DataFrame([
        {"Typ prvku": "Závětrná lišta spodní", "RŠ (mm)": 250, "Ohyby": 6},
        {"Typ prvku": "Okapnice pod fólii", "RŠ (mm)": 200, "Ohyby": 2},
        {"Typ prvku": "Okapnice okapová", "RŠ (mm)": 250, "Ohyby": 3},
        {"Typ prvku": "Parapet", "RŠ (mm)": 330, "Ohyby": 3},
        {"Typ prvku": "Lemování ke zdi", "RŠ (mm)": 312, "Ohyby": 3},
        {"Typ prvku": "Úžlabí", "RŠ (mm)": 500, "Ohyby": 4},
        {"Typ prvku": "Hřebenáč", "RŠ (mm)": 412, "Ohyby": 4},
        {"Typ prvku": "Závětrná lišta horní", "RŠ (mm)": 312, "Ohyby": 5}
    ])

if 'zakazka' not in st.session_state:
    st.session_state.zakazka = []

# Převod tabulek pro potřeby výpočetního algoritmu
materialy_dict = {row["Materiál"]: {"šířka": row["Šířka svitku (mm)"], "cena_m2": row["Cena za m2 (Kč)"]} 
                  for _, row in st.session_state.materialy_df.iterrows() if row["Materiál"]}

prvky_dict = {row["Typ prvku"]: {"rš": row["RŠ (mm)"], "ohyby": row["Ohyby"]} 
              for _, row in st.session_state.prvky_df.iterrows() if row["Typ prvku"]}

# --- ROZDĚLENÍ APLIKACE NA ZÁLOŽKY ---
tab_kalk, tab_data = st.tabs(["🧮 Kalkulátor zakázky", "⚙️ Správa ceníku a parametrů"])

# ==========================================
# ZÁLOŽKA 1: KALKULÁTOR
# ==========================================
with tab_kalk:
    col_input, col_table = st.columns([1, 3])
    
    with col_input:
        st.header("1. Zadání")
        if not prvky_dict or not materialy_dict:
            st.error("Chybí data v ceníku! Běžte do záložky Správa dat.")
        else:
            v_prvek = st.selectbox("Prvek", list(prvky_dict.keys()))
            v_mat = st.selectbox("Materiál", list(materialy_dict.keys()))
            v_delka = st.number_input("Celková délka (m)", min_value=0.1, value=2.0, step=0.1)
            v_ks = st.number_input("Počet kusů (ks)", min_value=1, value=1, step=1)
            
            if st.button("➕ Přidat do seznamu", type="primary", use_container_width=True):
                st.session_state.zakazka.append({
                    "Prvek": v_prvek,
                    "Materiál": v_mat,
                    "Délka (m)": v_delka,
                    "Kusů": v_ks,
                    "RŠ (mm)": prvky_dict[v_prvek]["rš"],
                    "Ohybů": prvky_dict[v_prvek]["ohyby"]
                })
                st.rerun()

        if st.button("🗑️ Vymazat vše", use_container_width=True):
            st.session_state.zakazka = []
            st.rerun()

    with col_table:
        st.header("2. Položky zakázky")
        if st.session_state.zakazka:
            df_z = pd.DataFrame(st.session_state.zakazka)
            st.table(df_z)
            
            if st.button("🚀 SPOČÍTAT OPTIMALIZACI A CENU", type="primary"):
                st.divider()
                st.header("✅ Výsledek")
                
                fyzicke_kusy = []
                cena_prace = 0
                
                for p in st.session_state.zakazka:
                    delka_mm = p["Délka (m)"] * 1000
                    # Výpočet počtu segmentů (střihů)
                    seg = 1 if delka_mm <= MAX_DELKA_STROJE else math.ceil((delka_mm - PRESAH) / (MAX_DELKA_STROJE - PRESAH))
                    delka_jednoho_seg = (delka_mm + (seg - 1) * PRESAH) / seg
                    
                    cena_prace += (p["Ohybů"] * CENA_OHYB) * seg * p["Kusů"]
                    
                    for _ in range(p["Kusů"] * seg):
                        fyzicke_kusy.append({
                            "mat": p["Materiál"], "L": delka_jednoho_seg, "rš": p["RŠ (mm)"],
                            "svitek_w": materialy_dict[p["Materiál"]]["šířka"],
                            "cena_m2": materialy_dict[p["Materiál"]]["cena_m2"]
                        })
                
                # Skládání na svitky (Tetris)
                fyzicke_kusy = sorted(fyzicke_kusy, key=lambda x: x['L'], reverse=True)
                pasy = []
                for k in fyzicke_kusy:
                    fit = False
                    for pas in pasy:
                        if pas['mat'] == k['mat'] and k['L'] <= pas['L'] and k['rš'] <= pas['zbyva']:
                            pas['zbyva'] -= k['rš']
                            fit = True
                            break
                    if not fit:
                        pasy.append({"mat": k["mat"], "L": k["L"], "zbyva": k["svitek_w"] - k["rš"], "full_w": k["svitek_w"], "cena_m2": k["cena_m2"]})
                
                # Sumarizace
                sumar = {}
                cena_mat_celkem = 0
                for pas in pasy:
                    m = pas["mat"]
                    m2 = (pas["L"]/1000) * (pas["full_w"]/1000)
                    cena = m2 * pas["cena_m2"]
                    cena_mat_celkem += cena
                    if m not in sumar: sumar[m] = {"Pásy (ks)": 0, "Metrů": 0.0, "Cena": 0.0}
                    sumar[m]["Pásy (ks)"] += 1
                    sumar[m]["Metrů"] += pas["L"]/1000
                    sumar[m]["Cena"] += cena
                
                df_res = pd.DataFrame.from_dict(sumar, orient='index')
                st.dataframe(df_res.style.format({"Metrů": "{:.2f}", "Cena": "{:.2f} Kč"}), use_container_width=True)
                
                res1, res2, res3 = st.columns(3)
                res1.metric("Materiál", f"{cena_mat_celkem:,.2f} Kč")
                res2.metric("Práce (ohyby)", f"{cena_prace:,.2f} Kč")
                res3.metric("CELKEM S DPH", f"{(cena_mat_celkem + cena_prace)*1.21:,.2f} Kč", delta="vč. 21% DPH")

                # --- EXPORTY ---
                st.divider()
                st.subheader("💾 Export a tisk")
                e1, e2 = st.columns(2)
                with e1:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine='openpyxl') as wr:
                        df_z.to_excel(wr, sheet_name='Zadání', index=False)
                        df_res.to_excel(wr, sheet_name='Souhrn_Svitků')
                    st.download_button("📥 Stáhnout Excel", buf.getvalue(), "kalkulace_stavinvest.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                with e2:
                    st.markdown('<button onclick="window.print()" style="width:100%; height:40px; border-radius:5px; cursor:pointer;">🖨️ Tisk / Uložit do PDF</button>', unsafe_allow_html=True)
        else:
            st.info("Seznam je prázdný. Přidejte prvky v levém panelu.")

# ==========================================
# ZÁLOŽKA 2: SPRÁVA DAT
# ==========================================
with tab_data:
    st.header("⚙️ Konfigurace ceníku")
    st.write("Změny se projeví ihned v kalkulátoru. Můžete přepisovat buňky nebo přidávat řádky na konci tabulky.")
    
    d_col1, d_col2 = st.columns(2)
    with d_col1:
        st.subheader("Svitky (Materiály)")
        st.session_state.materialy_df = st.data_editor(st.session_state.materialy_df, num_rows="dynamic", use_container_width=True, key="ed_mat")
    with d_col2:
        st.subheader("Typy prvků (RŠ a ohyby)")
        st.session_state.prvky_df = st.data_editor(st.session_state.prvky_df, num_rows="dynamic", use_container_width=True, key="ed_prv")
    
    st.divider()
    st.info("Tip: Pokud chcete přidat novou položku, klikněte do prázdného řádku s ikonou '+' úplně dole v tabulce.")
