import streamlit as st
import pandas as pd
import math
import io
import copy
import random
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from openpyxl.drawing.image import Image as xlImage
from openpyxl.utils import get_column_letter

# --- NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Konfigurátor Stavinvest BETA", page_icon="🧪", layout="wide")
st.title("🧪 Konfigurátor Stavinvest - TESTOVACÍ VERZE")
st.info("V této verzi zadáváte rozvinutou šíři (RŠ) ručně v milimetrech.")

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
        for it in test_items:
            groups[it['dy']].append(it)
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
                    m['strips'].append(s); m['used_w'] += s['w']
                    m['l'] = max(m['l'], s['l']); placed = True; break
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
                    it['draw_w'] = it['dx']; it['draw_h'] = it['dy']
                    placed.append(it)
            formatted_bins.append({'w_coil': coil_w, 'odvinuto_mm': m['l'], 'placed': placed})
    return formatted_bins

# --- DATA ---
if 'config' not in st.session_state:
    st.session_state.config = {"cena_ohyb": 10.0, "max_delka": 4000, "presah": 40, "povolit_rotaci": True}

if 'materialy_df' not in st.session_state:
    st.session_state.materialy_df = pd.DataFrame([
        {"Materiál": "svitek POZINK 0,55x1000mm", "Interní kód SI": "0160P003", "Šířka (mm)": 1000, "Cena/m2": 200.0, "Max délka": 50000},
        {"Materiál": "svitek POZINK 0,55x670mm", "Interní kód SI": "0160P002", "Šířka (mm)": 670, "Cena/m2": 218.0, "Max délka": 50000},
        {"Materiál": "svitek POZINK 0,5x1250mm PES", "Interní kód SI": "0160LP0107", "Šířka (mm)": 1250, "Cena/m2": 282.0, "Max délka": 50000},
        {"Materiál": "tabule AL 0,6x1000x2000 PES", "Interní kód SI": "0150AL06", "Šířka (mm)": 1000, "Cena/m2": 421.0, "Max délka": 2000}
    ])

if 'prvky_df' not in st.session_state:
    st.session_state.prvky_df = pd.DataFrame([
        {"Typ prvku": "Závětrná lišta spodní", "Ohyby": 6},
        {"Typ prvku": "Závětrná lišta pultová", "Ohyby": 6},
        {"Typ prvku": "Okapnice", "Ohyby": 2},
        {"Typ prvku": "Úžlabí", "Ohyby": 3},
        {"Typ prvku": "Atypický výrobek", "Ohyby": 9}
    ])

if 'zakazka' not in st.session_state: st.session_state.zakazka = []
mat_dict = {r["Materiál"]: r for _, r in st.session_state.materialy_df.iterrows()}
prv_dict = {r["Typ prvku"]: r for _, r in st.session_state.prvky_df.iterrows()}

tab_kalk, tab_nakres, tab_data = st.tabs(["🧮 Kalkulátor", "📐 Nákres", "⚙️ Ceník"])

with tab_data:
    st.header("⚙️ Správa dat")
    st.session_state.materialy_df = st.data_editor(st.session_state.materialy_df, num_rows="dynamic", use_container_width=True)
    st.session_state.prvky_df = st.data_editor(st.session_state.prvky_df, num_rows="dynamic", use_container_width=True)

with tab_kalk:
    col_in, col_res = st.columns([1, 2])
    with col_in:
        st.header("Zadání")
        v_mat = st.selectbox("Materiál", list(mat_dict.keys()))
        v_prvek = st.selectbox("Typ výrobku", list(prv_dict.keys()))
        v_rs = st.number_input("Rozvinutá šíře - RŠ (mm)", value=250, step=1)
        v_m = st.number_input("Délka (m)", value=2.0, step=0.1)
        v_ks = st.number_input("Kusů", min_value=1, value=1)
        
        if st.button("➕ Přidat položku", use_container_width=True):
            st.session_state.zakazka.append({
                "Prvek": v_prvek, "RŠ (mm)": v_rs, "Ohyby": prv_dict[v_prvek]["Ohyby"], 
                "Metrů": v_m, "Kusů": v_ks
            })
        if st.button("🗑️ Smazat vše"): st.session_state.zakazka = []; st.rerun()

    with col_res:
        if st.session_state.zakazka:
            df_zak = pd.DataFrame(st.session_state.zakazka)
            st.data_editor(df_zak, use_container_width=True)
            
            if st.button("🚀 SPOČÍTAT", type="primary", use_container_width=True):
                items = []
                m_data = mat_dict[v_mat]
                for idx, p in enumerate(st.session_state.zakazka):
                    for _ in range(int(p["Kusů"])):
                        items.append({"id": idx+1, "Prvek": p['Prvek'], "L": p['Metrů']*1000, "rš": p['RŠ (mm)']})
                
                bins = pack_module_strips(items, m_data["Šířka (mm)"], st.session_state.config["max_delka"])
                st.session_state.vysledky = bins
                st.success("Vypočítáno!")

with tab_nakres:
    if 'vysledky' in st.session_state:
        for i, b in enumerate(st.session_state.vysledky):
            fig, ax = plt.subplots(figsize=(10, 3))
            ax.add_patch(patches.Rectangle((0, 0), b['odvinuto_mm'], b['w_coil'], fill=False, edgecolor='black', lw=2))
            for p in b['placed']:
                ax.add_patch(patches.Rectangle((p['x'], p['y']), p['draw_w'], p['draw_h'], facecolor='skyblue', edgecolor='black'))
                ax.text(p['x']+p['draw_w']/2, p['y']+p['draw_h']/2, f"Ř.{p['id']}\n{p['rš']}mm", ha='center', va='center', fontsize=8)
            ax.set_xlim(0, st.session_state.config["max_delka"] * 1.05)
            ax.set_title(f"Modul {i+1} (Odvin: {b['odvinuto_mm']} mm)")
            st.pyplot(fig)
