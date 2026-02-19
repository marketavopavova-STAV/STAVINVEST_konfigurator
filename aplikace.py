import streamlit as st
import pandas as pd
import math

# --- NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Klempířský Konfigurátor", page_icon="✂️", layout="wide")
st.title("✂️ Klempířský Konfigurátor a Spotřeba Svitků")

# --- DATA (Zatím natvrdo, později napojíme na váš Excel) ---
CENA_OHYB = 10
MAX_DELKA_STROJE = 4000
PRESAH = 40

materialy = {
    "FeZn svitek 0,55 mm": {"šířka": 1250, "cena_m2": 200},
    "FeZn svitek lak PES 0,5 mm std": {"šířka": 2000, "cena_m2": 270},
    "Comax FALC 0,7mm PES": {"šířka": 1250, "cena_m2": 550}
}

prvky = {
    "závětrná lišta spodní r.š.250": {"rš": 250, "ohyby": 6},
    "okapnice do r.š. 200": {"rš": 200, "ohyby": 2},
    "parapet do r.š. 330": {"rš": 330, "ohyby": 3}
}

# --- PAMĚŤ APLIKACE (Košík) ---
if 'zakazka' not in st.session_state:
    st.session_state.zakazka = []

# --- LEVÝ PANEL (Přidávání položek) ---
st.sidebar.header("1. Přidat prvek do zakázky")
vybrany_prvek = st.sidebar.selectbox("Typ prvku", list(prvky.keys()))
vybrany_material = st.sidebar.selectbox("Materiál", list(materialy.keys()))
delka_m = st.sidebar.number_input("Celková délka (m)", min_value=0.1, value=2.5, step=0.1)
pocet_ks = st.sidebar.number_input("Počet kusů (ks)", min_value=1, value=1, step=1)

if st.sidebar.button("➕ Přidat do zakázky", type="primary"):
    st.session_state.zakazka.append({
        "Prvek": vybrany_prvek,
        "Materiál": vybrany_material,
        "Délka (m)": delka_m,
        "Kusů": pocet_ks,
        "RŠ (mm)": prvky[vybrany_prvek]["rš"],
        "Ohybů": prvky[vybrany_prvek]["ohyby"]
    })
    st.sidebar.success("Přidáno!")

if st.sidebar.button("🗑️ Vymazat zakázku"):
    st.session_state.zakazka = []
    st.rerun()

# --- HLAVNÍ ČÁST (Přehled zakázky) ---
st.subheader("📋 Aktuální položky v zakázce")
if len(st.session_state.zakazka) > 0:
    df_zakazka = pd.DataFrame(st.session_state.zakazka)
    st.dataframe(df_zakazka, use_container_width=True)
    
    # --- TETRIS ALGORITMUS ---
    if st.button("🚀 Optimalizovat Svitky (Spustit Tetris)", type="primary"):
        st.subheader("✅ Výsledek optimalizace")
        
        # 1. Rozpad na fyzické kusy
        fyzicke_kusy = []
        cena_prace_celkem = 0
        
        for polozka in st.session_state.zakazka:
            # Výpočet segmentů
            delka_mm = polozka["Délka (m)"] * 1000
            if delka_mm <= MAX_DELKA_STROJE:
                segmentu = 1
            else:
                segmentu = math.ceil((delka_mm - PRESAH) / (MAX_DELKA_STROJE - PRESAH))
                
            delka_1_segmentu = (delka_mm + (segmentu - 1) * PRESAH) / segmentu
            sire_svitku = materialy[polozka["Materiál"]]["šířka"]
            cena_m2 = materialy[polozka["Materiál"]]["cena_m2"]
            
            # Cena práce
            cena_prace_celkem += (polozka["Ohybů"] * CENA_OHYB) * segmentu * polozka["Kusů"]
            
            # Přidání každého jednotlivého plechu do seznamu
            celkem_fyzickych_plechu = polozka["Kusů"] * segmentu
            for _ in range(celkem_fyzickych_plechu):
                fyzicke_kusy.append({
                    "materiál": polozka["Materiál"],
                    "délka": delka_1_segmentu,
                    "rš": polozka["RŠ (mm)"],
                    "sire_svitku": sire_svitku,
                    "cena_m2": cena_m2
                })
        
        # 2. Seřadit od nejdelšího
        fyzicke_kusy = sorted(fyzicke_kusy, key=lambda x: x['délka'], reverse=True)
        
        # 3. Skládání
        odvinute_pasy = []
        for kus in fyzicke_kusy:
            umisteno = False
            for pas in odvinute_pasy:
                if pas['materiál'] == kus['materiál'] and kus['délka'] <= pas['délka'] and kus['rš'] <= pas['zbyva_sirka']:
                    pas['zbyva_sirka'] -= kus['rš'] # Uřízneme šířku vedle
                    umisteno = True
                    break
            
            if not umisteno:
                # Nový pás svitku
                odvinute_pasy.append({
                    "materiál": kus["materiál"],
                    "délka": kus["délka"],
                    "zbyva_sirka": kus["sire_svitku"] - kus["rš"],
                    "sire_svitku": kus["sire_svitku"],
                    "cena_m2": kus["cena_m2"]
                })
                
        # 4. Zpracování výsledků
        vysledky_mat = {}
        cena_material_celkem = 0
        
        for pas in odvinute_pasy:
            mat = pas["materiál"]
            delka_m = pas["délka"] / 1000
            plocha_m2 = delka_m * (pas["sire_svitku"] / 1000)
            cena_pasu = plocha_m2 * pas["cena_m2"]
            
            cena_material_celkem += cena_pasu
            
            if mat not in vysledky_mat:
                vysledky_mat[mat] = {"Odvinuté pásy": 0, "Celkem odvinout (m)": 0.0, "Cena (Kč)": 0.0}
                
            vysledky_mat[mat]["Odvinuté pásy"] += 1
            vysledky_mat[mat]["Celkem odvinout (m)"] += delka_m
            vysledky_mat[mat]["Cena (Kč)"] += cena_pasu
            
        # Zobrazení tabulky a cen
        df_vysledky = pd.DataFrame.from_dict(vysledky_mat, orient='index')
        st.dataframe(df_vysledky.style.format({"Celkem odvinout (m)": "{:.2f}", "Cena (Kč)": "{:.2f} Kč"}), use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Cena za materiál", f"{cena_material_celkem:,.2f} Kč")
        col2.metric("Cena za práci (ohyby)", f"{cena_prace_celkem:,.2f} Kč")
        col3.metric("CELKOVÁ CENA", f"{(cena_material_celkem + cena_prace_celkem):,.2f} Kč")
        
else:
    st.info("👈 Přidejte první prvek do zakázky pomocí menu vlevo.")