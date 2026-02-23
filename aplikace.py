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
# CHYTRÝ 2D TETRIS ALGORITMUS (BSSF + Max Area Split + Rotace)
# ==========================================
class FreeRect:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

def pack_guillotine_multibin(items, coil_w, max_l, allow_rotation=True):
    # Třídění od největší plochy
    items.sort(key=lambda x: x['L'] * x['rš'], reverse=True)
    bins = []
    
    for item in items:
        placed = False
        for b in bins:
            best_idx = -1
            best_score = float('inf')
            best_area = float('inf')
            best_rotated = False
            
            for i, fr in enumerate(b['free_rects']):
                # 1. Zkouška bez rotace
                if fr.w >= item['L'] and fr.h >= item['rš']:
                    score = min(fr.w - item['L'], fr.h - item['rš'])
                    area = fr.w * fr.h
                    if score < best_score or (score == best_score and area < best_area):
                        best_score = score; best_area = area; best_idx = i; best_rotated = False
                
                # 2. Zkouška s rotací o 90°
                if allow_rotation and fr.w >= item['rš'] and fr.h >= item['L']:
                    score = min(fr.w - item['rš'], fr.h - item['L'])
                    area = fr.w * fr.h
                    if score < best_score or (score == best_score and area < best_area):
                        best_score = score; best_area = area; best_idx = i; best_rotated = True
            
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
                
                # Max Area Split
                area1_split1 = w * h_left
                area2_split1 = w_left * best_fr.h
                max_area_split1 = max(area1_split1, area2_split1)
                
                area1_split2 = best_fr.w * h_left
                area2_split2 = w_left * h
                max_area_split2 = max(area1_split2, area2_split2)
                
                if max_area_split1 > max_area_split2:
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
            # Určení rotace pro nový svitek
            will_rotate = False
            if allow_rotation and coil_w >= item['L'] and item['rš'] <= max_l:
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
            
            area1_split1 = w * h_left; area2_split1 = w_left * coil_w
            max_area_split1 = max(area1_split1, area2_split1)
            
            area1_split2 = actual_max_l * h_left; area2_split2 = w_left * h
            max_area_split2 = max(area1_split2, area2_split2)
            
            if max_area_split1 > max_area_split2:
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
        {"Materiál": "H
