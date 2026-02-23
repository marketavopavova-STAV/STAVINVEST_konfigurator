import streamlit as st
import pandas as pd
import math
import io
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Stavinvest Konfigurátor", page_icon="✂️", layout="wide")
st.title("✂️ Stavinvest Konfigurátor vč. 2D Nákresu")

# ==========================================
# 2D GUILLOTINE BIN PACKING ALGORITMUS
# ==========================================
class FreeRect:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

def pack_guillotine(items, coil_w):
    # Seřazení od nejdelších a nejširších
    items.sort(key=lambda x: (x['L'], x['rš']), reverse=True)
    free_rects = [FreeRect(0, 0, 9999999, coil_w)] # Nekonečný svitek
    placed = []
    
    for item in items:
        best_idx = -1
        best_fr = None
        
        # Nalezení nejlepšího volného místa
        for i, fr in enumerate(free_rects):
            if fr.w >= item['L'] and fr.h >= item['rš']:
                if best_fr is None or fr.h < best_fr.h:
                    best_fr = fr
                    best_idx = i
        
        if best_fr is None:
            continue
            
        item['x'] = best_fr.x
        item['y'] = best_fr.y
        placed.append(item)
        
        # Gilotinový řez - rozdělení zbytku prostoru
        w_left = best_fr.w - item['L']
        h_left = best_fr.h - item['rš']
        
        fr_top = FreeRect(best_fr.x, best_fr.y + item['rš'], item['L'], h_left)
        fr_right = FreeRect(best_fr.x + item['L'], best_fr.y, w_left, best_fr.h)
        
        free_rects.pop(best_idx)
        if fr_top.w > 0 and fr_top.h > 0: free_rects.append(fr_top)
        if fr_right.w > 0 and fr_right.h > 0: free_rects.append(fr_right)
        
        # Třídění volných míst zleva doprava
        free_rects.sort(key=lambda f: (f.x, f.y))
        
    return placed

# --- INICIALIZACE NASTAVENÍ ---
if 'config' not in st.session_state:
    st.session_state.config = {"cena_ohyb": 10.0, "max_delka": 4000, "presah": 40}

if 'materialy_df' not in st.session_state:
    st.session_state.materialy_df = pd.DataFrame([
        {"Materiál": "FeZn svitek 0,55 mm", "Šířka (mm)": 1250, "Cena/m2": 200, "Max délka tabule (mm)": 10000},
        {"Materiál": "FeZn svitek lak PES 0,5 mm", "Šířka (mm)": 1250, "Cena/m2": 270, "Max délka tabule (mm)": 10000},
        {"Materiál": "Comax FALC 0,7mm PES", "Šířka (mm)": 1250, "Cena/m2": 550, "Max délka tabule (mm)": 10000},
        {"Materiál": "Titanzinek 0,6 mm", "Šířka (mm)": 1000, "Cena/m2": 650, "Max délka tabule (mm)": 2000}
    ])

if 'prvky_df' not in st.session_state:
    st.session_state.prvky_df = pd.DataFrame([
        {"Typ prvku": "závětrná lišta spodní r.š.250", "RŠ (mm)": 250, "Ohyby": 6},
        {"Typ prvku": "okapnice pod fólii r.š.200", "RŠ (mm)": 200, "Ohyby": 2},
        {"Typ prvku": "parapet r.š.330", "RŠ (mm)": 330, "Ohyby": 3},
        {"Typ prvku": "úžlabí r.š.500", "RŠ (mm)": 500, "Ohyby": 4}
    ])

if 'zakazka' not in st.session_state:
    st.session_state.zakazka = []

mat_dict = {r["Materiál"]: r for _, r in st.session_state.materialy_df.iterrows()}
prv_dict = {r["Typ prvku"]: r for _, r in st.session_state.prvky_df.iterrows()}

# --- ZÁLOŽKY ---
tab_kalk, tab_nakres, tab_data, tab_nastaveni = st.tabs(["🧮 Kalkulátor", "📐 Nákres 2D Řezů", "⚙️ Data (Ceník)", "🔧 Nastavení"])

# ==========================================
# ZÁLOŽKA: NASTAVENÍ
# ==========================================
with tab_nastaveni:
    st.header("🔧 Globální parametry")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.config["cena_ohyb"] = st.number_input("Cena za ohyb (Kč)", value=float(st.session_state.config["cena_ohyb"]))
        st.session_state.config["presah"] = st.number_input("Přesah spojů (mm)", value=int(st.session_state.config["presah"]))
    with c2:
        st.session_state.config["max_delka"] = st.number_input("Délka ohýbačky (mm)", value=int(st.session_state.config["max_delka"]))

# ==========================================
# ZÁLOŽKA: DATA
# ==========================================
with tab_data:
    st.header("⚙️ Správa dat")
    st.session_state.materialy_df = st.data_editor(st.session_state.materialy_df, num_rows="dynamic", key="em")
    st.session_state.prvky_df = st.data_editor(st.session_state.prvky_df, num_rows="dynamic", key="ep")

