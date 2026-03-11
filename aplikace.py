import streamlit as st
import pandas as pd
import math
import io
import copy
import random
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Pro vkládání obrázků a formátování do Excelu
from openpyxl.drawing.image import Image as xlImage
from openpyxl.utils import get_column_letter

# --- NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Stavinvest Konfigurátor", page_icon="✂️", layout="wide")
st.title("✂️ Stavinvest Konfigurátor (Výrobní Moduly + Excel Export)")

# ==========================================
# MODULOVÝ PRUHOVÝ ALGORITMUS (PRO PRŮBĚŽNÉ ŘEZY)
# ==========================================
def pack_module_strips(items, coil_w, max_l, allow_rotation=True):
    best_modules = None
    best_len = float('inf')
    
    for iteration in range(200):
        test_items = copy.deepcopy(items)
        
        if iteration == 0:
            test_items.sort(key=lambda x: x['L'], reverse=True)
        elif iteration == 1:
            test_items.sort(key=lambda x: x['rš'], reverse=True)
        else:
            random.shuffle(test_items)
            
        for it in test_items:
            can_std = (it['L'] <= max_l and it['rš'] <= coil_w)
            can_rot = (allow_rotation and it['rš'] <= max_l and it['L'] <= coil_w)
            
            if iteration < 2:
                if can_std: it['dx'], it['dy'], it['rotated'] = it['L'], it['rš'], False
                elif can_rot: it['dx'], it['dy'], it['rotated'] = it['rš'], it['L'], True
                else: it['dx'], it['dy'], it['rotated'] = it['L'], it['rš'], False 
            else:
                if can_std and can_rot:
                    if random.random() > 0.5: it['dx'], it['dy'], it['rotated'] = it['rš'], it['L'], True
                    else: it['dx'], it['dy'], it['rotated'] = it['L'], it['rš'], False
                elif can_rot: it['dx'], it['dy'], it['rotated'] = it['rš'], it['L'], True
                else: it['dx'], it['dy'], it['rotated'] = it['L'], it['rš'], False

        groups = defaultdict(list)
        for it in test_items:
            groups[it['dy']].append(it)
            
        strips = []
        for dy, group_items in groups.items():
            if iteration % 2 == 0:
                group_items.sort(key=lambda x: x['dx'], reverse=True)
            else:
                random.shuffle(group_items)
                
            current_strips = []
            for it in group_items:
                placed = False
                for s in current_strips:
                    if s['l'] + it['dx'] <= max_l:
                        it['x'] = s['l']
                        s['items'].append(it)
                        s['l'] += it['dx']
                        placed = True
                        break
                if not placed:
                    it['x'] = 0
                    current_strips.append({'w': dy, 'l': it['dx'], 'items': [it]})
            strips.extend(current_strips)
            
        strips.sort(key=lambda s: s['l'], reverse=True)
        modules = []
        
        for s in strips:
            placed = False
            for m in modules:
                if m['used_w'] + s['w'] <= coil_w:
                    s['y'] = m['used_w']
                    for it in s['items']:
                        it['y'] = s['y']
                    m['strips'].append(s)
                    m['used_w'] += s['w']
                    m['l'] = max(m['l'], s['l'])
                    placed = True
                    break
            if not placed:
                s['y'] = 0
                for it in s['items']:
                    it['y'] = 0
                modules.append({'used_w': s['w'], 'l': s['l'], 'strips': [s]})
                
        tot_len = sum(m['l'] for m in modules)
        if tot_len < best_len:
            best_len = tot_len
            best_modules = modules

    formatted_bins = []
    if best_modules:
        for m in best_modules:
            placed = []
            for s in m['strips']:
                for it in s['items']:
                    it['draw_w'] = it['dx']
                    it['draw_h'] = it['dy']
                    placed.append(it)
            formatted_bins.append({
                'w_coil': coil_w,
                'odvinuto_mm': m['l'],
                'placed': placed
            })
            
    return formatted_bins

