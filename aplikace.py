import streamlit as st
import pandas as pd
import math
import io
import copy
import random
import os
import json
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from openpyxl.drawing.image import Image as xlImage
from openpyxl.utils import get_column_letter

# --- NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Konfigurátor Stavinvest", page_icon="✂️", layout="wide")

# ==========================================
# 🔒 PŘIHLAŠOVACÍ ÚDAJE
# ==========================================
UZIVATELE = {
    "admin@stavinvest.cz": "HlavniKlempir!",
    "test1@stavinvest.cz": "PlechovaStrecha1",
    "test2@stavinvest.cz": "Okapnice2026",
    "test3@stavinvest.cz": "TitanzinekRulez",
    "test4@stavinvest.cz": "FalcujemeDobre",
    "test5@stavinvest.cz": "OhybackaStroj",
    "test6@stavinvest.cz": "SvitekPlechu99",
    "test7@stavinvest.cz": "KlempiroveCZ",
    "test8@stavinvest.cz": "ZavetrnaLista#",
    "test9@stavinvest.cz": "StavinvestPro",
    "test10@stavinvest.cz": "NuzkyNaPlech123"
}

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_user = ""

if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>🔒 Přihlášení do systému</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            email = st.text_input("E-mail")
            password = st.text_input("Heslo", type="password")
            submit = st.form_submit_button("Přihlásit se", use_container_width=True)

            if submit:
                if email in UZIVATELE and UZIVATELE[email] == password:
                    st.session_state.logged_in = True
                    st.session_state.current_user = email
                    st.rerun()
                else:
                    st.error("Chybný e-mail nebo heslo!")
    st.stop()

