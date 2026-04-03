"""
Core Mappings - User Input to SCF Feature Mappings

This module preserves the EXACT mapping functions from the original app.py.
These mappings convert user-friendly inputs into SCF (Survey of Consumer Finances) 
compatible features for the risk tolerance model.

No changes should be made to these mappings as they are critical for model prediction.
"""

import streamlit as st
from typing import Dict


def map_age_to_features(age: int) -> Dict:
    """
    Map age to AGE and AGECL features.
    
    SCF 2022 AGECL definitions:
    - AGECL 1: 18-34
    - AGECL 2: 35-44
    - AGECL 3: 45-54
    - AGECL 4: 55-64
    - AGECL 5: 65-74
    - AGECL 6: 75+
    """
    if age < 35:
        agecl = 1
    elif age < 45:
        agecl = 2
    elif age < 55:
        agecl = 3
    elif age < 65:
        agecl = 4
    elif age < 75:
        agecl = 5
    else:
        agecl = 6
    return {"AGE": age, "AGECL": agecl}


def map_education_to_features(education: str) -> Dict:
    """
    Map education level to EDUC feature.
    
    SCF 2022 EDUC definitions:
    - 8-9: High school/GED
    - 10-11: Some college or AA degree
    - 12: Bachelor's degree
    - 13: Master's degree
    - 14: Doctoral/Professional degree
    """
    education_map = {
        "Less than High School": 8,
        "High School/GED": 9,
        "Some College": 11,
        "Bachelor's": 12,
        "Master's": 13,
        "Doctoral": 14
    }
    return {"EDUC": education_map.get(education, 11)}


def map_occupation_to_features(occupation: str) -> Dict:
    """
    Map occupation status to OCCAT1 and OCCAT2 features.
    
    SCF 2022 occupation categories:
    - OCCAT1: 1=Employee, 2=Self-employed, 3=Retired, 4=Not working
    - OCCAT2: Secondary classification
    """
    occ_map = {
        "Employee/Salaried": {"OCCAT1": 1, "OCCAT2": 2},
        "Self-Employed": {"OCCAT1": 2, "OCCAT2": 1},
        "Retired": {"OCCAT1": 3, "OCCAT2": 3},
        "Not Working/Student": {"OCCAT1": 4, "OCCAT2": 3}
    }
    return occ_map.get(occupation, {"OCCAT1": 1, "OCCAT2": 2})


def map_income_to_features(income_range: str) -> Dict:
    """
    Map income range to income-related features.
    
    SCF 2022 INCCAT definitions:
    - INCCAT 1: $0-31K
    - INCCAT 2: $31K-54K
    - INCCAT 3: $54K-91K
    - INCCAT 4: $91K-151K
    - INCCAT 5: $151K-249K
    - INCCAT 6: $249K+
    """
    income_to_inccat = {
        "Under $30K": 1,
        "$30K-$55K": 2,
        "$55K-$90K": 3,
        "$90K-$150K": 4,
        "$150K-$250K": 5,
        "Over $250K": 6
    }
    inccat = income_to_inccat.get(income_range, 3)
    return {
        "INCCAT": inccat,
        "NINCCAT": max(1, inccat - 1) if inccat > 1 else 1,
        "NINC2CAT": 1 if inccat <= 2 else (2 if inccat <= 4 else 3),
        "INCPCTLECAT": min(12, inccat * 2),
        "NINCPCTLECAT": max(1, inccat * 2 - 1),
        "INCQRTCAT": min(4, max(1, (inccat + 1) // 2 + 1)),
        "NINCQRTCAT": min(4, max(1, inccat // 2 + 1))
    }


def map_networth_to_features(networth_range: str) -> Dict:
    """
    Map net worth range to NWCAT and NWPCTLECAT features.
    
    SCF 2022 NWCAT definitions:
    - NWCAT 1: <$27K
    - NWCAT 2: $27K-193K
    - NWCAT 3: $193K-659K
    - NWCAT 4: $659K-1.94M
    - NWCAT 5: >$1.94M
    """
    nw_map = {
        "Under $30K": 1,
        "$30K-$200K": 2,
        "$200K-$700K": 3,
        "$700K-$2M": 4,
        "Over $2M": 5
    }
    nwcat = nw_map.get(networth_range, 3)
    nw_pctle_map = {1: 2, 2: 4, 3: 6, 4: 9, 5: 11}
    return {"NWCAT": nwcat, "NWPCTLECAT": nw_pctle_map.get(nwcat, 6)}


def map_assets_to_features(assets_range: str) -> Dict:
    """
    Map total assets range to ASSETCAT feature.
    
    SCF 2022 ASSETCAT definitions:
    - ASSETCAT 1: <$32K
    - ASSETCAT 2: $32K-212K
    - ASSETCAT 3: $213K-455K
    - ASSETCAT 4: $455K-1.06M
    - ASSETCAT 5: $1.06M-2.12M
    - ASSETCAT 6: >$2.12M
    """
    asset_map = {
        "Under $30K": 1,
        "$30K-$200K": 2,
        "$200K-$500K": 3,
        "$500K-$1M": 4,
        "$1M-$2M": 5,
        "Over $2M": 6
    }
    return {"ASSETCAT": asset_map.get(assets_range, 3)}


def build_model_features(
    age: int,
    education: str,
    occupation: str,
    income_range: str,
    networth_range: str,
    assets_range: str,
    has_emergency: bool,
    has_savings: bool,
    has_mutual: bool,
    has_retirement: bool
) -> Dict:
    """
    Build complete feature vector from user inputs using SCF mappings.
    
    This combines all mapping functions to create the full feature set
    required by the risk tolerance model.
    
    Parameters
    ----------
    age : int
        User's age (18-85)
    education : str
        Education level dropdown value
    occupation : str
        Occupation status dropdown value
    income_range : str
        Annual income range dropdown value
    networth_range : str
        Net worth range dropdown value
    assets_range : str
        Total assets range dropdown value
    has_emergency : bool
        Has emergency fund checkbox
    has_savings : bool
        Has savings account checkbox
    has_mutual : bool
        Has mutual funds checkbox
    has_retirement : bool
        Has retirement account checkbox
    
    Returns
    -------
    Dict
        Complete feature dictionary with all SCF-compatible features
    """
    features = {}
    features.update(map_age_to_features(age))
    features.update(map_education_to_features(education))
    features.update(map_occupation_to_features(occupation))
    features.update(map_income_to_features(income_range))
    features.update(map_networth_to_features(networth_range))
    features.update(map_assets_to_features(assets_range))
    features.update({
        "EMERGSAV": int(has_emergency),
        "HSAVFIN": int(has_savings),
        "HNMMF": int(has_mutual),
        "HRETQLIQ": int(has_retirement)
    })
    return features


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_user_inputs(inputs: Dict) -> tuple:
    """
    Validate user inputs and return (is_valid, error_message).
    """
    if not inputs.get('age') or inputs['age'] < 18 or inputs['age'] > 85:
        return False, "Age must be between 18 and 85"
    if not inputs.get('education'):
        return False, "Please select an education level"
    if not inputs.get('occupation'):
        return False, "Please select an occupation"
    if not inputs.get('income'):
        return False, "Please select an income range"
    if not inputs.get('networth'):
        return False, "Please select a net worth range"
    if not inputs.get('assets'):
        return False, "Please select an assets range"
    if not inputs.get('capital') or inputs['capital'] < 1000:
        return False, "Capital must be at least $1,000"
    return True, None
