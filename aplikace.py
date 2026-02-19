import streamlit as st
import pandas as pd
import math
import io

# --- NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Stavinvest Konfigurátor", page_icon="✂️", layout="wide")
st.title("✂️ Stavinvest Konfigurátor")

# --- INICIALIZACE GLOBÁLNÍCH NASTAVENÍ (Z listu Nastavení) ---
if 'config' not in st.session_state:
    st.session_state.config = {
        "cena_ohyb": 10.0,
        "max_delka": 4000,
        "presah": 40
    }

# --- INICIALIZACE DAT (Z listu Data) ---
if 'materialy_df' not in st.session_state:
    st.session_state.materialy_df = pd.DataFrame([
        {"Materiál": "FeZn svitek 0,55 mm", "Šířka (mm)": 1250, "Cena/m2": 200},
        {"Materiál": "FeZn svitek lak PES 0,5 mm", "Šířka (mm)": 1250, "Cena/m2": 270},
        {"Materiál": "Comax FALC 0,7mm PES", "Šířka (mm)": 1250, "Cena/m2": 550},
        {"Materiál": "Al přírodní 0,6 mm", "Šířka (mm)": 1000, "Cena/m2": 320},
        {"Materiál": "Měď 0,55 mm", "Šířka (mm)": 670, "Cena/m2": 1200},
        {"Materiál": "Titanzinek 0,6 mm", "Šířka (mm)": 1000, "Cena/m2": 650}
    ])

if 'prvky_df' not in st.session_state:
    # Přesné názvy dle vašeho Excelu
    st.session_state.prvky_df = pd.DataFrame([
        {"Typ prvku": "závětrná lišta spodní r.š.250", "RŠ (mm)": 250, "Ohyby": 6},
        {"Typ prvku": "závětrná lišta horní r.š.312", "RŠ (mm)": 312, "Ohyby": 5},
        {"Typ prvku": "závětrná lišta pultová r.š.330", "RŠ (mm)": 330, "Ohyby": 4},
        {"Typ prvku": "okapnice pod fólii r.š.200", "RŠ (mm)": 200, "Ohyby": 2},
        {"Typ prvku": "okapnice okapová r.š.250", "RŠ (mm)": 250, "Ohyby": 3},
        {"Typ prvku": "parapet r.š.330", "RŠ (mm)": 330, "Ohyby": 3},
        {"Typ prvku": "lemování ke zdi r.š.312", "RŠ (mm)": 312, "Ohyby": 3},
        {"Typ prvku": "úžlabí r.š.500", "RŠ (mm)": 500, "Ohyby": 4},
        {"Typ prvku": "hřebenáč r.š.412", "RŠ (mm)": 412, "Ohyby": 4}
    ])

if 'zakazka' not in st.session_state:
    st.session_state.zakazka = []

# Pomocné slovníky pro výpočty
materialy_dict = {row["Materiál"]: {"šířka": row["Šířka (mm)"], "cena_m2": row["Cena/m2"]} 
                  for _, row in st.session_state.materialy_df.iterrows()}
prvky_dict = {row["Typ prvku"]: {"rš": row["RŠ (mm)"], "ohyby": row["Ohyby"]} 
              for _, row in st.session_state.prvky_df.iterrows()}

# --- ZÁLOŽKY ---
tab_kalk, tab_data, tab_nastaveni = st.tabs(["🧮 Kalkulátor", "⚙️ Data (Ceník)", "🔧 Nastavení"])

# ==========================================
# ZÁLOŽKA: NASTAVENÍ
# ==========================================
with tab_nastaveni:
    st.header("🔧 Globální parametry výroby")
    st.write("Tyto hodnoty ovlivňují výpočet ceny práce a dělení plechů.")
    
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        st.session_state.config["cena_ohyb"] = st.number_input("Cena za 1 ohyb (Kč)", value=st.session_state.config["cena_ohyb"])
        st.session_state.config["presah"] = st.number_input("Přesah při spojování (mm)", value=st.session_state.config["presah"])
    with col_n2:
        st.session_state.config["max_delka"] = st.number_input("Maximální délka ohýbačky (mm)", value=st.session_state.config["max_delka"])

# ==========================================
# ZÁLOŽKA: DATA (CENÍK)
# ==========================================
with tab_data:
    st.header("⚙️ Správa materiálů a prvků")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.subheader("Svitky")
        st.session_state.materialy_df = st.data_editor(st.session_state.materialy_df, num_rows="dynamic", key="ed_mat")
    with col_d2:
        st.subheader("Klempířské prvky")
        st.session_state.prvky_df = st.data_editor(st.session_state.prvky_df, num_rows="dynamic", key="ed_prv")

