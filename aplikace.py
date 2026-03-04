import streamlit as st
import pandas as pd
import math
import io
import copy
import random
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Stavinvest Konfigurátor", page_icon="✂️", layout="wide")
st.title("✂️ Stavinvest Konfigurátor (Super-Algoritmus)")

# ==========================================
# SUPER-ALGORITMUS: Kombinuje různé přístupy a vybírá vítěze s nejmenším odvinem!
# ==========================================
class FreeRect:
    def __init__(self, x, y, w, h):
        self.x = x; self.y = y; self.w = w; self.h = h

# --- METODA 1: PRUHOVÁ (Skvělá pro stejné okapnice) ---
def pack_tinsmith_strips(items, coil_w, max_l, allow_rotation):
    test_items = copy.deepcopy(items)
    test_items.sort(key=lambda x: (x['rš'], x['L']), reverse=True)
    bins = []
    
    for item in test_items:
        best_bin = None
        best_strip = None
        best_score = float('inf')
        best_rotated = False
        
        orientations = [(item['L'], item['rš'], False)]
        if allow_rotation and item['L'] != item['rš']:
            orientations.append((item['rš'], item['L'], True))
            
        for b in bins:
            bin_max_x = max([s['current_x'] for s in b['strips']] + [0])
            for w, h, rotated in orientations:
                # Zkouška do existujícího pruhu
                for s in b['strips']:
                    if s['rs'] >= h:
                        new_strip_x = s['current_x'] + w
                        if new_strip_x <= max_l:
                            new_bin_max_x = max(bin_max_x, new_strip_x)
                            score = new_bin_max_x * 10000 + (s['rs'] - h)
                            if score < best_score:
                                best_score = score; best_bin = b; best_strip = s; best_rotated = rotated
                                
                # Zkouška nad existující pruhy
                current_y = sum(s['rs'] for s in b['strips'])
                if current_y + h <= coil_w and w <= max_l:
                    new_bin_max_x = max(bin_max_x, w)
                    score = new_bin_max_x * 10000 + 1
                    if score < best_score:
                        best_score = score; best_bin = b; best_strip = "NEW"; best_rotated = rotated
                        
        w, h, rotated = (item['rš'], item['L'], True) if best_rotated else (item['L'], item['rš'], False)
        item['rotated'] = rotated
        item['draw_w'] = w; item['draw_h'] = h
        
        if best_bin is not None:
            if best_strip == "NEW":
                current_y = sum(s['rs'] for s in best_bin['strips'])
                new_s = {'rs': h, 'y': current_y, 'current_x': w, 'items': [item]}
                item['x'] = 0; item['y'] = current_y
                best_bin['strips'].append(new_s)
            else:
                item['x'] = best_strip['current_x']; item['y'] = best_strip['y']
                best_strip['current_x'] += w
                best_strip['items'].append(item)
        else:
            if w <= max_l and h <= coil_w:
                new_s = {'rs': h, 'y': 0, 'current_x': w, 'items': [item]}
                item['x'] = 0; item['y'] = 0
                new_b = {'w_coil': coil_w, 'strips': [new_s]}
                bins.append(new_b)
            else:
                item['x'] = 0; item['y'] = 0
                new_b = {'w_coil': coil_w, 'strips': [{'rs': h, 'y': 0, 'current_x': w, 'items': [item]}]}
                bins.append(new_b)
                
    formatted_bins = []
    for b in bins:
        placed = []
        for s in b['strips']: placed.extend(s['items'])
        max_x = max([s['current_x'] for s in b['strips']] + [0])
        formatted_bins.append({'w_coil': b['w_coil'], 'odvinuto_mm': max_x, 'placed': placed})
    return formatted_bins

