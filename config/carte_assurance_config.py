"""
Configuration pour la génération des cartes d'assurance.

Ce fichier contient les paramètres de configuration pour la génération
des cartes d'assurance médicale au format PDF.
"""
from pathlib import Path
from typing import Dict, Tuple, Optional

# Chemins par défaut
DEFAULT_OUTPUT_DIR = Path("cartes_assurance")
DEFAULT_FONT_DIR = Path("static/fonts")
DEFAULT_LOGO_PATH = Path("static/images/logo_hopital.png")
DEFAULT_WATERMARK_PATH = Path("static/images/watermark.png")

# Dimensions de la carte (en points A5 paysage)
CARD_WIDTH = 595.28  # 210mm en points
CARD_HEIGHT = 419.53  # 148mm en points
MARGIN = 20

# Couleurs (RVB)
COLORS = {
    'primary': (0, 0.4, 0.8),  # Bleu
    'secondary': (0.8, 0.2, 0.2),  # Rouge
    'text': (0.2, 0.2, 0.2),  # Noir
    'background': (1, 1, 1),  # Blanc
    'border': (0.8, 0.8, 0.8),  # Gris clair
}

# Polices
FONTS = {
    'regular': 'Helvetica',
    'bold': 'Helvetica-Bold',
    'title': 'Helvetica-Bold',
    'subtitle': 'Helvetica-Oblique',
}

# Tailles de police (en points)
FONT_SIZES = {
    'title': 14,
    'subtitle': 10,
    'normal': 9,
    'small': 8,
}

# Paramètres du QR code
QR_CODE_SETTINGS = {
    'version': 1,
    'box_size': 10,
    'border': 5,
    'fill_color': 'black',
    'back_color': 'white',
    'size': 150,  # Taille en pixels
}

# Paramètres de la photo
PHOTO_SETTINGS = {
    'width': 4.0,  # cm
    'height': 5.0,  # cm
    'border': 0.1,  # cm
    'border_color': COLORS['border'],
}

def get_card_size() -> Tuple[float, float]:
    """
    Retourne les dimensions de la carte en points.
    
    Returns:
        Tuple[float, float]: Largeur et hauteur en points
    """
    return CARD_WIDTH, CARD_HEIGHT

def get_available_fonts() -> Dict[str, str]:
    """
    Retourne les polices disponibles.
    
    Returns:
        Dict[str, str]: Dictionnaire des polices disponibles
    """
    return FONTS.copy()

def get_color(name: str, default: Optional[Tuple[float, float, float]] = None) -> Tuple[float, float, float]:
    """
    Récupère une couleur par son nom.
    
    Args:
        name: Nom de la couleur
        default: Valeur par défaut si la couleur n'existe pas
        
    Returns:
        Tuple[float, float, float]: Couleur RVB (valeurs entre 0 et 1)
    """
    return COLORS.get(name.lower(), default or (0, 0, 0))  # Noir par défaut

def get_font_size(size_name: str, default: int = 10) -> int:
    """
    Récupère une taille de police par son nom.
    
    Args:
        size_name: Nom de la taille de police
        default: Valeur par défaut si la taille n'existe pas
        
    Returns:
        int: Taille de police en points
    """
    return FONT_SIZES.get(size_name.lower(), default)