# ==========================================
# ZÁLOŽKA: KALKULÁTOR
# ==========================================
with tab_kalk:
    col_in, col_list = st.columns([1, 2])
    
    with col_in:
        st.header("Vložit položku")
        v_prvek = st.selectbox("Vyberte prvek (vč. RŠ)", list(prvky_dict.keys()))
        v_mat = st.selectbox("Vyberte materiál", list(materialy_dict.keys()))
        v_m = st.number_input("Délka celkem (m)", min_value=0.1, value=2.0)
        v_ks = st.number_input("Počet kusů", min_value=1, value=1)
        
        if st.button("➕ Přidat", type="primary", use_container_width=True):
            st.session_state.zakazka.append({
                "Prvek": v_prvek, "Materiál": v_mat, "Metrů": v_m, "Kusů": v_ks,
                "RŠ": prvky_dict[v_prvek]["rš"], "Ohybů": prvky_dict[v_prvek]["ohyby"]
            })
            st.rerun()
        
        if st.button("🗑️ Vymazat seznam", use_container_width=True):
            st.session_state.zakazka = []
            st.rerun()

    with col_list:
        st.header("Aktuální zakázka")
        if st.session_state.zakazka:
            df_zak = pd.DataFrame(st.session_state.zakazka)
            st.table(df_zak[["Prvek", "Materiál", "Metrů", "Kusů"]])
            
            if st.button("🚀 SPOČÍTAT", type="primary"):
                st.divider()
                
                fyzicke_kusy = []
                cena_prace = 0
                config = st.session_state.config
                
                for p in st.session_state.zakazka:
                    L_mm = p["Metrů"] * 1000
                    # Výpočet segmentů dle délky stroje a přesahu
                    if L_mm <= config["max_delka"]:
                        seg = 1
                        L_seg = L_mm
                    else:
                        seg = math.ceil((L_mm - config["presah"]) / (config["max_delka"] - config["presah"]))
                        L_seg = (L_mm + (seg - 1) * config["presah"]) / seg
                    
                    cena_prace += (p["Ohybů"] * config["cena_ohyb"]) * seg * p["Kusů"]
                    
                    for _ in range(int(p["Kusů"] * seg)):
                        fyzicke_kusy.append({
                            "mat": p["Materiál"], "L": L_seg, "rš": p["RŠ"],
                            "w": materialy_dict[p["Materiál"]]["šířka"],
                            "c_m2": materialy_dict[p["Materiál"]]["cena_m2"]
                        })

                # Tetris Optimalizace
                fyzicke_kusy = sorted(fyzicke_kusy, key=lambda x: x['L'], reverse=True)
                odvinuto = []
                for k in fyzicke_kusy:
                    placed = False
                    for pas in odvinuto:
                        if pas['mat'] == k['mat'] and k['L'] <= pas['L'] and k['rš'] <= pas['zbyva']:
                            pas['zbyva'] -= k['rš']
                            placed = True
                            break
                    if not placed:
                        odvinuto.append({"mat": k["mat"], "L": k["L"], "zbyva": k["w"] - k["rš"], "sirka": k["w"], "c_m2": k["c_m2"]})
                
                # Souhrn
                stats = {}
                cena_mat = 0
                for pas in odvinuto:
                    m2 = (pas["L"]/1000) * (pas["sirka"]/1000)
                    cena = m2 * pas["c_m2"]
                    cena_mat += cena
                    if pas["mat"] not in stats: stats[pas["mat"]] = {"Pásy (ks)": 0, "Metrů": 0.0, "Kč": 0.0}
                    stats[pas["mat"]]["Pásy (ks)"] += 1
                    stats[pas["mat"]]["Metrů"] += pas["L"]/1000
                    stats[pas["mat"]]["Kč"] += cena
                
                st.subheader("Souhrn materiálu")
                st.dataframe(pd.DataFrame.from_dict(stats, orient='index').style.format({"Metrů": "{:.2f}", "Kč": "{:.2f} Kč"}))
                
                r1, r2, r3 = st.columns(3)
                r1.metric("Materiál", f"{cena_mat:,.2f} Kč")
                r2.metric("Práce", f"{cena_prace:,.2f} Kč")
                r3.metric("CELKEM (vč. DPH)", f"{(cena_mat + cena_prace)*1.21:,.2f} Kč")

                # Export
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as wr:
                    df_zak.to_excel(wr, sheet_name='Zadání', index=False)
                    pd.DataFrame.from_dict(stats, orient='index').to_excel(wr, sheet_name='Souhrn')
                st.download_button("📥 Exportovat do Excelu", buf.getvalue(), "kalkulace.xlsx")
                st.button("🖨️ Tisk (Ctrl+P)", on_click=None)
        else:
            st.info("Přidejte položky pro výpočet.")