# --- METODA 2: GILOTINA (Skvělá na kombinování rozměrů) ---
def pack_guillotine_single(items, coil_w, max_l, allow_rotation):
    bins = []
    for item in items:
        best_bin_idx = -1; best_fr_idx = -1; best_score = (float('inf'), float('inf'), float('inf')); best_rotated = False
        
        for b_idx, b in enumerate(bins):
            current_max_x = max([0] + [p['x'] + p['draw_w'] for p in b['placed']])
            for i, fr in enumerate(b['free_rects']):
                if fr.w >= item['L'] and fr.h >= item['rš']:
                    w, h = item['L'], item['rš']
                    score = (max(current_max_x, fr.x + w), min(fr.w - w, fr.h - h), fr.y)
                    if score < best_score:
                        best_score = score; best_bin_idx = b_idx; best_fr_idx = i; best_rotated = False
                if allow_rotation and fr.w >= item['rš'] and fr.h >= item['L']:
                    w, h = item['rš'], item['L']
                    score = (max(current_max_x, fr.x + w), min(fr.w - w, fr.h - h), fr.y)
                    if score < best_score:
                        best_score = score; best_bin_idx = b_idx; best_fr_idx = i; best_rotated = True
                        
        if best_bin_idx != -1:
            b = bins[best_bin_idx]; best_fr = b['free_rects'][best_fr_idx]
            w = item['rš'] if best_rotated else item['L']
            h = item['L'] if best_rotated else item['rš']
            item['rotated'] = best_rotated; item['x'] = best_fr.x; item['y'] = best_fr.y
            item['draw_w'] = w; item['draw_h'] = h
            b['placed'].append(item)
            
            w_left = best_fr.w - w; h_left = best_fr.h - h
            if (w * h_left) > (w_left * h):
                fr_top = FreeRect(best_fr.x, best_fr.y + h, w, h_left)
                fr_right = FreeRect(best_fr.x + w, best_fr.y, w_left, best_fr.h)
            else:
                fr_top = FreeRect(best_fr.x, best_fr.y + h, best_fr.w, h_left)
                fr_right = FreeRect(best_fr.x + w, best_fr.y, w_left, h)
                
            b['free_rects'].pop(best_fr_idx)
            if fr_top.w > 0 and fr_top.h > 0: b['free_rects'].append(fr_top)
            if fr_right.w > 0 and fr_right.h > 0: b['free_rects'].append(fr_right)
            
        else:
            will_rotate = False
            if allow_rotation and coil_w >= item['L'] and item['rš'] <= max_l:
                if item['rš'] < item['L']: will_rotate = True
            w = item['rš'] if will_rotate else item['L']
            h = item['L'] if will_rotate else item['rš']
            
            actual_max_l = max(max_l, w)
            new_bin = {'free_rects': [], 'placed': [], 'w_coil': coil_w, 'max_l': actual_max_l}
            item['x'] = 0; item['y'] = 0; item['rotated'] = will_rotate; item['draw_w'] = w; item['draw_h'] = h
            new_bin['placed'].append(item)
            
            w_left = actual_max_l - w; h_left = coil_w - h
            if (w * h_left) > (w_left * h):
                fr_top = FreeRect(0, h, w, h_left); fr_right = FreeRect(w, 0, w_left, coil_w)
            else:
                fr_top = FreeRect(0, h, actual_max_l, h_left); fr_right = FreeRect(w, 0, w_left, h)
                
            if fr_top.w > 0 and fr_top.h > 0: new_bin['free_rects'].append(fr_top)
            if fr_right.w > 0 and fr_right.h > 0: new_bin['free_rects'].append(fr_right)
            bins.append(new_bin)
            
    for b in bins:
        b['odvinuto_mm'] = max([0] + [p['x'] + p['draw_w'] for p in b['placed']])
    return bins

# --- SPRAVEDLIVÝ SOUBOJ ALGORITMŮ ---
def pack_optimal_multibin(items, coil_w, max_l, allow_rotation=True):
    best_bins = None
    best_len = float('inf')
    
    # Kolo 1: Zkusit Pruhový systém (Často vyhrává pro stejné díly = 8 metrů)
    try:
        bins_strips = pack_tinsmith_strips(items, coil_w, max_l, allow_rotation)
        len_strips = sum(b['odvinuto_mm'] for b in bins_strips)
        if len_strips < best_len:
            best_len = len_strips
            best_bins = bins_strips
    except Exception:
        pass

    # Kolo 2: Gilotinové řazení
    sort_keys = [
        lambda x: (x['L'] * x['rš'], max(x['L'], x['rš'])),
        lambda x: (x['L'], x['rš']),
        lambda x: (x['rš'], x['L'])
    ]
    for key in sort_keys:
        test_items = copy.deepcopy(items)
        test_items.sort(key=key, reverse=True)
        bins_g = pack_guillotine_single(test_items, coil_w, max_l, allow_rotation)
        len_g = sum(b['odvinuto_mm'] for b in bins_g)
        if len_g < best_len:
            best_len = len_g
            best_bins = bins_g
            
    # Kolo 3: Gilotinová Monte Carlo Simulace (Náhodné zaplňování)
    for _ in range(50):
        test_items = copy.deepcopy(items)
        random.shuffle(test_items)
        bins_g = pack_guillotine_single(test_items, coil_w, max_l, allow_rotation)
        len_g = sum(b['odvinuto_mm'] for b in bins_g)
        if len_g < best_len:
            best_len = len_g
            best_bins = bins_g
            
    return best_bins

