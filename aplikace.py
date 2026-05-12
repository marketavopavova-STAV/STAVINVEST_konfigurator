import streamlit as st
import pandas as pd
import math
import io
import copy
import random
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Konfigurátor Stavinvest", page_icon="✂️", layout="wide")
st.title("✂️ Konfigurátor Stavinvest")

# --- INICIALIZACE ---
if 'config' not in st.session_state:
    st.session_state.config = {"cena_ohyb": 10.0, "max_delka": 4000, "presah": 50}
if 'zakazka' not in st.session_state:
    st.session_state.zakazka = []
if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

# ==========================================
# MODULOVÝ PRUHOVÝ ALGORITMUS
# ==========================================
def pack_module_strips(items, coil_w, max_l, allow_rotation=True):
    best_modules = None
    best_len = float('inf')
    for iteration in range(100):
        test_items = copy.deepcopy(items)
        random.shuffle(test_items)
        for it in test_items:
            it['dx'], it['dy'], it['rotated'] = it['L'], it['rš'], False
        groups = defaultdict(list)
        for it in test_items: groups[it['dy']].append(it)
        strips = []
        for dy, group_items in groups.items():
            current_strips = []
            for it in group_items:
                placed = False
                for s in current_strips:
                    if s['l'] + it['dx'] <= max_l:
                        it['x'] = s['l']; s['items'].append(it); s['l'] += it['dx']
                        placed = True; break
                if not placed:
                    it['x'] = 0; current_strips.append({'w': dy, 'l': it['dx'], 'items': [it]})
            strips.extend(current_strips)
        strips.sort(key=lambda s: s['l'], reverse=True)
        modules = []
        for s in strips:
            placed = False
            for m in modules:
                if m['used_w'] + s['w'] <= coil_w:
                    s['y'] = m['used_w']
                    for it in s['items']: it['y'] = s['y']
                    m['strips'].append(s); m['used_w'] += s['w']; m['l'] = max(m['l'], s['l'])
                    placed = True; break
            if not placed:
                s['y'] = 0
                for it in s['items']: it['y'] = 0
                modules.append({'used_w': s['w'], 'l': s['l'], 'strips': [s]})
        tot_len = sum(m['l'] for m in modules)
        if tot_len < best_len:
            best_len = tot_len; best_modules = modules
    formatted_bins = []
    if best_modules:
        for m in best_modules:
            placed = []
            for s in m['strips']:
                for it in s['items']:
                    it['draw_w'] = it['dx']; it['draw_h'] = it['dy']; placed.append(it)
            formatted_bins.append({'w_coil': coil_w, 'odvinuto_mm': m['l'], 'placed': placed})
    return formatted_bins

# --- DATA: MATERIÁLY (15 položek) ---
if 'materialy_df' not in st.session_state:
    st.session_state.materialy_df = pd.DataFrame([
        {"Materiál": "svitek POZINK 0,55x1000mm", "Interní kód SI": "0160P003", "Šířka (mm)": 1000, "Cena/m2": 200.0, "Max délka": 50000},
        {"Materiál": "svitek POZINK 0,55x670mm", "Interní kód SI": "0160P002", "Šířka (mm)": 670, "Cena/m2": 218.0, "Max délka": 50000},
        {"Materiál": "svitek POZINK 0,5x1250mm PES STANDARD BARVY O+SF", "Interní kód SI": "0160LP0107016O+SF", "Šířka (mm)": 1250, "Cena/m2": 282.0, "Max délka": 50000},
        {"Materiál": "svitek POZINK 0,5x1250mm PES NESTANDARD O+SF", "Interní kód SI": "0160LP0109010O+SF", "Šířka (mm)": 1250, "Cena/m2": 301.0, "Max délka": 50000},
        {"Materiál": "Comax FALC POZINK 0,5x620mm PES šedá J+SF", "Interní kód SI": "0160LP0017016J+SF", "Šířka (mm)": 620, "Cena/m2": 456.0, "Max délka": 50000},
        {"Materiál": "svitek TITANZINEK 0,6x1000mm", "Interní kód SI": "0160T003", "Šířka (mm)": 1000, "Cena/m2": 611.0, "Max délka": 50000},
        {"Materiál": "svitek TITANZINEK 0,6x670mm", "Interní kód SI": "0160T002", "Šířka (mm)": 670, "Cena/m2": 611.0, "Max délka": 50000},
        {"Materiál": "svitek MĚĎ 0,55x1000mm", "Interní kód SI": "0160M011000", "Šířka (mm)": 1000, "Cena/m2": 2120.0, "Max délka": 50000},
        {"Materiál": "svitek MĚĎ 0,55x670mm", "Interní kód SI": "0160M010670", "Šířka (mm)": 670, "Cena/m2": 2120.0, "Max délka": 50000},
        {"Materiál": "PREFA svitek CLR 0,7x1000 PE", "Interní kód SI": "65P31105", "Šířka (mm)": 1000, "Cena/m2": 457.0, "Max délka": 30000},
        {"Materiál": "PREFA svitek Prefalz 0,7x1000 hladký", "Interní kód SI": "65P40100", "Šířka (mm)": 1000, "Cena/m2": 578.0, "Max délka": 30000},
        {"Materiál": "PREFA svitek Prefalz 0,7x650 hladký", "Interní kód SI": "65P40200", "Šířka (mm)": 650, "Cena/m2": 578.0, "Max délka": 50000},
        {"Materiál": "Comax FALC AL 0,7x600mm", "Interní kód SI": "0160ALCO0706007016", "Šířka (mm)": 600, "Cena/m2": 622.0, "Max délka": 50000},
        {"Materiál": "tabule AL 0,6x1000x2000 PES jednostranná s folií", "Interní kód SI": "0150AL06100020007016J+SF", "Šířka (mm)": 1000, "Cena/m2": 421.0, "Max délka": 2000},
        {"Materiál": "tabule PVC 0,6x1000x2000 ROOFPLAN 7035", "Interní kód SI": "0150PVC0037035", "Šířka (mm)": 1000, "Cena/m2": 591.0, "Max délka": 2000}
    ])

