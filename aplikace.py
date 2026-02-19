import streamlit as st
import pandas as pd
import math
import io

# --- NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Stavinvest Konfigurátor", page_icon="✂️", layout="wide")
st.title("✂️ Stavinvest Konfigurátor a Spotřeba Svitků")

# --- VÝCHOZÍ PARAMETRY ---
CENA_OHYB = 10
MAX_DELKA_STROJE = 4000
PRESAH = 40

# --- PAMĚŤ PRO DATA (Editor ceníku) ---
if 'materialy_df' not in st.session_state:
    st.session_state.materialy_df = pd.DataFrame([
        {"Materiál": "FeZn svitek 0,55 mm", "Šířka svitku (mm)": 1250, "Cena za m2 (Kč)": 200},
        {"Materiál": "FeZn svitek lak PES 0,5 mm std", "Šířka svitku (mm)": 2000, "Cena za m2 (Kč)": 270},
        {"Materiál": "Comax FALC 0,7mm PES", "Šířka svitku (mm)": 1250, "Cena za m2 (Kč)": 550}
    ])

if 'prvky_df' not in st.session_state:
    st.session_state.prvky_df = pd.DataFrame([
        {"Typ prvku": "závětrná lišta spodní r.š.250", "RŠ (mm)": 250, "Ohyby": 6},
        {"Typ prvku": "okapnice do r.š. 200", "RŠ (mm)": 200, "Ohyby": 2},
        {"Typ prvku": "parapet do r.š. 330", "RŠ (mm)": 330, "Ohyby": 3}
    ])

if 'zakazka' not in st.session_state:
    st.session_state.zakazka = []

# Převod tabulek na slovníky pro výpočty
materialy = {row["Materiál"]: {"šířka": row["Šířka svitku (mm)"], "cena_m2": row["Cena za m2 (Kč)"]} for _, row in st.session_state.materialy_df.iterrows()}
prvky = {row["Typ prvku"]: {"rš": row["RŠ (mm)"], "ohyby": row["Ohyby"]} for _, row in st.session_state.prvky_df.iterrows()}

# --- ROZDĚLENÍ NA ZÁLOŽKY ---
tab_kalkulacka, tab_data = st.tabs(["🧮 Hlavní Kalkulátor", "⚙️ Správa Dat a Ceníku"])