# --- INICIALIZACE NASTAVENÍ ---
if 'config' not in st.session_state:
    st.session_state.config = {"cena_ohyb": 10.0, "max_delka": 4000, "presah": 40, "povolit_rotaci": True}

# --- NAČTENÍ KOMPLETNÍCH DAT Z EXCELU ---
if 'materialy_df' not in st.session_state:
    m_data = [
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
    ]
    st.session_state.materialy_df = pd.DataFrame(m_data)

if 'prvky_df' not in st.session_state:
    p_data = [
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
    ]
    st.session_state.prvky_df = pd.DataFrame(p_data)

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
        st.session_state.config["povolit_rotaci"] = st.checkbox("🔄 Povolit otáčení dílů o 90° (Výrazná úspora materiálu)", value=st.session_state.config["povolit_rotaci"])

# ==========================================
# ZÁLOŽKA: DATA
# ==========================================
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
            df_zakazka = pd.DataFrame(st.session_state.zakazka)
            df_zakazka.index = df_zakazka.index + 1
            
            edited_zakazka_df = st.data_editor(
                df_zakazka,
                column_config={
                    "Prvek": st.column_config.SelectboxColumn("Prvek", options=list(prv_dict.keys()), required=True),
                    "Materiál": st.column_config.SelectboxColumn("Materiál", options=list(mat_dict.keys()), required=True),
                    "Metrů": st.column_config.NumberColumn("Metrů", min_value=0.1, step=0.1, required=True),
                    "Kusů": st.column_config.NumberColumn("Kusů", min_value=1, step=1, required=True)
                },
                num_rows="dynamic",
                use_container_width=True,
                key="editor_zakazka"
            )
            
            st.session_state.zakazka = edited_zakazka_df.to_dict('records')
            
            if st.button("🚀 SPOČÍTAT S VYUŽITÍM AI", type="primary", use_container_width=True):
                with st.spinner("🧠 AI testuje různé algoritmy pro nalezení absolutního minima materiálu..."):
                    fyzicke_kusy = {}
                    cena_prace = 0
                    conf = st.session_state.config
                    
                    for p in st.session_state.zakazka:
                        m_data = mat_dict[p["Materiál"]]
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
                            st.error(f"CHYBA: Prvek '{p['Prvek']}' je moc široký na svitek {p['Materiál']}!")
                            continue

                        cena_prace += (p_data["Ohyby"] * conf["cena_ohyb"]) * seg * p["Kusů"]
                        
                        if p["Materiál"] not in fyzicke_kusy:
                            fyzicke_kusy[p["Materiál"]] = []
                            
                        for _ in range(int(p["Kusů"] * seg)):
                            fyzicke_kusy[p["Materiál"]].append({"Prvek": p['Prvek'], "L": L_seg, "rš": p_data["RŠ (mm)"]})

                    vysledky_packing = {}
                    c_mat = 0; sumar = {}
                    
                    for mat_name, items in fyzicke_kusy.items():
                        w_coil = mat_dict[mat_name]["Šířka (mm)"]
                        cena_m2 = mat_dict[mat_name]["Cena/m2"]
                        max_tab_len = mat_dict[mat_name]["Max délka tabule (mm)"]
                        
                        bins = pack_optimal_multibin(items, w_coil, max_tab_len, conf["povolit_rotaci"])
                        
                        if bins:
                            tot_odvinuto = 0; tot_plocha = 0; tot_cena = 0
                            vysledky_packing[mat_name] = bins
                            
                            for b in bins:
                                max_x = b['odvinuto_mm']
                                odvinuto_m = max_x / 1000
                                plocha_m2 = odvinuto_m * (w_coil / 1000)
                                cena_za_svitek = plocha_m2 * cena_m2
                                
                                tot_odvinuto += odvinuto_m
                                tot_plocha += plocha_m2
                                tot_cena += cena_za_svitek
                                
                            c_mat += tot_cena
                            sumar[mat_name] = {
                                "Pásů/Tabulí (ks)": len(bins), 
                                "Celkem odvinout (m)": tot_odvinuto, 
                                "Plocha (m2)": tot_plocha, 
                                "Cena": tot_cena
                            }
                    
                    st.session_state.vysledky_packing = vysledky_packing
                    
                st.subheader("Souhrnná tabulka materiálu")
                st.dataframe(pd.DataFrame.from_dict(sumar, orient='index').style.format({
                    "Celkem odvinout (m)": "{:.2f}", 
                    "Plocha (m2)": "{:.2f}", 
                    "Cena": "{:.2f} Kč"
                }))
                
                r1, r2, r3 = st.columns(3)
                r1.metric("Materiál", f"{c_mat:,.2f} Kč")
                r2.metric("Práce (Ohyby)", f"{cena_prace:,.2f} Kč")
                r3.metric("CELKEM ZAKÁZKA (vč. DPH)", f"{(c_mat + cena_prace)*1.21:,.2f} Kč")

                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine='openpyxl') as wr:
                    edited_zakazka_df.to_excel(wr, sheet_name='Zadání', index=True)
                    pd.DataFrame.from_dict(sumar, orient='index').to_excel(wr, sheet_name='Souhrn_Materiálu')
                st.download_button("📥 Stáhnout Excel", buf.getvalue(), "kalkulace.xlsx", use_container_width=True)