# --- DATA: PRVKY (12 položek) ---
if 'prvky_df' not in st.session_state:
    st.session_state.prvky_df = pd.DataFrame([
        {"Typ prvku": "Závětrná lišta spodní", "Ohyby": 6},
        {"Typ prvku": "Závětrná lišta pultová", "Ohyby": 6},
        {"Typ prvku": "Okapnice", "Ohyby": 2},
        {"Typ prvku": "Lemování ke zdi", "Ohyby": 3},
        {"Typ prvku": "Úžlabí", "Ohyby": 3},
        {"Typ prvku": "Úžlabí s drážkou", "Ohyby": 5},
        {"Typ prvku": "Atikový plech", "Ohyby": 4},
        {"Typ prvku": "L lišta", "Ohyby": 2},
        {"Typ prvku": "Stěnová lišta", "Ohyby": 2},
        {"Typ prvku": "Parapet", "Ohyby": 3},
        {"Typ prvku": "Parapet včetně boků", "Ohyby": 3},
        {"Typ prvku": "Atypický výrobek", "Ohyby": 9}
    ])

mat_dict = {r["Materiál"]: r for _, r in st.session_state.materialy_df.iterrows()}
prv_dict = {r["Typ prvku"]: r for _, r in st.session_state.prvky_df.iterrows()}

tab_kalk, tab_nakres, tab_data = st.tabs(["🧮 Kalkulátor", "📐 Nákres", "⚙️ Ceník"])

with tab_data:
    st.session_state.materialy_df = st.data_editor(st.session_state.materialy_df, num_rows="dynamic", key="em")
    st.session_state.prvky_df = st.data_editor(st.session_state.prvky_df, num_rows="dynamic", key="ep")