# ==========================================
# ZÁLOŽKA 1: KALKULÁTOR
# ==========================================
with tab_kalkulacka:
    st.sidebar.header("1. Přidat prvek")
    vybrany_prvek = st.sidebar.selectbox("Typ prvku", list(prvky.keys()))
    vybrany_material = st.sidebar.selectbox("Materiál", list(materialy.keys()))
    delka_m = st.sidebar.number_input("Celková délka (m)", min_value=0.1, value=2.5, step=0.1)
    pocet_ks = st.sidebar.number_input("Počet kusů (ks)", min_value=1, value=1, step=1)

    if st.sidebar.button("➕ Přidat do zakázky", type="primary"):
        st.session_state.zakazka.append({
            "Prvek": vybrany_prvek, "Materiál": vybrany_material,
            "Délka (m)": delka_m, "Kusů": pocet_ks,
            "RŠ (mm)": prvky[vybrany_prvek]["rš"], "Ohybů": prvky[vybrany_prvek]["ohyby"]
        })
        st.sidebar.success("Přidáno!")

    if st.sidebar.button("🗑️ Vymazat zakázku"):
        st.session_state.zakazka = []
        st.rerun()

    st.subheader("📋 Položky v zakázce")
    if len(st.session_state.zakazka) > 0:
        df_zakazka = pd.DataFrame(st.session_state.zakazka)
        st.dataframe(df_zakazka, use_container_width=True)
        
        if st.button("🚀 Optimalizovat Svitky", type="primary"):
            st.subheader("✅ Výsledek optimalizace")
            
            fyzicke_kusy = []
            cena_prace_celkem = 0
            for polozka in st.session_state.zakazka:
                delka_mm = polozka["Délka (m)"] * 1000
                segmentu = 1 if delka_mm <= MAX_DELKA_STROJE else math.ceil((delka_mm - PRESAH) / (MAX_DELKA_STROJE - PRESAH))
                delka_seg = (delka_mm + (segmentu - 1) * PRESAH) / segmentu
                
                cena_prace_celkem += (polozka["Ohybů"] * CENA_OHYB) * segmentu * polozka["Kusů"]
                for _ in range(polozka["Kusů"] * segmentu):
                    fyzicke_kusy.append({
                        "materiál": polozka["Materiál"], "délka": delka_seg,
                        "rš": polozka["RŠ (mm)"], "sire_svitku": materialy[polozka["Materiál"]]["šířka"],
                        "cena_m2": materialy[polozka["Materiál"]]["cena_m2"]
                    })
            
            fyzicke_kusy = sorted(fyzicke_kusy, key=lambda x: x['délka'], reverse=True)
            odvinute_pasy = []
            for kus in fyzicke_kusy:
                umisteno = False
                for pas in odvinute_pasy:
                    if pas['materiál'] == kus['materiál'] and kus['délka'] <= pas['délka'] and kus['rš'] <= pas['zbyva_sirka']:
                        pas['zbyva_sirka'] -= kus['rš']
                        umisteno = True
                        break
                if not umisteno:
                    odvinute_pasy.append({"materiál": kus["materiál"], "délka": kus["délka"], "zbyva_sirka": kus["sire_svitku"] - kus["rš"], "sire_svitku": kus["sire_svitku"], "cena_m2": kus["cena_m2"]})

            vysledky_mat = {}
            cena_mat_celkem = 0
            for pas in odvinute_pasy:
                dm = pas["délka"] / 1000
                cp = dm * (pas["sire_svitku"] / 1000) * pas["cena_m2"]
                cena_mat_celkem += cp
                if pas["materiál"] not in vysledky_mat:
                    vysledky_mat[pas["materiál"]] = {"Pásy (ks)": 0, "Délka (m)": 0.0, "Cena (Kč)": 0.0}
                vysledky_mat[pas["materiál"]]["Pásy (ks)"] += 1
                vysledky_mat[pas["materiál"]]["Délka (m)"] += dm
                vysledky_mat[pas["materiál"]]["Cena (Kč)"] += cp
            
            df_vysledky = pd.DataFrame.from_dict(vysledky_mat, orient='index')
            st.dataframe(df_vysledky.style.format({"Délka (m)": "{:.2f}", "Cena (Kč)": "{:.2f} Kč"}), use_container_width=True)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Materiál", f"{cena_mat_celkem:,.2f} Kč")
            c2.metric("Práce", f"{cena_prace_celkem:,.2f} Kč")
            c3.metric("CELKEM", f"{(cena_mat_celkem + cena_prace_celkem):,.2f} Kč")

            # --- EXPORT A TISK ---
            st.markdown("---")
            st.subheader("💾 Export a Tisk")
            ce1, ce2 = st.columns(2)
            with ce1:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_zakazka.to_excel(writer, sheet_name='Položky', index=False)
                    df_vysledky.to_excel(writer, sheet_name='Souhrn')
                st.download_button(label="📥 Stáhnout Excel", data=output.getvalue(), file_name="kalkulace.xlsx")
            with ce2:
                st.markdown('<button onclick="window.print()" style="padding: 10px; border-radius: 5px; cursor: pointer;">🖨️ Tisk / PDF</button>', unsafe_allow_html=True)
    else:
        st.info("👈 Přidejte první prvek.")

# ==========================================
# ZÁLOŽKA 2: SPRÁVA DAT
# ==========================================
with tab_data:
    st.subheader("⚙️ Nastavení ceníku a parametrů")
    c_d1, c_d2 = st.columns(2)
    with c_d1:
        st.write("Svitky a ceny:")
        st.session_state.materialy_df = st.data_editor(st.session_state.materialy_df, num_rows="dynamic", use_container_width=True)
    with c_d2:
        st.write("Klempířské prvky:")
        st.session_state.prvky_df = st.data_editor(st.session_state.prvky_df, num_rows="dynamic", use_container_width=True)