# ==========================================
# ZÁLOŽKA: NÁKRES
# ==========================================
with tab_nakres:
    st.header("📐 Schéma řezů na svitku")
    if 'vysledky_packing' in st.session_state and st.session_state.vysledky_packing:
        barvy = ['#3498db', '#e74c3c', '#2ecc71', '#f1c40f', '#9b59b6', '#e67e22', '#1abc9c', '#34495e', '#16a085', '#27ae60', '#8e44ad', '#f39c12', '#d35400', '#c0392b']
        
        for mat_name, bins in st.session_state.vysledky_packing.items():
            st.subheader(f"Materiál: {mat_name}")
            
            for i, b in enumerate(bins):
                odvinuto_mm = b['odvinuto_mm']
                w_coil = b['w_coil']
                
                st.write(f"**Svitek {i+1}:** Odstřihnout/Odvinout **{odvinuto_mm / 1000:.2f} m** (Šířka svitku: {w_coil} mm, Účtovaná plocha: **{(odvinuto_mm/1000)*(w_coil/1000):.2f} m2**)")
                
                fig, ax = plt.subplots(figsize=(12, 2.5))
                ax.add_patch(patches.Rectangle((0, 0), odvinuto_mm, w_coil, fill=False, edgecolor='black', linewidth=2))
                
                unikatni_prvky = list(set([p['Prvek'] for p in b['placed']]))
                color_map = {prvek: barvy[idx % len(barvy)] for idx, prvek in enumerate(unikatni_prvky)}
                
                for p in b['placed']:
                    ax.add_patch(patches.Rectangle((p['x'], p['y']), p['draw_w'], p['draw_h'], facecolor=color_map[p['Prvek']], edgecolor='black', alpha=0.8))
                    font_size = 8 if p['draw_w'] > 500 else 6
                    rotace_text = " ↻" if p.get('rotated') else ""
                    ax.text(p['x'] + p['draw_w']/2, p['y'] + p['draw_h']/2, f"{p['Prvek']}\n({p['L']:.0f}x{p['rš']}){rotace_text}", 
                            ha='center', va='center', fontsize=font_size, color='white', weight='bold')
                
                ax.set_xlim(0, max(odvinuto_mm * 1.02, 100))
                ax.set_ylim(0, w_coil * 1.05)
                ax.set_xlabel("Délka odvinutého plechu (mm)")
                ax.set_ylabel("Šířka svitku (mm)")
                st.pyplot(fig)
            st.divider()
    else:
        st.info("Nejdříve proveďte výpočet v záložce Kalkulátor.")
