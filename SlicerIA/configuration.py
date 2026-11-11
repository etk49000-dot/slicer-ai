"""Catalogue indicatif des machines et calculs de coût locaux."""

# Valeurs indicatives en watts, et non mesures garanties de consommation moyenne.
# Le chauffage, le matériau et les conditions ambiantes font varier la puissance.
MACHINES = {
    "Anycubic": {
        "Kobra 4": 475,
        "Kobra X / Max": 500,
        "Kobra 3 Plus / Combo": 400,
        "Kobra 3": 400,
    },
    "Bambu Lab": {
        "X1-Carbon": 350,
        "P1S": 350,
        "P1P": 350,
        "A1": 350,
        "A1 mini": 150,
    },
    "Creality": {
        "K1 Max": 350,
        "K1": 350,
        "Ender-3 V3": 350,
        "Ender-3 V3 SE": 350,
    },
    "Elegoo": {
        "Neptune 4 Max": 450,
        "Neptune 4 Plus": 400,
        "Neptune 4 Pro": 350,
    },
    "Prusa": {
        "XL": 900,
        "MK4S": 240,
        "MINI+": 160,
    },
    "Qidi Tech": {
        "X-Max 3": 900,
        "X-Plus 3": 500,
        "Q1 Pro": 350,
    },
    "Snapmaker": {
        "U1 (Artisan / 3-en-1)": 350,
        "Artisan": 350,
        "J1": 350,
    },
}


def calculer_cout_matiere(poids_grammes, prix_bobine_un_kilo):
    """Calcule le coût du filament à partir du prix d'un kilogramme."""
    return poids_grammes / 1000 * prix_bobine_un_kilo


def calculer_cout_energie(heures, minutes, puissance_watts, tarif_kwh):
    """Estime le coût à puissance constante ; le tarif est exprimé en euros par kWh."""
    duree_heures = heures + minutes / 60
    return duree_heures * puissance_watts / 1000 * tarif_kwh
