"""
Module pour la génération de cartes d'assurance médicale au format PDF.

Ce module fournit une classe pour générer des cartes d'assurance médicale personnalisées
avec les informations du patient, une photo, un code QR et des détails d'assurance.
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from io import BytesIO
import qrcode

from reportlab.lib.pagesizes import A5, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Importer la configuration
from ..config import carte_assurance_config as config

class CarteAssuranceGenerator:
    """
    Générateur de cartes d'assurance médicale au format PDF.
    
    Cette classe permet de générer des cartes d'assurance personnalisées pour les patients,
    incluant leurs informations personnelles, une photo, un code QR et des détails d'assurance.
    
    Attributes:
        output_dir (Path): Répertoire de sortie pour les cartes générées
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        """
        Initialise le générateur de cartes d'assurance.
        
        Args:
            output_dir (str, optional): Répertoire de sortie pour les cartes générées.
                                     Si non spécifié, utilise la valeur par défaut de la configuration.
        """
        # Utiliser le répertoire de sortie par défaut si aucun n'est spécifié
        self.output_dir = Path(output_dir) if output_dir else config.DEFAULT_OUTPUT_DIR
        
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, IOError) as e:
            logging.error("Impossible de créer le répertoire de sortie %s: %s", self.output_dir, str(e))
            raise
            
        # Enregistrer les polices personnalisées si disponibles
        try:
            self._enregistrer_polices()
        except Exception as e:
            logging.warning("Erreur lors de l'enregistrement des polices: %s", str(e))
    
    def _enregistrer_polices(self) -> None:
        """
        Tente d'enregistrer des polices personnalisées pour le PDF.
        
        En cas d'échec, utilise les polices par défaut de ReportLab.
        """
        try:
            pdfmetrics.registerFont(TTFont('Arial', 'arial.ttf'))
            pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
        except (IOError, OSError) as e:
            # Utiliser les polices par défaut si les polices personnalisées ne sont pas disponibles
            logging.warning("Impossible de charger les polices personnalisées: %s", str(e))
    
    def generer_carte_assurance(self, patient_data: Dict[str, Any]) -> str:
        """
        Génère une carte d'assurance médicale au format PDF avec QR code.
        
        La carte générée contient les informations personnelles du patient, sa photo,
        un code QR et les détails de son assurance. Le fichier est enregistré dans le
        répertoire de sortie spécifié lors de l'initialisation.
        
        Args:
            patient_data: Dictionnaire contenant les informations du patient avec les clés :
                - id (str): Identifiant unique du patient
                - nom (str): Nom de famille du patient
                - prenom (str): Prénom du patient
                - date_naissance (str): Date de naissance (format JJ/MM/AAAA)
                - numero_assurance (str): Numéro de sécurité sociale ou d'assurance
                - expiration_assurance (str): Date d'expiration (format JJ/MM/AAAA)
                - photo_path (str, optionnel): Chemin vers la photo du patient
                - qr_code_data (str): Données à encoder dans le QR code
                
        Returns:
            str: Chemin absolu vers le fichier PDF généré
            
        Raises:
            FileNotFoundError: Si le répertoire de sortie n'existe pas
            PermissionError: Si l'écriture est refusée dans le répertoire de sortie
            ValueError: Si les données du patient sont invalides
            Exception: Pour les autres erreurs lors de la génération
        """
        try:
            # Vérifier les données requises
            required_fields = ['id', 'nom', 'prenom', 'date_naissance', 'numero_assurance', 'qr_code_data']
            for field in required_fields:
                if field not in patient_data or not patient_data[field]:
                    raise ValueError(f"Le champ obligatoire '{field}' est manquant ou vide")
            
            # Créer un nom de fichier unique
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"carte_assurance_{patient_data['id']}_{timestamp}.pdf"
            output_path = self.output_dir / filename
            
            # Créer le document PDF en mode paysage A5
            doc = SimpleDocTemplate(
                str(output_path),
                pagesize=landscape(A5),
                leftMargin=config.MARGIN,
                rightMargin=config.MARGIN,
                topMargin=config.MARGIN,
                bottomMargin=config.MARGIN
            )
            
            # Styles pour le document
            styles = self._creer_styles()
            
            # Contenu du document
            elements = self._creer_contenu(patient_data, styles)
            
            # Générer le PDF
            doc.build(elements)
            
            logging.info("Carte d'assurance générée avec succès: %s", output_path)
            return str(output_path)
            
        except (FileNotFoundError, PermissionError, ValueError) as e:
            logging.error("Erreur lors de la génération de la carte d'assurance: %s", str(e))
            raise
        except Exception as e:
            logging.error("Erreur inattendue lors de la génération de la carte d'assurance: %s", str(e), exc_info=True)
            raise
    
    def _creer_styles(self) -> Dict[str, ParagraphStyle]:
        """Crée et retourne les styles pour le document PDF."""
        styles = {}
        
        # Style normal
        styles['normal'] = ParagraphStyle(
            'Normal',
            fontName=config.FONTS['regular'],
            fontSize=config.get_font_size('normal'),
            leading=config.get_font_size('normal') + 2,
            textColor=config.COLORS['text'],
            spaceAfter=6
        )
        
        # Style titre
        styles['title'] = ParagraphStyle(
            'Title',
            parent=styles['normal'],
            fontName=config.FONTS['title'],
            fontSize=config.get_font_size('title'),
            textColor=config.COLORS['primary'],
            spaceAfter=12,
            alignment=1  # Centré
        )
        
        # Style sous-titre
        styles['subtitle'] = ParagraphStyle(
            'Subtitle',
            parent=styles['normal'],
            fontName=config.FONTS['subtitle'],
            fontSize=config.get_font_size('subtitle'),
            textColor=config.COLORS['secondary']
        )
        
        return styles
    
    def _creer_contenu(self, patient_data: Dict[str, Any], styles: Dict[str, ParagraphStyle]) -> list:
        """Crée et retourne la liste des éléments du document PDF."""
        elements = []
        
        # En-tête avec le titre
        elements.append(Paragraph("CARTE D'IDENTITÉ MÉDICALE", styles['title']))
        elements.append(Spacer(1, 10))
        
        # Ligne avec photo, informations personnelles et QR code
        data = [
            [
                self._create_photo_cell(patient_data.get('photo_path')),
                self._create_info_personnelles(patient_data, styles['normal']),
                self._create_qr_code_cell(patient_data.get('qr_code_data'))
            ]
        ]
        
        # Créer un tableau avec les données
        table = Table(data, colWidths=[6*cm, 10*cm, 8*cm])
        table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, config.COLORS['border']),
            ('BOX', (0, 0), (-1, -1), 1, config.COLORS['border']),
            ('BACKGROUND', (0, 0), (-1, 0), config.COLORS['primary']),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("En cas d'urgence, présentez cette carte au personnel médical", 
                                ParagraphStyle('Footer', parent=styles['normal'], fontSize=8, alignment=1)))
        
        return elements
        doc.build(elements)
        
        return str(output_path)
    
    def _create_photo_cell(self, photo_path: Optional[str]) -> Table:
        """
        Crée une cellule avec la photo du patient.
        
        Args:
            photo_path: Chemin vers la photo du patient. Peut être None.
            
        Returns:
            Table: Une cellule de tableau contenant la photo ou un message par défaut.
        """
        try:
            if photo_path and os.path.exists(photo_path):
                # Vérifier que le fichier est bien une image
                if not photo_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    raise ValueError("Le fichier n'est pas une image valide")
                    
                img = Image(
                    photo_path, 
                    width=config.PHOTO_SETTINGS['width'] * cm, 
                    height=config.PHOTO_SETTINGS['height'] * cm
                )
                
                # Ajouter une bordure à l'image
                data = [
                    [img],
                    [Paragraph("<b>Photo d'identité</b>", 
                              ParagraphStyle('PhotoLabel', alignment=1, fontSize=8))]
                ]
            else:
                # Image par défaut si aucune photo n'est disponible
                data = [
                    [Paragraph(
                        "<b>Photo non disponible</b>", 
                        ParagraphStyle('PhotoPlaceholder', alignment=1, fontSize=8, textColor=colors.grey)
                    )]
                ]
            
            return Table(
                data, 
                colWidths=[(config.PHOTO_SETTINGS['width'] + 0.5) * cm],
                style=TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BOX', (0, 0), (-1, -1), 1, config.COLORS['border']),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
                ])
            )
            
        except Exception as e:
            logging.warning("Erreur lors du chargement de la photo: %s", str(e))
            return Table([["Erreur photo"]])
    
    def _create_info_personnelles(self, patient_data: Dict[str, Any], style: ParagraphStyle) -> Table:
        """
        Crée une cellule avec les informations personnelles du patient.
        
        Args:
            patient_data: Dictionnaire contenant les informations du patient.
            style: Style à appliquer aux paragraphes.
            
        Returns:
            Table: Un tableau contenant les informations personnelles formatées.
        """
        try:
            # En-tête de section
            elements = [
                Paragraph(
                    "<b>INFORMATIONS PERSONNELLES</b>", 
                    ParagraphStyle(
                        'InfoHeader', 
                        parent=style,
                        fontName=config.FONTS['bold'],
                        textColor=config.COLORS['primary']
                    )
                ),
                Spacer(1, 8)
            ]
            
            # Informations personnelles
            infos = [
                ("Nom", patient_data.get('nom', 'Non renseigné')),
                ("Prénom", patient_data.get('prenom', 'Non renseigné')),
                ("Date de naissance", patient_data.get('date_naissance', 'Non renseignée')),
                ("Numéro de carte", patient_data.get('id', 'Non renseigné')),
            ]
            
            # Ajouter chaque information avec formatage
            for label, value in infos:
                elements.append(Paragraph(
                    f"<b>{label}:</b> {value}", 
                    style
                ))
            
            # Créer un tableau avec une seule colonne
            data = [[element] for element in elements]
            
            return Table(
                data, 
                colWidths=[12 * cm],
                style=TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ])
            )
            
        except Exception as e:
            logging.error("Erreur lors de la création des informations personnelles: %s", str(e))
            return Table([["Erreur lors du chargement des informations personnelles"]])
    
    def _create_qr_code_cell(self, qr_data: Optional[str]) -> Table:
        """
        Crée une cellule avec un code QR encodant les données fournies.
        
        Args:
            qr_data: Données à encoder dans le QR code.
            
        Returns:
            Table: Une cellule de tableau contenant le QR code ou un message d'erreur.
        """
        if not qr_data:
            return Table([["Pas de données pour le QR code"]])
        
        try:
            # Générer le QR code avec les paramètres de configuration
            qr = qrcode.QRCode(
                version=config.QR_CODE_SETTINGS['version'],
                box_size=config.QR_CODE_SETTINGS['box_size'],
                border=config.QR_CODE_SETTINGS['border'],
                error_correction=qrcode.constants.ERROR_CORRECT_H
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            # Créer l'image du QR code avec les couleurs de configuration
            qr_img = qr.make_image(
                fill_color=config.QR_CODE_SETTINGS['fill_color'],
                back_color=config.QR_CODE_SETTINGS['back_color']
            )
            
            # Sauvegarder le QR code dans un buffer
            buffer = BytesIO()
            qr_img.save(buffer, format='PNG')
            buffer.seek(0)
            
            # Créer une image à partir du buffer
            img = Image(
                buffer, 
                width=config.QR_CODE_SETTINGS['size'] / 2.54 * 72 / 25.4,  # Conversion mm en points
                height=config.QR_CODE_SETTINGS['size'] / 2.54 * 72 / 25.4
            )
            
            data = [
                [img],
                [Paragraph("<b>Scanner pour vérifier</b>", 
                          ParagraphStyle('QRCodeLabel', alignment=1, fontSize=8))]
            ]
            
            return Table(
                data, 
                colWidths=[config.QR_CODE_SETTINGS['size'] / 2.54 * 72 / 25.4],
                style=TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BOX', (0, 0), (-1, -1), 1, config.COLORS['border']),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
                ])
            )
            
        except Exception as e:
            logging.error("Erreur lors de la génération du QR code: %s", str(e), exc_info=True)
            return Table([["Erreur de génération du QR code"]])
    
    def _create_info_assurance(self, patient_data: Dict[str, Any], style: ParagraphStyle) -> Table:
        """
        Crée une cellule avec les informations d'assurance du patient.
        
        Args:
            patient_data: Dictionnaire contenant les informations d'assurance.
            style: Style à appliquer aux paragraphes.
            
        Returns:
            Table: Un tableau contenant les informations d'assurance formatées.
        """
        try:
            # En-tête de section
            elements = [
                Paragraph(
                    "<b>INFORMATIONS D'ASSURANCE</b>", 
                    ParagraphStyle(
                        'AssuranceHeader', 
                        parent=style,
                        fontName=config.FONTS['bold'],
                        textColor=config.COLORS['primary']
                    )
                ),
                Spacer(1, 8)
            ]
            
            # Informations d'assurance
            infos = [
                ("Numéro d'assuré", patient_data.get('numero_assurance', 'Non renseigné')),
                ("Date d'expiration", patient_data.get('expiration_assurance', 'Non renseignée')),
                ("Type de couverture", patient_data.get('type_couverture', 'Complète')),
                ("Médecin traitant", patient_data.get('medecin_traitant', 'Non renseigné')),
            ]
            
            # Ajouter chaque information avec formatage
            for label, value in infos:
                elements.append(Paragraph(
                    f"<b>{label}:</b> {value}", 
                    style
                ))
            
            # Ajouter un espace et des informations supplémentaires
            elements.extend([
                Spacer(1, 12),
                Paragraph(
                    "En cas d'urgence, présenter cette carte à tout professionnel de santé.",
                    ParagraphStyle('Note', parent=style, fontSize=8, textColor=colors.grey)
                ),
                Paragraph(
                    "Cette carte est strictement personnelle et doit être conservée en lieu sûr.",
                    ParagraphStyle('Note', parent=style, fontSize=8, textColor=colors.grey)
                )
            ])
            
            # Créer un tableau avec une seule colonne
            data = [[element] for element in elements]
            
            return Table(
                data, 
                colWidths=[12 * cm],
                style=TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ])
            )
            
        except Exception as e:
            logging.error("Erreur lors de la création des informations d'assurance: %s", str(e))
            return Table([["Erreur lors du chargement des informations d'assurance"]])

