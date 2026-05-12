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

# --- DATA ---
if 'materialy_df' not in st.session_state:
    st.session_state.materialy_df = pd.DataFrame([
        {"Materiál": "svitek POZINK 0,55x1000mm", "Interní kód SI": "0160P003", "Šířka (mm)": 1000, "Cena/m2": 200.0, "Max délka": 50000},
        {"Materiál": "svitek POZINK 0,55x670mm", "Interní kód SI": "0160P002", "Šířka (mm)": 670, "Cena/m2": 218.0, "Max délka": 50000},
        {"Materiál": "svitek TITANZINEK 0,6x1000mm", "Interní kód SI": "0160T003", "Šířka (mm)": 1000, "Cena/m2": 611.0, "Max délka": 50000}
    ])

if 'prvky_df' not in st.session_state:
    st.session_state.prvky_df = pd.DataFrame([
        {"Typ prvku": "Závětrná lišta spodní", "Ohyby": 6},
        {"Typ prvku": "Okapnice", "Ohyby": 2},
        {"Typ prvku": "Úžlabí", "Ohyby": 3},
        {"Typ prvku": "Parapet", "Ohyby": 3},
        {"Typ prvku": "Atypický výrobek", "Ohyby": 9}
    ])

if 'zakazka' not in st.session_state: st.session_state.zakazka = []
if 'config' not in st.session_state: st.session_state.config = {"cena_ohyb": 10.0, "max_delka": 4000}
if 'reset_counter' not in st.session_state: st.session_state.reset_counter = 0

mat_dict = {r["Materiál"]: r for _, r in st.session_state.materialy_df.iterrows()}
prv_dict = {r["Typ prvku"]: r for _, r in st.session_state.prvky_df.iterrows()}

tab_kalk, tab_nakres, tab_data = st.tabs(["🧮 Kalkulátor", "📐 Nákres", "⚙️ Ceník"])

with tab_data:
    st.session_state.materialy_df = st.data_editor(st.session_state.materialy_df, num_rows="dynamic", key="em")
    st.session_state.prvky_df = st.data_editor(st.session_state.prvky_df, num_rows="dynamic", key="ep")

with tab_kalk:
    col_in, col_res = st.columns([1, 2])
    
    with col_in:
        st.subheader("1. Obecné údaje")
        v_odberatel = st.text_input("Odběratel / Projekt", value=st.session_state.get('odberatel', ''))
        st.session_state.odberatel = v_odberatel
        v_mat = st.selectbox("Materiál", list(mat_dict.keys()))
        
        st.markdown("---")
        # --- ZDE ZAČÍNÁ SEKCE 2 ---
        st.subheader("2. Přidat položku")
        
        v_prvek = st.selectbox("Prvek", list(prv_dict.keys()))
        default_ohyby = int(prv_dict[v_prvek]["Ohyby"])
        
        with st.form("pridat_polozku_form", clear_on_submit=True):
            f_rs = st.number_input("Rozvinutá šíře - RŠ (mm)", min_value=10, value=250, step=1, key=f"rs_{st.session_state.reset_counter}")
            f_ohyby = st.number_input("Počet ohybů", value=default_ohyby, min_value=0, key=f"ohyby_{v_prvek}_{st.session_state.reset_counter}")
            f_m = st.number_input("Délka (m)", value=2.5, step=0.1, key=f"m_{st.session_state.reset_counter}")
            f_ks = st.number_input("Kusů", min_value=1, value=1, key=f"ks_{st.session_state.reset_counter}")
            f_prip = st.number_input("Atyp. příplatek/ks (Kč bez DPH)", value=0.0, step=10.0, key=f"prip_{st.session_state.reset_counter}")
            
            submitted = st.form_submit_button("➕ Přidat do zakázky", use_container_width=True)
            if submitted:
                st.session_state.zakazka.append({
                    "Prvek": v_prvek, "RŠ (mm)": f_rs, "Ohyby": f_ohyby,
                    "Metrů": f_m, "Kusů": f_ks, "Atyp příplatek/ks (Kč)": f_prip
                })
                st.session_state.reset_counter += 1
                st.rerun()
            
        if st.button("🗑️ Smazat celou zakázku", use_container_width=True):
            st.session_state.zakazka = []; st.session_state.calc_done = False; st.rerun()

    with col_res:
        # VIZUÁLNÍ VYROVNÁNÍ: Posuneme pravou stranu dolů tak, aby subheader "Výpočet" 
        # byl na úrovni levého subheaderu "2. Přidat položku"
        # 165px je přibližná výška sekce "1. Obecné údaje"
        st.markdown('<div style="margin-top: 165px;"></div>', unsafe_allow_html=True)
        
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
                        items.append({"id": idx+1, "Prvek": p['Prvek'], "L": p['Metrů']*1000, "rš": p['RŠ (mm)']})

                bins = pack_module_strips(items, m_data["Šířka (mm)"], conf["max_delka"])
                t_odvin = sum(b['odvinuto_mm'] for b in bins) / 1000
                c_mat = (t_odvin * (m_data["Šířka (mm)"]/1000)) * m_data["Cena/m2"]
                
                st.session_state.res = {"c_mat": c_mat, "c_prace": c_prace, "c_prip": c_prip, "bins": bins}
                st.session_state.calc_done = True; st.rerun()

            if st.session_state.get('calc_done'):
                r = st.session_state.res
                bez_dph = r["c_mat"] + r["c_prace"] + r["c_prip"]
                
                st.divider()
                st.write("**Souhrn kalkulace (bez DPH):**")
                m1, m2, m3 = st.columns(3)
                m1.metric("Materiál", f"{r['c_mat']:,.2f} Kč")
                m2.metric("Práce (Ohyby)", f"{r['c_prace']:,.2f} Kč")
                m3.metric("Atyp. příplatky", f"{r['c_prip']:,.2f} Kč")
                
                st.write("**Celkové součty:**")
                m4, m5 = st.columns(2)
                m4.metric("CELKEM (bez DPH)", f"{bez_dph:,.2f}", delta_color="off")
                m5.metric("CELKEM (s DPH 21%)", f"{bez_dph*1.21:,.2f}")

# --- NÁKRESOVÁ ČÁST ---
with tab_nakres:
    if st.session_state.get('calc_done') and 'res' in st.session_state:
        for i, b in enumerate(st.session_state.res['bins']):
            fig, ax = plt.subplots(figsize=(10, 2.5))
            ax.add_patch(patches.Rectangle((0, 0), b['odvinuto_mm'], b['w_coil'], fill=False, edgecolor='black', lw=2))
            for p in b['placed']:
                ax.add_patch(patches.Rectangle((p['x'], p['y']), p['draw_w'], p['draw_h'], facecolor='skyblue', edgecolor='black', alpha=0.8))
                ax.text(p['x']+p['draw_w']/2, p['y']+p['draw_h']/2, f"Ř.{p['id']}\n{p['rš']}mm", ha='center', va='center', fontsize=7)
            st.write(f"**Modul {i+1}:** Odvinout {b['odvinuto_mm']/1000:.2f} m")
            st.pyplot(fig)
