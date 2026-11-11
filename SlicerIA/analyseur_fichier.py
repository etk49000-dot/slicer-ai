"""Extraction locale et prudente des configurations de tranchage."""

import zipfile
import json
import xml.etree.ElementTree as ET
import io
import re


TAILLE_MAXIMALE = 5 * 1024 * 1024
NOMBRE_MAXIMAL_FICHIERS = 2000
EXPRESSION_URL = re.compile(r"(?:https?://|www\.)[^\s\"'<>]+", re.IGNORECASE)


def _lire_octets(fichier_charge):
    """Lit un fichier en mémoire sans dépendre de sa position courante."""
    if isinstance(fichier_charge, (bytes, bytearray)):
        return bytes(fichier_charge)
    if hasattr(fichier_charge, "getvalue"):
        return fichier_charge.getvalue()
    fichier_charge.seek(0)
    return fichier_charge.read()


def _nettoyer(valeur):
    if isinstance(valeur, str):
        return EXPRESSION_URL.sub("", valeur).strip()
    if isinstance(valeur, dict):
        return {str(cle): _nettoyer(element) for cle, element in valeur.items()}
    if isinstance(valeur, list):
        return [_nettoyer(element) for element in valeur]
    return valeur


def _extraire_contenu(contenu, nom, parametres):
    """Accepte les configurations JSON, XML et les lignes clé = valeur."""
    texte = contenu.decode("utf-8-sig", errors="replace")
    try:
        donnees = json.loads(texte)
    except (ValueError, TypeError):
        donnees = None
    if isinstance(donnees, dict):
        for cle, valeur in donnees.items():
            parametres.setdefault(str(cle), valeur)
        return
    if isinstance(donnees, list):
        parametres.setdefault(nom, donnees)
        return
    try:
        racine = ET.fromstring(texte)
    except ET.ParseError:
        racine = None
    if racine is not None:
        for element in racine.iter():
            cle = element.get("key") or element.get("name")
            valeur = element.get("value")
            if cle and valeur is not None:
                parametres.setdefault(cle, valeur)
            elif len(element) == 0 and element.text and element.text.strip():
                parametres.setdefault(element.tag.split("}")[-1], element.text.strip())
        return
    for ligne in texte.splitlines():
        ligne = ligne.strip().lstrip(";# ")
        if not ligne or "=" not in ligne:
            continue
        cle, valeur = ligne.split("=", 1)
        if cle.strip():
            parametres.setdefault(cle.strip(), valeur.strip())


def extraire_configuration_3mf(fichier_charge):
    """Renvoie au plus cent paramètres extraits d'un projet ou d'une configuration."""
    try:
        octets = _lire_octets(fichier_charge)
        nom = getattr(fichier_charge, "name", "projet.3mf").lower()
        parametres = {}
        if nom.endswith((".json", ".config")):
            if len(octets) > TAILLE_MAXIMALE:
                raise ValueError("Le fichier de configuration dépasse 5 Mo.")
            _extraire_contenu(octets, nom, parametres)
        else:
            with zipfile.ZipFile(io.BytesIO(octets)) as archive:
                fichiers = archive.infolist()
                if len(fichiers) > NOMBRE_MAXIMAL_FICHIERS:
                    raise ValueError("L'archive contient trop de fichiers.")
                taille_totale = 0
                for entree in fichiers:
                    if entree.is_dir() or not entree.filename.lower().endswith((".config", ".json")):
                        continue
                    taille_totale += entree.file_size
                    if entree.file_size > TAILLE_MAXIMALE or taille_totale > TAILLE_MAXIMALE:
                        raise ValueError("Les configurations de l'archive dépassent 5 Mo.")
                    _extraire_contenu(archive.read(entree), entree.filename, parametres)
                    if len(parametres) >= 100:
                        break
        return json.dumps(_nettoyer(dict(list(parametres.items())[:100])), ensure_ascii=False, indent=2)
    except (OSError, ValueError, TypeError, AttributeError, zipfile.BadZipFile, RuntimeError, EOFError) as erreur:
        return json.dumps({"erreur": f"Impossible de lire la configuration : {erreur}"}, ensure_ascii=False)


def analyser_metadonnees_gcode(fichier_charge):
    """Extrait les trente premiers commentaires du fichier de commandes."""
    try:
        octets = _lire_octets(fichier_charge)
        texte = octets.decode("utf-8-sig", errors="replace") if isinstance(octets, bytes) else str(octets)
        commentaires = []
        for ligne in texte.splitlines():
            if ligne.lstrip().startswith(";"):
                commentaires.append(EXPRESSION_URL.sub("", ligne.strip()))
                if len(commentaires) == 30:
                    break
        return "\n".join(commentaires) or "Aucun commentaire trouvé."
    except (OSError, ValueError, TypeError, AttributeError) as erreur:
        return f"Impossible de lire les métadonnées : {erreur}"