# --- BOČNÍ PANEL (Odhlášení) ---
st.sidebar.write(f"👤 Přihlášen(a): **{st.session_state.current_user}**")
if st.sidebar.button("🚪 Odhlásit se", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.current_user = ""
    st.rerun()

# ==========================================
# HLAVNÍ APLIKACE
# ==========================================
st.title("✂️ Konfigurátor Stavinvest")
st.info("💡 **Nová funkce:** Rozvinutou šíři (RŠ) nyní zadáváte ručně v milimetrech pro každý prvek zvlášť.")

# ==========================================
# MODULOVÝ PRUHOVÝ ALGORITMUS (POUZE PODÉLNÉ ŘEZY)
# ==========================================
def pack_module_strips(items, coil_w, max_l, allow_rotation=False):
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

# ==========================================
# SOUBORY PRO TRVALÉ ULOŽENÍ
# ==========================================
FILE_MAT = "materialy_db.csv"
FILE_PRV = "prvky_db.csv"
FILE_CONF = "config_db.json"

# --- INICIALIZACE NASTAVENÍ A DAT ---
if 'config' not in st.session_state:
    st.session_state.config = {"cena_ohyb": 12.0, "max_delka": 4000, "presah": 40}
    if os.path.exists(FILE_CONF):
        with open(FILE_CONF, "r", encoding="utf-8") as f:
            st.session_state.config.update(json.load(f))

# Načtení materiálů (s aktualizovanými cenami)
if 'materialy_df' not in st.session_state:
    if os.path.exists(FILE_MAT):
        st.session_state.materialy_df = pd.read_csv(FILE_MAT)
    else:
        st.session_state.materialy_df = pd.DataFrame([
            {"Materiál": "svitek POZINK 0,55x1000mm", "Interní kód SI": "0160P003", "Šířka (mm)": 1000, "Cena/m2": 200.0, "Max délka tabule (mm)": 50000},
            {"Materiál": "svitek POZINK 0,55x670mm", "Interní kód SI": "0160P002", "Šířka (mm)": 670, "Cena/m2": 218.0, "Max délka tabule (mm)": 50000},
            {"Materiál": "svitek POZINK 0,5x1250mm PES STANDARD BARVY O+SF", "Interní kód SI": "0160LP0107016O+SF", "Šířka (mm)": 1250, "Cena/m2": 282.0, "Max délka tabule (mm)": 50000},
            {"Materiál": "svitek POZINK 0,5x1250mm PES NESTANDARD O+SF", "Interní kód SI": "0160LP0109010O+SF", "Šířka (mm)": 1250, "Cena/m2": 301.0, "Max délka tabule (mm)": 50000},
            {"Materiál": "Comax FALC POZINK 0,5x620mm PES  šedá J+SF", "Interní kód SI": "0160LP0017016J+SF", "Šířka (mm)": 620, "Cena/m2": 456.0, "Max délka tabule (mm)": 50000},
            {"Materiál": "svitek TITANZINEK 0,6x1000mm", "Interní kód SI": "0160T003", "Šířka (mm)": 1000, "Cena/m2": 672.0, "Max délka tabule (mm)": 50000},
            {"Materiál": "svitek TITANZINEK 0,6x670mm", "Interní kód SI": "0160T002", "Šířka (mm)": 670, "Cena/m2": 672.0, "Max délka tabule (mm)": 50000},
            {"Materiál": "svitek MĚĎ 0,55x1000mm", "Interní kód SI": "0160M011000", "Šířka (mm)": 1000, "Cena/m2": 2347.0, "Max délka tabule (mm)": 50000},
            {"Materiál": "svitek MĚĎ 0,55x670mm", "Interní kód SI": "0160M010670", "Šířka (mm)": 670, "Cena/m2": 2347.0, "Max délka tabule (mm)": 50000},
            {"Materiál": "PREFA svitek CLR 0,7x1000 PE", "Interní kód SI": "65P31105", "Šířka (mm)": 1000, "Cena/m2": 490.0, "Max délka tabule (mm)": 30000},
            {"Materiál": "PREFA svitek Prefalz 0,7x1000 hladký", "Interní kód SI": "65P40100", "Šířka (mm)": 1000, "Cena/m2": 619.0, "Max délka tabule (mm)": 30000},
            {"Materiál": "PREFA svitek  Prefalz 0,7x650 hladký", "Interní kód SI": "65P40200", "Šířka (mm)": 650, "Cena/m2": 619.0, "Max délka tabule (mm)": 50000},
            {"Materiál": "Comax FALC AL 0,7x600mm", "Interní kód SI": "0160ALCO0706007016", "Šířka (mm)": 600, "Cena/m2": 694.0, "Max délka tabule (mm)": 50000},
            {"Materiál": "tabule AL 0,6x1000x2000 PES jednostranná s folií", "Interní kód SI": "0150AL06100020007016J+SF", "Šířka (mm)": 1000, "Cena/m2": 518.0, "Max délka tabule (mm)": 2000},
            {"Materiál": "tabule PVC 0,6x1000x2000 ROOFPLAN 7035", "Interní kód SI": "0150PVC0037035", "Šířka (mm)": 1000, "Cena/m2": 591.0, "Max délka tabule (mm)": 2000}
        ])

# Načtení prvků
if 'prvky_df' not in st.session_state:
    if os.path.exists(FILE_PRV):
        st.session_state.prvky_df = pd.read_csv(FILE_PRV)
    else:
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

if 'zakazka' not in st.session_state:
    st.session_state.zakazka = []

if 'reset_counter' not in st.session_state:
    st.session_state.reset_counter = 0

mat_dict = {r["Materiál"]: r for _, r in st.session_state.materialy_df.iterrows()}
prv_dict = {r["Typ prvku"]: r for _, r in st.session_state.prvky_df.iterrows()}

# --- VYLEPŠENÁ POMOCNÁ FUNKCE PRO FORMÁTOVÁNÍ ČÍSEL ---
def fmt_cz(value):
    try:
        parts = f"{float(value):,.2f}".split('.')
        integer_part = parts[0].replace(',', ' ')
        return f"{integer_part},{parts[1]}"
    except (ValueError, TypeError):
        return value

# --- ZÁLOŽKY ---
tab_kalk, tab_nakres, tab_data = st.tabs(["🧮 Kalkulátor", "📐 Nákres 2D Řezů", "⚙️ Správa (Ceník a Nastavení)"])

# ==========================================
# ZÁLOŽKA: NASTAVENÍ A DATA
# ==========================================
with tab_data:
    st.header("⚙️ Správa dat (Ceník, materiály a nastavení)")
    
    if st.session_state.current_user == "admin@stavinvest.cz":
        st.write("Jako administrátor můžete upravovat globální nastavení, ceny a materiály.")
        
        # Admin si může upravit a uložit cenu za ohyb
        novy_ohyb = st.number_input("Cena za 1 ohyb (Kč)", value=float(st.session_state.config.get("cena_ohyb", 12.0)))
        
        edited_mat = st.data_editor(st.session_state.materialy_df, num_rows="dynamic", key="em", use_container_width=True)
        edited_prv = st.data_editor(st.session_state.prvky_df, num_rows="dynamic", key="ep", use_container_width=True)
        
        if st.button("💾 Uložit všechny změny trvale", type="primary"):
            # Uložení CSV
            edited_mat.to_csv(FILE_MAT, index=False)
            edited_prv.to_csv(FILE_PRV, index=False)
            
            # Uložení konfigurace (json)
            st.session_state.config["cena_ohyb"] = novy_ohyb
            with open(FILE_CONF, "w", encoding="utf-8") as f:
                json.dump(st.session_state.config, f)
                
            st.session_state.materialy_df = edited_mat
            st.session_state.prvky_df = edited_prv
            st.success("✅ Veškeré nastavení, ceníky a prvky byly úspěšně uloženy!")
    else:
        st.warning("Pohled pro čtení. Úpravy nastavení může provádět pouze administrátor.")
        st.write(f"**Aktuální cena za ohyb:** {fmt_cz(st.session_state.config.get('cena_ohyb', 12.0))} Kč")
        st.dataframe(st.session_state.materialy_df, use_container_width=True)
        st.dataframe(st.session_state.prvky_df, use_container_width=True)

# ==========================================
# ZÁLOŽKA: KALKULÁTOR
# ==========================================
with tab_kalk:
    
    # 1. OBECNÉ ÚDAJE (CELÁ ŠÍŘKA STRÁNKY)
    st.header("1. Obecné údaje")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.session_state.odberatel = st.text_input("Odběratel / Název zakázky", st.session_state.get('odberatel', ''))
        v_mat = st.selectbox("Materiál (pro celou zakázku)", list(mat_dict.keys()))
    with col_t2:
        st.write("**Parametry výroby:**")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.session_state.config["max_delka"] = st.number_input("Délka ohýbačky (mm)", value=int(st.session_state.config.get("max_delka", 4000)))
        with col_p2:
            st.session_state.config["presah"] = st.number_input("Přesah spojů (mm)", value=int(st.session_state.config.get("presah", 40)))
        
    st.markdown("---")

    # 2. PŘIDAT POLOŽKU A VÝPOČET (VEDLE SEBE)
    col_in, col_res = st.columns([1, 2])
    
    with col_in:
        st.header("2. Přidat položku")
        v_prvek = st.selectbox("Prvek", list(prv_dict.keys()))
        default_ohyby = int(prv_dict[v_prvek]["Ohyby"]) if v_prvek in prv_dict else 0
        
        with st.form("pridat_polozku_form", clear_on_submit=True):
            v_rs = st.number_input("Rozvinutá šíře - RŠ (mm)", min_value=10, value=250, step=1)
            v_ohyby = st.number_input("Počet ohybů", value=default_ohyby, min_value=0)
            v_m = st.number_input("Délka (m)", value=2.5, step=0.1)
            v_ks = st.number_input("Kusů", min_value=1, value=1)
            v_priplatek = st.number_input("Atyp. příplatek/ks (Kč - celá čísla)", value=0, step=10)
            
            submitted = st.form_submit_button("➕ Přidat do zakázky", use_container_width=True)
            if submitted:
                st.session_state.zakazka.append({
                    "Prvek": v_prvek,
                    "RŠ (mm)": v_rs,
                    "Ohyby": v_ohyby,
                    "Metrů": v_m, 
                    "Kusů": v_ks,
                    "Atyp příplatek/ks (Kč)": float(v_priplatek)
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
                    "RŠ (mm)": st.column_config.NumberColumn("RŠ (mm)", min_value=10, step=1, required=True),
                    "Ohyby": st.column_config.NumberColumn("Ohyby", min_value=0, step=1, required=True),
                    "Metrů": st.column_config.NumberColumn("Metrů", min_value=0.1, step=0.1, required=True),
                    "Kusů": st.column_config.NumberColumn("Kusů", min_value=1, step=1, required=True),
                    "Atyp příplatek/ks (Kč)": st.column_config.NumberColumn("Atyp příplatek/ks (Kč)", min_value=0.0, step=1.0, required=True)
                },
                hide_index=True,
                num_rows="dynamic",
                use_container_width=True,
                key="editor_zakazka"
            )
            
            updated_zakazka = edited_zakazka_df.drop(columns=['Řádek']).to_dict('records')
            st.session_state.zakazka = updated_zakazka
            
            if st.button("🚀 SPOČÍTAT ZAKÁZKU", type="primary", use_container_width=True):
                with st.spinner("🧠 Vytvářím výrobní moduly pro stroje a kreslím plány..."):
                    
                    items = []
                    cena_prace = 0
                    cena_priplatky = 0
                    conf = st.session_state.config
                    m_data = mat_dict[v_mat]
                    
                    for idx, p in enumerate(st.session_state.zakazka):
                        row_id = idx + 1 
                        L_mm = p["Metrů"] * 1000
                        rs_mm = p["RŠ (mm)"]
                        
                        seg = 1 if L_mm <= conf["max_delka"] else math.ceil((L_mm - conf["presah"]) / (conf["max_delka"] - conf["presah"]))
                        L_seg = (L_mm + (seg - 1) * conf["presah"]) / seg
                        
                        vejde_se = (rs_mm <= m_data["Šířka (mm)"])
                            
                        if not vejde_se:
                            st.error(f"CHYBA na řádku {row_id}: Prvek '{p['Prvek']}' s RŠ {rs_mm} mm je moc široký na materiál {v_mat}!")
                            continue

                        # VÝPOČET PRÁCE: (počet ohybů * cena * metry * kusy)
                        cena_prace += (p["Ohyby"] * conf["cena_ohyb"]) * p["Metrů"] * p["Kusů"]
                        cena_priplatky += p.get("Atyp příplatek/ks (Kč)", 0.0) * p["Kusů"]
                        
                        for _ in range(int(p["Kusů"] * seg)):
                            items.append({"id": row_id, "Prvek": p['Prvek'], "L": L_seg, "rš": rs_mm})

                    if items:
                        w_coil = m_data["Šířka (mm)"]
                        cena_m2 = m_data["Cena/m2"]
                        max_tab_len = min(m_data["Max délka tabule (mm)"], conf["max_delka"])
                        
                        bins = pack_module_strips(items, w_coil, max_tab_len, allow_rotation=False)
                        
                        tot_odvinuto = 0
                        tot_hruba_plocha = 0
                        tot_cena_mat = 0
                        
                        for b in bins:
                            odvinuto_m = b['odvinuto_mm'] / 1000
                            hruba_plocha_modulu = odvinuto_m * (w_coil / 1000)
                            
                            tot_odvinuto += odvinuto_m
                            tot_hruba_plocha += hruba_plocha_modulu
                            tot_cena_mat += hruba_plocha_modulu * cena_m2
                            
                        sumar = {
                            "Počet Modulů (ks)": len(bins), 
                            "Celkem odvinout (m)": tot_odvinuto
                        }
                        
                        st.session_state.sumar = sumar
                        st.session_state.tot_odvinuto = tot_odvinuto
                        st.session_state.tot_hruba_plocha = tot_hruba_plocha
                        st.session_state.cena_prace = cena_prace
                        st.session_state.cena_priplatky = cena_priplatky
                        st.session_state.c_mat = tot_cena_mat
                        st.session_state.v_mat = v_mat
                        
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
                                rotace_text = ""
                                ax.text(p['x'] + p['draw_w']/2, p['y'] + p['draw_h']/2, f"Ř.{p['id']} {p['Prvek']}\n({p['L']:.0f}x{p['rš']}){rotace_text}", 
                                        ha='center', va='center', fontsize=font_size, color='white', weight='bold')
                            osa_x_max = max(max_tab_len, 100) 
                            ax.set_xlim(0, osa_x_max * 1.02)
                            ax.set_ylim(0, w_coil * 1.05)
                            ax.set_xlabel("Délka modulu (mm)")
                            ax.set_ylabel("Šířka materiálu (mm)")
                            ax.set_title(f"Modul {i+1}: Odvinout/Ustřihnout {odvinuto_mm/1000:.2f} m")
                            figs.append((b, fig))
                        
                        st.session_state.generated_figs = figs
                        st.session_state.calc_done = True

            if st.session_state.get('calc_done', False):
                st.divider()
                st.subheader("🧾 Souhrnná kalkulace")
                
                tot_hruba_plocha = float(st.session_state.tot_hruba_plocha)
                c_mat = float(st.session_state.c_mat)
                cena_prace = float(st.session_state.cena_prace)
                cena_priplatky = float(st.session_state.get('cena_priplatky', 0))
                total_bez = c_mat + cena_prace + cena_priplatky
                total_s = total_bez * 1.21

                md_table = f"""
| Položka | Hodnota |
| :--- | ---: |
| Fakturovaná plocha (odvin × šířka svitku): | {fmt_cz(tot_hruba_plocha)} m² |
| **Materiál (výpočet z odvinu - bez DPH):** | **{fmt_cz(c_mat)} Kč** |
| Práce / Ohyby (bez DPH): | {fmt_cz(cena_prace)} Kč |
| Atypické příplatky (bez DPH): | {fmt_cz(cena_priplatky)} Kč |
| <span style="font-size: 1.1em; color: #333;">**CELKEM (bez DPH):**</span> | <span style="font-size: 1.1em; color: #333;">**{fmt_cz(total_bez)} Kč**</span> |
| <span style="font-size: 1.3em; color: #D32F2F;">**CELKEM (s DPH 21 %):**</span> | <span style="font-size: 1.3em; color: #D32F2F;">**{fmt_cz(total_s)} Kč**</span> |
"""
                st.markdown(md_table, unsafe_allow_html=True)

                # --- EXCEL EXPORT ---
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as wr:
                    info_df = pd.DataFrame([
                        {"Parametr": "Odběratel / Zakázka", "Hodnota": st.session_state.odberatel},
                        {"Parametr": "Materiál", "Hodnota": st.session_state.v_mat},
                        {"Parametr": "Nastavený přesah spojů (mm)", "Hodnota": st.session_state.config.get("presah", 40)}
                    ])
                    info_df.to_excel(wr, sheet_name='Zadání', index=False, startrow=0)
                    
                    df_out = pd.DataFrame(st.session_state.zakazka)
                    df_out.insert(0, 'Řádek', range(1, len(df_out) + 1))
                    
                    cena_ohyb_val = float(st.session_state.config.get("cena_ohyb", 12.0))
                    
                    df_out['Cena za ohyby (Kč)'] = df_out['Ohyby'] * cena_ohyb_val * df_out['Metrů'] * df_out['Kusů']
                    
                    total_row = {col: "" for col in df_out.columns}
                    total_row['Řádek'] = "CELKEM"
                    total_row['Atyp příplatek/ks (Kč)'] = cena_priplatky
                    total_row['Cena za ohyby (Kč)'] = df_out['Cena za ohyby (Kč)'].sum()
                    
                    df_out = pd.concat([df_out, pd.DataFrame([total_row])], ignore_index=True)
                    df_out.to_excel(wr, sheet_name='Zadání', index=False, startrow=5)
                    
                    kalkulace_startrow = 5 + len(df_out) + 2 
                    fin_data = [
                        {"Finální kalkulace": "Celkem odvinout z role (m)", "Hodnota / Částka": float(st.session_state.tot_odvinuto)},
                        {"Finální kalkulace": "Fakturovaná plocha z odvinu (m2)", "Hodnota / Částka": tot_hruba_plocha},
                        {"Finální kalkulace": "Materiál (výpočet z odvinu - bez DPH)", "Hodnota / Částka": c_mat},
                        {"Finální kalkulace": "Práce / Ohyby (bez DPH)", "Hodnota / Částka": cena_prace},
                        {"Finální kalkulace": "Atypické příplatky (bez DPH)", "Hodnota / Částka": cena_priplatky},
                        {"Finální kalkulace": "CELKEM (bez DPH)", "Hodnota / Částka": total_bez},
                        {"Finální kalkulace": "CELKEM (s DPH 21 %)", "Hodnota / Částka": total_s}
                    ]
                    pd.DataFrame(fin_data).to_excel(wr, sheet_name='Zadání', index=False, startrow=kalkulace_startrow)

                    prod_startrow = kalkulace_startrow + len(fin_data) + 2
                    prod_data = [
                        {"Výrobní parametry": "Počet Výrobních Modulů (ks)", "Hodnota": st.session_state.sumar["Počet Modulů (ks)"]}
                    ]
                    pd.DataFrame(prod_data).to_excel(wr, sheet_name='Zadání', index=False, startrow=prod_startrow)
                    
                    wb = wr.book
                    ws = wr.sheets['Zadání']
                    for col in ws.columns:
                        max_length = 0
                        column_letter = col[0].column_letter
                        for cell in col:
                            if isinstance(cell.value, float):
                                cell.number_format = '#,##0.00'
                            try:
                                if cell.value:
                                    max_length = max(max_length, len(str(cell.value)))
                            except:
                                pass
                        ws.column_dimensions[column_letter].width = (max_length + 2)
                    
                    if st.session_state.get('generated_figs'):
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
    st.header("📐 Výrobní plány pro stroje")
    if st.session_state.get('calc_done') and st.session_state.get('generated_figs'):
        for i, (b, fig) in enumerate(st.session_state.generated_figs):
            st.write(f"**Modul {i+1}:** Odvinout/Ustřihnout napříč na **{b['odvinuto_mm'] / 1000:.2f} m**")
            st.pyplot(fig)
            st.divider()
    else:
        st.info("Nejdříve proveďte výpočet v záložce Kalkulátor.")
