import streamlit as st
import pandas as pd
import numpy as np

# ---------------------------------------------------------
# 1. 9x9 SBC GRID DEFINITION
# ---------------------------------------------------------
# This is a template matrix. In a full production system, you will 
# map all 28 Nakshatras (outer edge), Rashis, and Swaras/Varnas.
# For intraday stock tracking, we focus on the Consonants/Syllables.

sbc_matrix = [
    # Row 0 (Top Edge)
    ["A (Vowel)", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Aa (Vowel)"],
    # Row 1
    ["Bharani", "Ta (TCS)", "Tha", "Da", "Dha", "Na", "Pa", "Pha", "Magha"],
    # Row 2
    ["Ashwini", "Cha", "Vrshabha", "Mithuna", "Karka", "Simha", "Kanya", "Ba (Bajaj)", "Purva Phalguni"],
    # Row 3
    ["Revati", "Kha", "Mesha", "O (Vowel)", "U (Vowel)", "I (Vowel)", "Tula", "Bha", "Uttara Phalguni"],
    # Row 4
    ["Uttara Bhadrapada", "Ka", "Meena", "Au (Vowel)", "Brahma (Center)", "Ae (Vowel)", "Vrishchika", "Ma (M&M)", "Hasta"],
    # Row 5
    ["Purva Bhadrapada", "Ha", "Kumbha", "Am (Vowel)", "Ah (Vowel)", "E (Vowel)", "Dhanu", "Ya", "Chitra"],
    # Row 6
    ["Shatabhisha", "Sa (SBI)", "Makara", "Ra (Reliance)", "La", "Va", "Sha", "Ra", "Swati"],
    # Row 7
    ["Dhanishta", "Gha", "Ga", "Ccha", "Ca", "Nga", "Jha", "Ja", "Vishakha"],
    # Row 8 (Bottom Edge)
    ["Uu (Vowel)", "Shravana", "Abhijit", "Uttara Ashadha", "Purva Ashadha", "Mula", "Jyeshtha", "Anuradha", "Ii (Vowel)"]
]

# ---------------------------------------------------------
# 2. COORDINATE LOOKUP DICTIONARY
# ---------------------------------------------------------
# To calculate Vedhas quickly, we need to know the exact (row, col) 
# of any given element without looping through the matrix every time.

def build_coordinate_map(matrix):
    coord_map = {}
    for r in range(9):
        for c in range(9):
            element = matrix[r][c]
            # Clean up the string to use as a key (e.g., "Ta (TCS)" -> "Ta")
            base_key = element.split(" ")[0] 
            coord_map[base_key] = (r, c)
            # Also store the full name for UI display
            coord_map[element] = (r, c) 
    return coord_map

SBC_COORDS = build_coordinate_map(sbc_matrix)