# --- INICIALIZACE NASTAVENÍ A DAT ---
if 'config' not in st.session_state:
    st.session_state.config = {"cena_ohyb": 10.0, "max_delka": 4000, "presah": 40, "povolit_rotaci": True}

if 'materialy_df' not in st.session_state:
    st.session_state.materialy_df = pd.DataFrame([
        {"Materiál": "FeZn svitek 0,55 mm", "Šířka (mm)": 1250, "Cena/m2": 200.0, "Max délka tabule (mm)": 50000},
        {"Materiál": "FeZn svitek lak PES 0,5 mm std barvy", "Šířka (mm)": 2000, "Cena/m2": 270.0, "Max délka tabule (mm)": 50000},
        {"Materiál": "FeZn svitek lak PES 0,5 mm nestandard", "Šířka (mm)": 1000, "Cena/m2": 288.0, "Max délka tabule (mm)": 50000},
        {"Materiál": "Titanzinek 0,6 mm", "Šířka (mm)": 1500, "Cena/m2": 611.0, "Max délka tabule (mm)": 50000},
        {"Materiál": "Titanzinek 0,7 mm", "Šířka (mm)": 1250, "Cena/m2": 714.0, "Max délka tabule (mm)": 50000},
        {"Materiál": "Cu svitek 0,55 mm", "Šířka (mm)": 2000, "Cena/m2": 2119.0, "Max délka tabule (mm)": 50000},
        {"Materiál": "Hliník 0,6 mm J+SF PES (MTC)", "Šířka (mm)": 1000, "Cena/m2": 400.0, "Max délka tabule (mm)": 50000},
        {"Materiál": "Hliník 0,7 mm O+SF PES (MTC)", "Šířka (mm)": 1500, "Cena/m2": 530.0, "Max délka tabule (mm)": 50000},
        {"Materiál": "Comax FALC 0,7mm PES", "Šířka (mm)": 1750, "Cena/m2": 550.0, "Max délka tabule (mm)": 50000},
        {"Materiál": "Comax FALC 0,7mm Cortex", "Šířka (mm)": 2500, "Cena/m2": 590.0, "Max délka tabule (mm)": 50000},
        {"Materiál": "Prefa CLR", "Šířka (mm)": 1300, "Cena/m2": 457.0, "Max délka tabule (mm)": 50000},
        {"Materiál": "PREFA Prefalz", "Šířka (mm)": 1700, "Cena/m2": 580.0, "Max délka tabule (mm)": 50000},
        {"Materiál": "PVC ROOFPLAN 7035", "Šířka (mm)": 1800, "Cena/m2": 591.0, "Max délka tabule (mm)": 50000},
        {"Materiál": "Bauder PVC svitek 7035", "Šířka (mm)": 2600, "Cena/m2": 840.0, "Max délka tabule (mm)": 50000},
        {"Materiál": "ATYP", "Šířka (mm)": 1250, "Cena/m2": 0.0, "Max délka tabule (mm)": 50000},
        {"Materiál": "Výroba z materiálu zákazníka", "Šířka (mm)": 1250, "Cena/m2": 0.0, "Max délka tabule (mm)": 50000}
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
# ZÁLOŽKA: NASTAVENÍ A DATA
# ==========================================
with tab_nastaveni:
    st.header("🔧 Globální parametry")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.config["cena_ohyb"] = st.number_input("Cena za ohyb (Kč)", value=float(st.session_state.config["cena_ohyb"]))
        st.session_state.config["presah"] = st.number_input("Přesah spojů (mm)", value=int(st.session_state.config["presah"]))
    with c2:
        st.session_state.config["max_delka"] = st.number_input("Délka ohýbačky (mm)", value=int(st.session_state.config["max_delka"]))
        st.session_state.config["povolit_rotaci"] = st.checkbox("🔄 Povolit otáčení dílů o 90°", value=st.session_state.config["povolit_rotaci"])

with tab_data:
    st.header("⚙️ Správa dat")
    st.info("Základní maximální délka svitku/tabule je nyní nastavena na 50 metrů (50 000 mm).")
    st.session_state.materialy_df = st.data_editor(st.session_state.materialy_df, num_rows="dynamic", key="em", use_container_width=True)
    st.session_state.prvky_df = st.data_editor(st.session_state.prvky_df, num_rows="dynamic", key="ep", use_container_width=True)

# ==========================================
# ZÁLOŽKA: KALKULÁTOR
# ==========================================
with tab_kalk:
    col_in, col_res = st.columns([1, 2])
    with col_in:
        st.header("1. Obecné údaje")
        v_odberatel = st.text_input("Odběratel / Název zakázky", st.session_state.get('odberatel', ''))
        st.session_state.odberatel = v_odberatel
        
        v_mat = st.selectbox("Materiál (pro celou zakázku)", list(mat_dict.keys()))
        
        st.header("2. Přidat položku")
        v_prvek = st.selectbox("Prvek", list(prv_dict.keys()))
        
        default_ohyby = int(prv_dict[v_prvek]["Ohyby"]) if v_prvek in prv_dict else 0
        v_ohyby = st.number_input("Počet ohybů (lze upravit)", value=default_ohyby, min_value=0)
        v_m = st.number_input("Délka (m)", value=2.5, step=0.1)
        v_ks = st.number_input("Kusů", min_value=1, value=1)
        
        if st.button("➕ Přidat do zakázky", type="primary", use_container_width=True):
            st.session_state.zakazka.append({
                "Prvek": v_prvek,
                "Ohyby": v_ohyby,
                "Metrů": v_m, 
                "Kusů": v_ks
            })
            st.rerun()
            
        if st.button("🗑️ Smazat vše", use_container_width=True):
            st.session_state.zakazka = []
            st.session_state.generated_figs = []
            st.session_state.calc_done = False
            st.rerun()

    with col_res:
        st.header("Výpočet a Optimalizace")
        if st.session_state.zakazka:
            df_zakazka = pd.DataFrame(st.session_state.zakazka)
            df_zakazka.insert(0, 'Řádek', range(1, len(df_zakazka) + 1))
            
            edited_zakazka_df = st.data_editor(
                df_zakazka,
                column_config={
                    "Řádek": st.column_config.Column("Řádek", disabled=True),
                    "Prvek": st.column_config.SelectboxColumn("Prvek", options=list(prv_dict.keys()), required=True),
                    "Ohyby": st.column_config.NumberColumn("Ohyby", min_value=0, step=1, required=True),
                    "Metrů": st.column_config.NumberColumn("Metrů", min_value=0.1, step=0.1, required=True),
                    "Kusů": st.column_config.NumberColumn("Kusů", min_value=1, step=1, required=True)
                },
                hide_index=True,
                num_rows="dynamic",
                use_container_width=True,
                key="editor_zakazka"
            )
            
            updated_zakazka = edited_zakazka_df.drop(columns=['Řádek']).to_dict('records')
            st.session_state.zakazka = updated_zakazka
            
            if st.button("🚀 SPOČÍTAT ZAKÁZKU", type="primary", use_container_width=True):
                with st.spinner("🧠 Vytvářím výrobní moduly pro 4m stroje a kreslím plány..."):
                    items = []
                    cena_prace = 0
                    conf = st.session_state.config
                    m_data = mat_dict[v_mat]
                    
                    for idx, p in enumerate(st.session_state.zakazka):
                        row_id = idx + 1 
                        p_data = prv_dict[p["Prvek"]]
                        L_mm = p["Metrů"] * 1000
                        
                        seg = 1 if L_mm <= conf["max_delka"] else math.ceil((L_mm - conf["presah"]) / (conf["max_delka"] - conf["presah"]))
                        L_seg = (L_mm + (seg - 1) * conf["presah"]) / seg
                        
                        if conf["povolit_rotaci"]:
                            vejde_se = (p_data["RŠ (mm)"] <= m_data["Šířka (mm)"]) or \
                                       (L_seg <= m_data["Šířka (mm)"] and p_data["RŠ (mm)"] <= m_data["Max délka tabule (mm)"])
                        else:
                            vejde_se = (p_data["RŠ (mm)"] <= m_data["Šířka (mm)"])
                            
                        if not vejde_se:
                            st.error(f"CHYBA na řádku {row_id}: Prvek '{p['Prvek']}' je moc široký na svitek {v_mat}!")
                            continue

                        cena_prace += (p["Ohyby"] * conf["cena_ohyb"]) * seg * p["Kusů"]
                        
                        for _ in range(int(p["Kusů"] * seg)):
                            items.append({"id": row_id, "Prvek": p['Prvek'], "L": L_seg, "rš": p_data["RŠ (mm)"]})

                    if items:
                        w_coil = m_data["Šířka (mm)"]
                        cena_m2 = m_data["Cena/m2"]
                        max_tab_len = min(m_data["Max délka tabule (mm)"], conf["max_delka"])
                        
                        bins = pack_module_strips(items, w_coil, max_tab_len, conf["povolit_rotaci"])
                        
                        tot_odvinuto = 0; tot_plocha = 0; tot_cena_mat = 0
                        for b in bins:
                            odvinuto_m = b['odvinuto_mm'] / 1000
                            plocha_m2 = odvinuto_m * (w_coil / 1000)
                            
                            tot_odvinuto += odvinuto_m
                            tot_plocha += plocha_m2
                            tot_cena_mat += plocha_m2 * cena_m2
                            
                        sumar = {
                            "Počet 4m Modulů (ks)": len(bins), 
                            "Celkem odvinout (m)": tot_odvinuto, 
                            "Plocha (m2)": tot_plocha, 
                            "Cena materiálu": tot_cena_mat
                        }
                        
                        st.session_state.sumar = sumar
                        st.session_state.cena_prace = cena_prace
                        st.session_state.c_mat = tot_cena_mat
                        
                        figs = []
                        barvy = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#e67e22', '#1abc9c', '#34495e', '#16a085', '#27ae60', '#8e44ad', '#f39c12', '#d35400', '#c0392b']
                        
                        for i, b in enumerate(bins):
                            odvinuto_mm = b['odvinuto_mm']
                            fig, ax = plt.subplots(figsize=(12, 2.5))
                            ax.add_patch(patches.Rectangle((0, 0), odvinuto_mm, w_coil, fill=False, edgecolor='black', linewidth=2))
                            
                            for p in b['placed']:
                                color = barvy[(p['id'] - 1) % len(barvy)] 
                                ax.add_patch(patches.Rectangle((p['x'], p['y']), p['draw_w'], p['draw_h'], facecolor=color, edgecolor='black', alpha=0.8))
                                font_size = 8 if p['draw_w'] > 500 else 6
                                rotace_text = " ↻" if p.get('rotated') else ""
                                ax.text(p['x'] + p['draw_w']/2, p['y'] + p['draw_h']/2, f"Ř.{p['id']} {p['Prvek']}\n({p['L']:.0f}x{p['rš']}){rotace_text}", 
                                        ha='center', va='center', fontsize=font_size, color='white', weight='bold')
                            
                            # KLÍČOVÁ OPRAVA: Pevné měřítko pro reálné zobrazení délek!
                            osa_x_max = max(max_tab_len, 100) 
                            ax.set_xlim(0, osa_x_max * 1.02)
                            
                            ax.set_ylim(0, w_coil * 1.05)
                            ax.set_xlabel("Délka modulu (mm)")
                            ax.set_ylabel("Šířka svitku (mm)")
                            ax.set_title(f"Modul {i+1}: Ustřihnout {odvinuto_mm/1000:.2f} m")
                            figs.append((b, fig))
                        
                        st.session_state.generated_figs = figs
                        st.session_state.calc_done = True
                        st.session_state.v_mat = v_mat

            if st.session_state.get('calc_done', False):
                st.divider()
                st.subheader("Souhrnná kalkulace")
                st.dataframe(pd.DataFrame.from_dict(st.session_state.sumar, orient='index').style.format("{:.2f}"))
                
                c_mat = st.session_state.c_mat
                cena_prace = st.session_state.cena_prace
                r1, r2, r3 = st.columns(3)
                r1.metric("Materiál", f"{c_mat:,.2f} Kč")
                r2.metric("Práce (Ohyby)", f"{cena_prace:,.2f} Kč")
                r3.metric("CELKEM ZAKÁZKA (vč. DPH)", f"{(c_mat + cena_prace)*1.21:,.2f} Kč")

                # EXPORT DO EXCELU (S AUTOMATICKOU ŠÍŘKOU SLOUPCŮ)
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as wr:
                    info_df = pd.DataFrame([
                        {"Parametr": "Odběratel / Zakázka", "Hodnota": st.session_state.odberatel},
                        {"Parametr": "Materiál", "Hodnota": st.session_state.v_mat}
                    ])
                    info_df.to_excel(wr, sheet_name='Zadání', index=False, startrow=0)
                    
                    df_out = pd.DataFrame(st.session_state.zakazka)
                    df_out.insert(0, 'Řádek', range(1, len(df_out) + 1))
                    df_out.to_excel(wr, sheet_name='Zadání', index=False, startrow=4)
                    
                    pd.DataFrame.from_dict(st.session_state.sumar, orient='index').to_excel(wr, sheet_name='Souhrn_Materiálu')
                    
                    # Formátování sloupců (Automatická šířka podle textu)
                    wb = wr.book
                    for sheet_name in ['Zadání', 'Souhrn_Materiálu']:
                        ws = wr.sheets[sheet_name]
                        for col in ws.columns:
                            max_length = 0
                            column_letter = col[0].column_letter
                            for cell in col:
                                try:
                                    if cell.value:
                                        max_length = max(max_length, len(str(cell.value)))
                                except:
                                    pass
                            adjusted_width = (max_length + 2)
                            ws.column_dimensions[column_letter].width = adjusted_width
                    
                    # Generování obrázků do třetího listu
                    ws_img = wb.create_sheet('Výrobní nákresy')
                    ws_img.column_dimensions['A'].width = 50 
                    
                    row_offset = 1
                    for idx, (b, fig) in enumerate(st.session_state.generated_figs):
                        ws_img.cell(row=row_offset, column=1, value=f"Modul {idx+1}: Odvinout {b['odvinuto_mm']/1000:.2f} m")
                        row_offset += 1
                        img_data = io.BytesIO()
                        fig.savefig(img_data, format='png', bbox_inches='tight', dpi=100)
                        img_data.seek(0)
                        img = xlImage(img_data)
                        ws_img.add_image(img, f"A{row_offset}")
                        row_offset += 18 
                        
                st.download_button("📥 Stáhnout Excel vč. Nákresů", buf.getvalue(), "Kalkulace_a_vyroba.xlsx", use_container_width=True)

# ==========================================
# ZÁLOŽKA: NÁKRES
# ==========================================
with tab_nakres:
    st.header("📐 Výrobní plány pro 4m stroje")
    if st.session_state.get('generated_figs'):
        for i, (b, fig) in enumerate(st.session_state.generated_figs):
            st.write(f"**Modul {i+1}:** Odvinout/Ustřihnout napříč na **{b['odvinuto_mm'] / 1000:.2f} m**")
            st.pyplot(fig)
            st.divider()
    else:
        st.info("Nejdříve proveďte výpočet v záložce Kalkulátor.")