with tab_kalk:
    st.subheader("1. Obecné údaje")
    ci1, ci2, ci3 = st.columns(3)
    with ci1:
        st.session_state.odberatel = st.text_input("Odběratel / Projekt", value=st.session_state.get('odberatel', ''))
    with ci2:
        st.session_state.config["max_delka"] = st.number_input("Max. délka ohýbačky (mm)", value=int(st.session_state.config.get("max_delka", 4000)))
    with ci3:
        st.session_state.config["presah"] = st.number_input("Přesah spojů (mm)", value=int(st.session_state.config.get("presah", 50)))
    
    st.markdown("---")

    col_in, col_res = st.columns([1, 2])
    with col_in:
        v_mat = st.selectbox("Materiál pro zakázku", list(mat_dict.keys()))
        st.subheader("2. Přidat položku")
        v_prvek = st.selectbox("Typ prvku", list(prv_dict.keys()))
        default_ohyby = int(prv_dict[v_prvek]["Ohyby"])
        
        with st.form("pridat_polozku_form", clear_on_submit=True):
            f_rs = st.number_input("Rozvinutá šíře - RŠ (mm)", min_value=10, value=250, step=1, key=f"rs_{st.session_state.reset_counter}")
            f_ohyby = st.number_input("Počet ohybů", value=default_ohyby, min_value=0, key=f"ohyby_{v_prvek}_{st.session_state.reset_counter}")
            f_m = st.number_input("Délka (m)", value=2.5, step=0.1, key=f"m_{st.session_state.reset_counter}")
            f_ks = st.number_input("Kusů", min_value=1, value=1, key=f"ks_{st.session_state.reset_counter}")
            f_prip = st.number_input("Atyp. příplatek/ks (Kč - celá čísla)", min_value=0, value=0, step=1, key=f"prip_{st.session_state.reset_counter}")
            
            submitted = st.form_submit_button("➕ Přidat do zakázky", use_container_width=True)
            if submitted:
                st.session_state.zakazka.append({
                    "Prvek": v_prvek, "RŠ (mm)": f_rs, "Ohyby": f_ohyby,
                    "Metrů": f_m, "Kusů": f_ks, "Atyp příplatek/ks (Kč)": float(f_prip)
                })
                st.session_state.reset_counter += 1
                st.rerun()
            
        if st.button("🗑️ Smazat celou zakázku", use_container_width=True):
            st.session_state.zakazka = []; st.session_state.calc_done = False; st.rerun()

    with col_res:
        st.subheader("Výpočet a Optimalizace")
        if st.session_state.zakazka:
            df_zak = pd.DataFrame(st.session_state.zakazka)
            df_zak.insert(0, 'Řádek', range(1, len(df_zak) + 1))
            edited_df = st.data_editor(df_zak, hide_index=True, use_container_width=True, key="editor_zak")
            st.session_state.zakazka = edited_df.drop(columns=['Řádek']).to_dict('records')
            
            if st.button("🚀 SPOČÍTAT ZAKÁZKU", type="primary", use_container_width=True):
                m_data = mat_dict[v_mat]; conf = st.session_state.config
                items = []; c_prace = 0; c_prip = 0
                for idx, p in enumerate(st.session_state.zakazka):
                    c_prace += (p["Ohyby"] * conf["cena_ohyb"]) * p["Metrů"] * p["Kusů"]
                    c_prip += p.get("Atyp příplatek/ks (Kč)", 0.0) * p["Kusů"]
                    for _ in range(int(p["Kusů"])): 
                        items.append({"id": idx+1, "Prvek": p['Prvek'], "L": (p['Metrů']*1000) + conf["presah"], "rš": p['RŠ (mm)']})
                
                bins = pack_module_strips(items, m_data["Šířka (mm)"], conf["max_delka"])
                t_odvin = sum(b['odvinuto_mm'] for b in bins) / 1000
                c_mat = (t_odvin * (m_data["Šířka (mm)"]/1000)) * m_data["Cena/m2"]
                st.session_state.res = {"c_mat": c_mat, "c_prace": c_prace, "c_prip": c_prip, "bins": bins, "w_coil": m_data["Šířka (mm)"]}
                st.session_state.calc_done = True; st.rerun()

            if st.session_state.get('calc_done'):
                r = st.session_state.res
                bez_dph = r["c_mat"] + r["c_prace"] + r["c_prip"]
                st.divider()
                st.subheader("🧾 Souhrnná kalkulace")
                
                souhrn_final = pd.DataFrame([
                    {"Položka": "Materiál (bez DPH)", "Částka": r['c_mat']},
                    {"Položka": "Práce / Ohyby (bez DPH)", "Částka": r['c_prace']},
                    {"Položka": "Atypické příplatky (bez DPH)", "Částka": r['c_prip']},
                    {"Položka": "CELKEM BEZ DPH", "Částka": bez_dph},
                    {"Položka": "CELKEM S DPH 21 %", "Částka": bez_dph * 1.21}
                ])
                
                def highlight_totals(s):
                    return ['background-color: #f0f2f6; font-weight: bold;' if s.name in [3, 4] else '' for _ in s]

                styled_df = souhrn_final.style.apply(highlight_totals, axis=1).format({"Částka": "{:,.2f} Kč"})
                st.dataframe(styled_df, column_config={"Položka": st.column_config.TextColumn("Položka", width="medium"), "Částka": st.column_config.NumberColumn("Částka", format="%.2f Kč")}, hide_index=True, use_container_width=True)

with tab_nakres:
    if st.session_state.get('calc_done') and 'res' in st.session_state:
        barvy = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#e67e22', '#1abc9c']
        for i, b in enumerate(st.session_state.res['bins']):
            fig, ax = plt.subplots(figsize=(10, 3))
            ax.add_patch(patches.Rectangle((0, 0), b['odvinuto_mm'], b['w_coil'], fill=False, edgecolor='black', lw=2))
            for p in b['placed']:
                barva = barvy[(p['id'] - 1) % len(barvy)]
                ax.add_patch(patches.Rectangle((p['x'], p['y']), p['draw_w'], p['draw_h'], facecolor=barva, edgecolor='black', alpha=0.7))
                ax.text(p['x'] + p['draw_w']/2, p['y'] + p['draw_h']/2, f"Ř.{p['id']}\n{p['rš']}mm", ha='center', va='center', fontsize=8, color='black', weight='bold')
            ax.set_xlim(0, b['odvinuto_mm'] * 1.05); ax.set_ylim(0, b['w_coil'] * 1.1)
            st.write(f"**Modul {i+1}:** Odvinout {b['odvinuto_mm']/1000:.2f} m")
            st.pyplot(fig)