# ==========================================
# ZÁLOŽKA: KALKULÁTOR
# ==========================================
with tab_kalk:
    col_in, col_res = st.columns([1, 2])
    with col_in:
        st.header("Zadání")
        v_prvek = st.selectbox("Prvek", list(prv_dict.keys()))
        v_mat = st.selectbox("Materiál", list(mat_dict.keys()))
        v_m = st.number_input("Délka (m)", value=2.5, step=0.1)
        v_ks = st.number_input("Kusů", min_value=1, value=1)
        
        if st.button("➕ Přidat do zakázky", type="primary", use_container_width=True):
            st.session_state.zakazka.append({"Prvek": v_prvek, "Materiál": v_mat, "Metrů": v_m, "Kusů": v_ks})
            st.rerun()
        if st.button("🗑️ Smazat vše", use_container_width=True):
            st.session_state.zakazka = []
            st.session_state.vysledky_packing = {}
            st.rerun()

    with col_res:
        st.header("Výpočet a Optimalizace")
        if st.session_state.zakazka:
            st.table(pd.DataFrame(st.session_state.zakazka))
            
            if st.button("🚀 SPOČÍTAT 2D", type="primary", use_container_width=True):
                st.divider()
                fyzicke_kusy = {}
                cena_prace = 0
                conf = st.session_state.config
                
                # Příprava dílů pro jednotlivé materiály
                for p in st.session_state.zakazka:
                    m_data = mat_dict[p["Materiál"]]
                    p_data = prv_dict[p["Prvek"]]
                    L_mm = p["Metrů"] * 1000
                    
                    if p_data["RŠ (mm)"] > m_data["Šířka (mm)"]:
                        st.error(f"CHYBA: Prvek '{p['Prvek']}' je širší než svitek {p['Materiál']}!")
                        continue
                        
                    seg = 1 if L_mm <= conf["max_delka"] else math.ceil((L_mm - conf["presah"]) / (conf["max_delka"] - conf["presah"]))
                    L_seg = (L_mm + (seg - 1) * conf["presah"]) / seg
                    
                    if L_seg > m_data["Max délka tabule (mm)"]:
                        st.error(f"CHYBA: Segment ({L_seg:.0f}mm) je delší než dostupná tabule materiálu {p['Materiál']}!")
                        continue

                    cena_prace += (p_data["Ohyby"] * conf["cena_ohyb"]) * seg * p["Kusů"]
                    
                    if p["Materiál"] not in fyzicke_kusy:
                        fyzicke_kusy[p["Materiál"]] = []
                        
                    for _ in range(int(p["Kusů"] * seg)):
                        fyzicke_kusy[p["Materiál"]].append({
                            "Prvek": p['Prvek'], "L": L_seg, "rš": p_data["RŠ (mm)"]
                        })

                # Vlastní skládání pro každý materiál
                vysledky_packing = {}
                c_mat = 0
                sumar = {}
                
                for mat_name, items in fyzicke_kusy.items():
                    w_coil = mat_dict[mat_name]["Šířka (mm)"]
                    cena_m2 = mat_dict[mat_name]["Cena/m2"]
                    
                    placed = pack_guillotine(items, w_coil)
                    
                    if placed:
                        max_x = max([p['x'] + p['L'] for p in placed])
                        odvinuto_m = max_x / 1000
                        cena_za_svitek = odvinuto_m * (w_coil / 1000) * cena_m2
                        
                        vysledky_packing[mat_name] = {
                            "w_coil": w_coil, "max_x": max_x, "placed": placed
                        }
                        
                        c_mat += cena_za_svitek
                        sumar[mat_name] = {"Odvinout (m)": odvinuto_m, "Cena": cena_za_svitek}
                
                st.session_state.vysledky_packing = vysledky_packing
                
                st.subheader("Souhrnná tabulka")
                st.dataframe(pd.DataFrame.from_dict(sumar, orient='index').style.format({"Odvinout (m)": "{:.2f}", "Cena": "{:.2f} Kč"}))
                
                r1, r2, r3 = st.columns(3)
                r1.metric("Materiál", f"{c_mat:,.2f} Kč")
                r2.metric("Práce", f"{cena_prace:,.2f} Kč")
                r3.metric("CELKEM (vč. DPH)", f"{(c_mat + cena_prace)*1.21:,.2f} Kč")

# ==========================================
# ZÁLOŽKA: NÁKRES
# ==========================================
with tab_nakres:
    st.header("📐 Schéma řezů na svitku")
    st.write("Díky 2D Gilotinovému algoritmu aplikace minimalizuje prořez a zajistí, že všechny řezy půjdou provést na tabulových nůžkách.")
    
    if 'vysledky_packing' in st.session_state and st.session_state.vysledky_packing:
        barvy = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#e67e22', '#1abc9c']
        
        for mat_name, data in st.session_state.vysledky_packing.items():
            st.subheader(f"Materiál: {mat_name}")
            st.write(f"Celkem odvinout ze svitku: **{data['max_x'] / 1000:.2f} m**")
            
            fig, ax = plt.subplots(figsize=(12, 3))
            
            # Kreslení obrysu svitku
            ax.add_patch(patches.Rectangle((0, 0), data['max_x'], data['w_coil'], fill=False, edgecolor='black', linewidth=2))
            
            # Přiřazení barev
            unikatni_prvky = list(set([p['Prvek'] for p in data['placed']]))
            color_map = {prvek: barvy[i % len(barvy)] for i, prvek in enumerate(unikatni_prvky)}
            
            # Kreslení prvků
            for p in data['placed']:
                ax.add_patch(patches.Rectangle((p['x'], p['y']), p['L'], p['rš'], facecolor=color_map[p['Prvek']], edgecolor='black', alpha=0.8))
                
                # Text uvnitř obdélníku
                font_size = 8 if p['L'] > 500 else 6
                ax.text(p['x'] + p['L']/2, p['y'] + p['rš']/2, f"{p['Prvek']}\n({p['L']:.0f}x{p['rš']})", 
                        ha='center', va='center', fontsize=font_size, color='white', weight='bold')
            
            ax.set_xlim(0, data['max_x'] * 1.02)
            ax.set_ylim(0, data['w_coil'] * 1.05)
            ax.set_xlabel("Délka odvinutého svitku (mm)")
            ax.set_ylabel("Šířka svitku (mm)")
            st.pyplot(fig)
            st.divider()
    else:
        st.info("Nejdříve proveďte výpočet v záložce Kalkulátor.")