def main() -> int:
    """
    Fonction principale pour tester la génération de la carte d'assurance.
    
    Cette fonction est utilisée uniquement pour les tests locaux et démontre comment utiliser
    la classe CarteAssuranceGenerator pour générer une carte d'assurance pour un patient.
    
    Returns:
        int: Code de sortie (0 pour succès, 1 pour erreur)
        
    Example:
        >>> if __name__ == "__main__":
        ...     import sys
        ...     sys.exit(main())
    """
    # Exemple de données patient
    patient_data = {
        'id': 'PAT123456',
        'nom': 'DUPONT',
        'prenom': 'Jean',
        'date_naissance': '15/05/1985',
        'numero_assurance': '800123456789',
        'expiration_assurance': '31/12/2025',
        'photo_path': 'chemin/vers/photo.jpg',  # Remplacer par un chemin valide
        'qr_code_data': 'https://exemple.com/patient/PAT123456'
    }
    
    logging.info("Début de la génération de la carte d'assurance...")
    
    try:
        # Créer une instance du générateur avec le répertoire de sortie par défaut
        generator = CarteAssuranceGenerator()
        
        # Générer la carte d'assurance
        pdf_path = generator.generer_carte_assurance(patient_data)
        
        logging.info("Carte d'assurance générée avec succès: %s", pdf_path)
        return 0
        
    except FileNotFoundError as e:
        logging.error("Erreur: Répertoire de sortie introuvable - %s", str(e))
    except PermissionError as e:
        logging.error("Erreur de permission lors de l'écriture du fichier - %s", str(e))
    except Exception as e:
        logging.error("Erreur inattendue lors de la génération de la carte d'assurance: %s", str(e), exc_info=True)
    
    return 1

# Point d'entrée principal pour l'exécution en tant que script
if __name__ == "__main__":
    # Configurer le système de journalisation
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('generation_carte.log')
        ]
    )
    
    # Exécuter la fonction principale et quitter avec le code de retour approprié
    raise SystemExit(main())
