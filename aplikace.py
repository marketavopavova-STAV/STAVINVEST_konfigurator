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
# 2D GUILLOTINE BIN PACKING (Více svitků/tabulí)
# ==========================================
class FreeRect:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

def pack_guillotine_multibin(items, coil_w, max_l):
    # Seřazení kusů
    items.sort(key=lambda x: (x['L'], x['rš']), reverse=True)
    bins = []
    
    for item in items:
        placed = False
        # Pokus o umístění do už existujících rozdělaných svitků
        for b in bins:
            best_idx = -1
            best_fr = None
            for i, fr in enumerate(b['free_rects']):
                if fr.w >= item['L'] and fr.h >= item['rš']:
                    if best_fr is None or fr.h < best_fr.h:
                        best_fr = fr
                        best_idx = i
            
            if best_fr is not None:
                item['x'] = best_fr.x
                item['y'] = best_fr.y
                b['placed'].append(item)
                
                w_left = best_fr.w - item['L']
                h_left = best_fr.h - item['rš']
                fr_top = FreeRect(best_fr.x, best_fr.y + item['rš'], item['L'], h_left)
                fr_right = FreeRect(best_fr.x + item['L'], best_fr.y, w_left, best_fr.h)
                
                b['free_rects'].pop(best_idx)
                if fr_top.w > 0 and fr_top.h > 0: b['free_rects'].append(fr_top)
                if fr_right.w > 0 and fr_right.h > 0: b['free_rects'].append(fr_right)
                
                b['free_rects'].sort(key=lambda f: (f.x, f.y))
                placed = True
                break
                
        # Pokud se kus už nevejde, založíme nový svitek (Bin)
        if not placed:
            actual_max_l = max(max_l, item['L']) # Pro jistotu, kdyby někdo zadal prvek delší než max limit
            new_bin = {'free_rects': [FreeRect(0, 0, actual_max_l, coil_w)], 'placed': [], 'w_coil': coil_w}
            item['x'] = 0
            item['y'] = 0
            new_bin['placed'].append(item)
            
            w_left = actual_max_l - item['L']
            h_left = coil_w - item['rš']
            fr_top = FreeRect(0, item['rš'], item['L'], h_left)
            fr_right = FreeRect(item['L'], 0, w_left, coil_w)
            
            if fr_top.w > 0 and fr_top.h > 0: new_bin['free_rects'].append(fr_top)
            if fr_right.w > 0 and fr_right.h > 0: new_bin['free_rects'].append(fr_right)
            
            new_bin['free_rects'].sort(key=lambda f: (f.x, f.y))
            bins.append(new_bin)
            
    return bins

# --- INICIALIZACE NASTAVENÍ ---
if 'config' not in st.session_state:
    st.session_state.config = {"cena_ohyb": 10.0, "max_delka": 4000, "presah": 40}

# --- NAČTENÍ KOMPLETNÍCH DAT Z EXCELU ---
if 'materialy_df' not in st.session_state:
    st.session_state.materialy_df = pd.DataFrame([
        {"Materiál": "FeZn svitek 0,55 mm", "Šířka (mm)": 1250, "Cena/m2": 200.0, "Max délka tabule (mm)": 10000},
        {"Materiál": "FeZn svitek lak PES 0,5 mm std barvy", "Šířka (mm)": 2000, "Cena/m2": 270.0, "Max délka tabule (mm)": 10000},
        {"Materiál": "FeZn svitek lak PES 0,5 mm nestandard", "Šířka (mm)": 1000, "Cena/m2": 288.0, "Max délka tabule (mm)": 10000},
        {"Materiál": "Titanzinek 0,6 mm", "Šířka (mm)": 1500, "Cena/m2": 611.0, "Max délka tabule (mm)": 10000},
        {"Materiál": "Titanzinek 0,7 mm", "Šířka (mm)": 1250, "Cena/m2": 714.0, "Max délka tabule (mm)": 10000},
        {"Materiál": "Cu svitek 0,55 mm", "Šířka (mm)": 2000, "Cena/m2": 2119.0, "Max délka tabule (mm)": 10000},
        {"Materiál": "Hliník 0,6 mm J+SF PES (MTC)", "Šířka (mm)": 1000, "Cena/m2": 400.0, "Max délka tabule (mm)": 10000},
        {"Materiál": "Hliník 0,7 mm O+SF PES (MTC)", "Šířka (mm)": 1500, "Cena/m2": 530.0, "Max délka tabule (mm)": 10000},
        {"Materiál": "Comax FALC 0,7mm PES", "Šířka (mm)": 1750, "Cena/m2": 550.0, "Max délka tabule (mm)": 10000},
        {"Materiál": "Comax FALC 0,7mm Cortex", "Šířka (mm)": 2500, "Cena/m2": 590.0, "Max délka tabule (mm)": 10000},
        {"Materiál": "Prefa CLR", "Šířka (mm)": 1300, "Cena/m2": 457.0, "Max délka tabule (mm)": 10000},
        {"Materiál": "PREFA Prefalz", "Šířka (mm)": 1700, "Cena/m2": 580.0, "Max délka tabule (mm)": 10000},
        {"Materiál": "PVC ROOFPLAN 7035", "Šířka (mm)": 1800, "Cena/m2": 591.0, "Max délka tabule (mm)": 10000},
        {"Materiál": "Bauder PVC svitek 7035", "Šířka (mm)": 2600, "Cena/m2": 840.0, "Max délka tabule (mm)": 10000},
        {"Materiál": "ATYP", "Šířka (mm)": 1250, "Cena/m2": 0.0, "Max délka tabule (mm)": 10000},
        {"Materiál": "Výroba z materiálu zákazníka", "Šířka (mm)": 1250, "Cena/m2": 0.0, "Max délka tabule (mm)": 10000}
    ])

