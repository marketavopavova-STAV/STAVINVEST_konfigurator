import streamlit as st
import pandas as pd
import math
import io
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# --- NASTAVENÍ STRÁNKY ---
st.set_page_config(page_title="Stavinvest Konfigurátor", page_icon="✂️", layout="wide")
st.title("✂️ Stavinvest Konfigurátor vč. Chytrého 2D Tetrisu")

# ==========================================
# CHYTRÝ 2D TETRIS (MINIMALIZACE DÉLKY ODVINU + ROTACE)
# ==========================================
class FreeRect:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

def pack_guillotine_multibin(items, coil_w, max_l, allow_rotation=True):
    # Díly řadíme od největší plochy a nejdelší strany
    items.sort(key=lambda x: (x['L'] * x['rš'], max(x['L'], x['rš'])), reverse=True)
    bins = []
    
    for item in items:
        placed = False
        for b in bins:
            best_idx = -1
            # Prioritou je nyní minimální prodloužení svitku (new_max_x)
            best_score = (float('inf'), float('inf'), float('inf'), float('inf'))
            best_rotated = False
            
            # Jaká je aktuální délka odvinutého svitku v tomto pásu
            current_max_x = max([0] + [p['x'] + p['draw_w'] for p in b['placed']])
            
            for i, fr in enumerate(b['free_rects']):
                # 1. Zkouška BEZ rotace
                if fr.w >= item['L'] and fr.h >= item['rš']:
                    w, h = item['L'], item['rš']
                    new_max_x = max(current_max_x, fr.x + w)
                    fit_score = min(fr.w - w, fr.h - h)
                    # Skóre: (Minimální délka odvinutí, co nejvíce vlevo, co nejvíce dole, přesný spoj)
                    score = (new_max_x, fr.x, fr.y, fit_score)
                    if score < best_score:
                        best_score = score
                        best_idx = i
                        best_rotated = False
                
                # 2. Zkouška S rotací o 90°
                if allow_rotation and fr.w >= item['rš'] and fr.h >= item['L']:
                    w, h = item['rš'], item['L']
                    new_max_x = max(current_max_x, fr.x + w)
                    fit_score = min(fr.w - w, fr.h - h)
                    score = (new_max_x, fr.x, fr.y, fit_score)
                    if score < best_score:
                        best_score = score
                        best_idx = i
                        best_rotated = True
            
            if best_idx != -1:
                best_fr = b['free_rects'][best_idx]
                item['rotated'] = best_rotated
                w = item['rš'] if best_rotated else item['L']
                h = item['L'] if best_rotated else item['rš']
                
                item['x'] = best_fr.x
                item['y'] = best_fr.y
                item['draw_w'] = w
                item['draw_h'] = h
                b['placed'].append(item)
                
                w_left = best_fr.w - w
                h_left = best_fr.h - h
                
                # Gilotinový řez - zachování největší plochy
                area_top1 = w * h_left
                area_right1 = w_left * best_fr.h
                max_area1 = max(area_top1, area_right1)
                
                area_top2 = best_fr.w * h_left
                area_right2 = w_left * h
                max_area2 = max(area_top2, area_right2)
                
                if max_area1 >= max_area2:
                    fr_top = FreeRect(best_fr.x, best_fr.y + h, w, h_left)
                    fr_right = FreeRect(best_fr.x + w, best_fr.y, w_left, best_fr.h)
                else:
                    fr_top = FreeRect(best_fr.x, best_fr.y + h, best_fr.w, h_left)
                    fr_right = FreeRect(best_fr.x + w, best_fr.y, w_left, h)
                    
                b['free_rects'].pop(best_idx)
                if fr_top.w > 0 and fr_top.h > 0: b['free_rects'].append(fr_top)
                if fr_right.w > 0 and fr_right.h > 0: b['free_rects'].append(fr_right)
                placed = True
                break
                
        if not placed:
            # Zakládáme nový pás/tabuli
            will_rotate = False
            if allow_rotation and coil_w >= item['L'] and item['rš'] <= max_l:
                # Otočíme ho, pokud to ušetří délku odvinutí
                if item['rš'] < item['L']: 
                    will_rotate = True
                    
            w = item['rš'] if will_rotate else item['L']
            h = item['L'] if will_rotate else item['rš']
            
            actual_max_l = max(max_l, w)
            new_bin = {'free_rects': [], 'placed': [], 'w_coil': coil_w, 'max_l': actual_max_l}
            
            item['x'] = 0; item['y'] = 0; item['rotated'] = will_rotate
            item['draw_w'] = w; item['draw_h'] = h
            new_bin['placed'].append(item)
            
            w_left = actual_max_l - w
            h_left = coil_w - h
            
            area_top1 = w * h_left
            area_right1 = w_left * coil_w
            max_area1 = max(area_top1, area_right1)
            
            area_top2 = actual_max_l * h_left
            area_right2 = w_left * h
            max_area2 = max(area_top2, area_right2)
            
            if max_area1 >= max_area2:
                fr_top = FreeRect(0, h, w, h_left)
                fr_right = FreeRect(w, 0, w_left, coil_w)
            else:
                fr_top = FreeRect(0, h, actual_max_l, h_left)
                fr_right = FreeRect(w, 0, w_left, h)
                
            if fr_top.w > 0 and fr_top.h > 0: new_bin['free_rects'].append(fr_top)
            if fr_right.w > 0 and fr_right.h > 0: new_bin['free_rects'].append(fr_right)
            bins.append(new_bin)
            
    return bins

# --- INICIALIZACE NASTAVENÍ ---
if 'config' not in st.session_state:
    st.session_state.config = {"cena_ohyb": 10.0, "max_delka": 4000, "presah": 40, "povolit_rotaci": True}

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
        st.session_state.config["povolit_rotaci"] = st.checkbox("🔄 Povolit otáčení dílů o 90° (Výrazná úspora materiálu)", value=st.session_state.config["povolit_rotaci"])

# ==========================================
# ZÁLOŽKA: DATA
# ==========================================
with tab_data:
    st.header("⚙️ Správa dat")
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
            st.table(df_zakazka)
            
            if st.button("🚀 SPOČÍTAT 2D", type="primary", use_container_width=True):
                st.divider()
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
                        vejde_se = (p_data["RŠ (mm)"] <= m_data["Šířka (mm)"]) or (L_seg <= m_data["Šířka (mm)"] and p_data["RŠ (mm)"] <= m_data["Max délka tabule (mm)"])
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
                    
                    bins = pack_guillotine_multibin(items, w_coil, max_tab_len, conf["povolit_rotaci"])
                    
                    if bins:
                        tot_odvinuto = 0; tot_plocha = 0; tot_cena = 0
                        vysledky_packing[mat_name] = bins
                        
                        for b in bins:
                            max_x = max([p['x'] + p['draw_w'] for p in b['placed']])
                            b['odvinuto_mm'] = max_x
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
                    df_zakazka.to_excel(wr, sheet_name='Zadání', index=True)
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
                
                st.write(f"**Pás {i+1}:** Odstřihnout **{odvinuto_mm / 1000:.2f} m** (Šířka svitku: {w_coil} mm, Účtovaná plocha: **{(odvinuto_mm/1000)*(w_coil/1000):.2f} m2**)")
                
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