if 'prvky_df' not in st.session_state:
    st.session_state.prvky_df = pd.DataFrame([
        {"Typ prvku": "závětrná lišta spodní r.š.250", "RŠ (mm)": 250, "Ohyby": 6},
        {"Typ prvku": "závětrná lišta spodní r.š.330", "RŠ (mm)": 333, "Ohyby": 6},
        {"Typ prvku": "závětrná lišta spodní r.š.410", "RŠ (mm)": 410, "Ohyby": 6},
        {"Typ prvku": "okapnice do r.š. 200", "RŠ (mm)": 200, "Ohyby": 2},
        {"Typ prvku": "okapnice r.š.201-250", "RŠ (mm)": 250, "Ohyby": 2},
        {"Typ prvku": "okapnice r.š. 250 - 333", "RŠ (mm)": 333, "Ohyby": 2},
        {"Typ prvku": "lemování ke zdi r.š.250", "RŠ (mm)": 250, "Ohyby": 3},
        {"Typ prvku": "lemování ke zdi r.š.330", "RŠ (mm)": 333, "Ohyby": 6},
        {"Typ prvku": "úžlabí r.š.500", "RŠ (mm)": 500, "Ohyby": 3},
        {"Typ prvku": "úžlabí rš 670", "RŠ (mm)": 670, "Ohyby": 3},
        {"Typ prvku": "úžlabí s drážkou rš. 500", "RŠ (mm)": 500, "Ohyby": 5},
        {"Typ prvku": "úžlabí s drážkou rš. 670", "RŠ (mm)": 670, "Ohyby": 5},
        {"Typ prvku": "závětrná lišta pultová r.š.250", "RŠ (mm)": 250, "Ohyby": 6},
        {"Typ prvku": "závětrná lišta pultová r.š.330", "RŠ (mm)": 333, "Ohyby": 6},
        {"Typ prvku": "atikový plech do r.š. 500", "RŠ (mm)": 500, "Ohyby": 4},
        {"Typ prvku": "L lišta", "RŠ (mm)": 100, "Ohyby": 2},
        {"Typ prvku": "stěnová lišta", "RŠ (mm)": 100, "Ohyby": 2},
        {"Typ prvku": "parapet do r.š. 250", "RŠ (mm)": 250, "Ohyby": 3},
        {"Typ prvku": "parapet do r.š. 330", "RŠ (mm)": 333, "Ohyby": 3},
        {"Typ prvku": "parapet do r.š. 500", "RŠ (mm)": 500, "Ohyby": 3},
        {"Typ prvku": "parapet do r.š. 250 včetně boků", "RŠ (mm)": 250, "Ohyby": 3},
        {"Typ prvku": "parapet do r.š. 330 včetně boků", "RŠ (mm)": 333, "Ohyby": 3},
        {"Typ prvku": "parapet do r.š. 500 včetně boků", "RŠ (mm)": 500, "Ohyby": 3},
        {"Typ prvku": "atypický výrobek rš 0 - 100", "RŠ (mm)": 100, "Ohyby": 9},
        {"Typ prvku": "atypický výrobek rš 100 - 250", "RŠ (mm)": 250, "Ohyby": 9},
        {"Typ prvku": "atypický výrobek rš 251 - 333", "RŠ (mm)": 333, "Ohyby": 9},
        {"Typ prvku": "atypický výrobek rš 334 - 500", "RŠ (mm)": 500, "Ohyby": 9},
        {"Typ prvku": "atypický výrobek rš 501 - 1250", "RŠ (mm)": 1250, "Ohyby": 9}
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
    st.info("Zde můžete přidávat materiály, upravovat jejich ceny i limitní délku (Max délka tabule).")
    st.session_state.materialy_df = st.data_editor(st.session_state.materialy_df, num_rows="dynamic", key="em", use_container_width=True)
    st.session_state.prvky_df = st.data_editor(st.session_state.prvky_df, num_rows="dynamic", key="ep", use_container_width=True)

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
                        st.error(f"CHYBA: Váš prvek potřebuje segment dlouhý {L_seg:.0f} mm, ale {p['Materiál']} má max. délku {m_data['Max délka tabule (mm)']} mm!")
                        continue

                    cena_prace += (p_data["Ohyby"] * conf["cena_ohyb"]) * seg * p["Kusů"]
                    
                    if p["Materiál"] not in fyzicke_kusy:
                        fyzicke_kusy[p["Materiál"]] = []
                        
                    for _ in range(int(p["Kusů"] * seg)):
                        fyzicke_kusy[p["Materiál"]].append({
                            "Prvek": p['Prvek'], "L": L_seg, "rš": p_data["RŠ (mm)"]
                        })

                vysledky_packing = {}
                c_mat = 0
                sumar = {}
                
                for mat_name, items in fyzicke_kusy.items():
                    w_coil = mat_dict[mat_name]["Šířka (mm)"]
                    cena_m2 = mat_dict[mat_name]["Cena/m2"]
                    max_tab_len = mat_dict[mat_name]["Max délka tabule (mm)"]
                    
                    bins = pack_guillotine_multibin(items, w_coil, max_tab_len)
                    
                    if bins:
                        tot_odvinuto = 0
                        tot_cena = 0
                        vysledky_packing[mat_name] = bins
                        
                        for b in bins:
                            max_x = max([p['x'] + p['L'] for p in b['placed']])
                            b['odvinuto_mm'] = max_x
                            odvinuto_m = max_x / 1000
                            cena_za_svitek = odvinuto_m * (w_coil / 1000) * cena_m2
                            
                            tot_odvinuto += odvinuto_m
                            tot_cena += cena_za_svitek
                            
                        c_mat += tot_cena
                        sumar[mat_name] = {"Pásů/Tabulí (ks)": len(bins), "Celkem odvinout (m)": tot_odvinuto, "Cena": tot_cena}
                
                st.session_state.vysledky_packing = vysledky_packing
                st.subheader("Souhrnná tabulka materiálu")
                st.dataframe(pd.DataFrame.from_dict(sumar, orient='index').style.format({"Celkem odvinout (m)": "{:.2f}", "Cena": "{:.2f} Kč"}))
                
                r1, r2, r3 = st.columns(3)
                r1.metric("Materiál", f"{c_mat:,.2f} Kč")
                r2.metric("Práce (Ohyby)", f"{cena_prace:,.2f} Kč")
                r3.metric("CELKEM ZAKÁZKA (vč. DPH)", f"{(c_mat + cena_prace)*1.21:,.2f} Kč")

# ==========================================
# ZÁLOŽKA: NÁKRES
# ==========================================
with tab_nakres:
    st.header("📐 Schéma řezů na svitku")
    st.write("Aplikace nyní hlídá **Maximální délku tabule** a pokud je překročena, automaticky založí nový svitek.")
    
    if 'vysledky_packing' in st.session_state and st.session_state.vysledky_packing:
        barvy = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#e67e22', '#1abc9c']
        
        for mat_name, bins in st.session_state.vysledky_packing.items():
            st.subheader(f"Materiál: {mat_name}")
            
            for i, b in enumerate(bins):
                odvinuto_mm = b['odvinuto_mm']
                w_coil = b['w_coil']
                
                st.write(f"**Pás {i+1}:** Odstřihnout **{odvinuto_mm / 1000:.2f} m** (Šířka svitku: {w_coil} mm)")
                
                fig, ax = plt.subplots(figsize=(12, 2.5))
                # Kreslení obrysu pásu
                ax.add_patch(patches.Rectangle((0, 0), odvinuto_mm, w_coil, fill=False, edgecolor='black', linewidth=2))
                
                unikatni_prvky = list(set([p['Prvek'] for p in b['placed']]))
                color_map = {prvek: barvy[idx % len(barvy)] for idx, prvek in enumerate(unikatni_prvky)}
                
                for p in b['placed']:
                    ax.add_patch(patches.Rectangle((p['x'], p['y']), p['L'], p['rš'], facecolor=color_map[p['Prvek']], edgecolor='black', alpha=0.8))
                    font_size = 8 if p['L'] > 500 else 6
                    ax.text(p['x'] + p['L']/2, p['y'] + p['rš']/2, f"{p['Prvek']}\n({p['L']:.0f}x{p['rš']})", 
                            ha='center', va='center', fontsize=font_size, color='white', weight='bold')
                
                ax.set_xlim(0, max(odvinuto_mm * 1.02, 100))
                ax.set_ylim(0, w_coil * 1.05)
                ax.set_xlabel("Délka (mm)")
                ax.set_ylabel("Šířka (mm)")
                st.pyplot(fig)
            st.divider()
    else:
        st.info("Nejdříve proveďte výpočet v záložce Kalkulátor.")
