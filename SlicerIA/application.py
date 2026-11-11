"""Interface locale de préparation et de diagnostic d'impression 3D."""

import json

import streamlit as st
import streamlit.components.v1 as composants
import requests

import analyseur_fichier
import configuration
import moteur_ia


st.set_page_config(layout="wide", page_title="SlicerIA")
st.title("SlicerIA")
st.caption("Votre atelier d'impression 3D : réglages, coûts et diagnostic.")

with st.sidebar:
    st.header("Configuration de l'atelier")
    cle_api = st.text_input("Clé API Google AI Studio", type="password").strip()
    modele_gemini = st.text_input("Modèle Gemini", value="gemini-3.6-flash").strip()
    marque = st.selectbox("Marque de l'imprimante", list(configuration.MACHINES))
    modele = st.selectbox("Modèle de l'imprimante", list(configuration.MACHINES[marque]), key=f"modele_{marque}")
    puissance_reference = configuration.MACHINES[marque][modele]
    st.caption(f"Puissance indicative du catalogue : {puissance_reference} W")
    puissance = st.number_input("Puissance moyenne estimée ou mesurée (W)", min_value=0.0, value=float(puissance_reference), step=10.0, key=f"puissance_{marque}_{modele}")
    tarif = st.number_input("Tarif de l'électricité (€/kWh)", min_value=0.0, value=0.25, step=0.01, format="%.3f")
    st.caption("Les puissances du catalogue sont indicatives, pas des mesures de consommation moyenne. Utilisez un wattmètre pour une estimation fiable.")
    if not cle_api:
        st.warning("Ajoutez une clé Google AI Studio pour utiliser les fonctions Gemini. Le dialogue local reste disponible.")
    st.caption("Les données envoyées à Gemini, notamment les images et les configurations, quittent votre ordinateur. Vérifiez-les avant envoi.")

machine = f"{marque} {modele}"
moteur = moteur_ia.MoteurGemini(cle_api, modele_gemini)
profil, diagnostic, communaute, discussion = st.tabs([
    "Générateur de profil & Éco-Mode",
    "Diagnostic des échecs d'impression",
    "Alerte & Avis communautaires",
    "Slicer en langage naturel",
])

with profil:
    st.subheader("Préparer un profil de tranchage")
    gauche, droite = st.columns(2)
    with gauche:
        materiau = st.selectbox("Matériau", ["PLA", "PETG", "ABS", "ASA", "TPU", "Nylon", "Autre"])
        usage = st.text_input("Cas d'usage", value="Pièce fonctionnelle")
        robustesse = st.slider("Robustesse souhaitée", 1, 5, 3)
        finition = st.slider("Qualité de finition souhaitée", 1, 5, 3)
    with droite:
        poids = st.number_input("Poids estimé de la pièce (g)", min_value=0.0, value=100.0, step=1.0)
        heures = st.number_input("Durée : heures", min_value=0, value=3, step=1)
        minutes = st.number_input("Durée : minutes", min_value=0, max_value=59, value=0, step=1)
        prix_bobine = st.number_input("Prix de la bobine de 1 kg (€)", min_value=0.0, value=25.0, step=1.0)
    fichier = st.file_uploader("Configuration facultative à analyser localement", type=["3mf", "json", "config"])
    donnees_configuration = ""
    if fichier is not None:
        donnees_configuration = analyseur_fichier.extraire_configuration_3mf(fichier)
        try:
            donnees_lues = json.loads(donnees_configuration)
        except ValueError:
            donnees_lues = {"erreur": "La configuration extraite est illisible."}
        if "erreur" in donnees_lues:
            st.error(donnees_lues["erreur"])
            donnees_configuration = ""
        elif not donnees_lues:
            st.warning("Aucun paramètre de tranchage n'a été trouvé dans ce fichier.")
            donnees_configuration = ""
        else:
            with st.expander("Paramètres extraits localement"):
                st.json(donnees_lues)
    cout_matiere = configuration.calculer_cout_matiere(poids, prix_bobine)
    cout_energie = configuration.calculer_cout_energie(heures, minutes, puissance, tarif)
    colonnes = st.columns(3)
    colonnes[0].metric("Coût matière", f"{cout_matiere:.2f} €")
    colonnes[1].metric("Coût électrique estimé", f"{cout_energie:.2f} €")
    colonnes[2].metric("Total estimé", f"{cout_matiere + cout_energie:.2f} €")
    st.caption("Estimation hors amortissement, entretien et déchets ; consommation calculée à puissance constante.")
    if st.button("Générer le profil et l'Éco-Mode", type="primary"):
        st.session_state.pop("resultat_profil", None)
        st.session_state.pop("suggestions_profil", None)
        if not cle_api:
            st.warning("Une clé Google AI Studio est nécessaire pour générer le profil.")
        elif not modele_gemini:
            st.warning("Renseignez le modèle Gemini.")
        else:
            with st.spinner("Recherche et préparation du profil en cours…"):
                try:
                    st.session_state["resultat_profil"] = moteur.generer_profil_et_eco(
                        machine, materiau, usage, robustesse, finition, poids, heures, minutes,
                        prix_bobine, cout_matiere, cout_energie, donnees_configuration,
                    )
                    st.session_state["suggestions_profil"] = moteur.suggestions_recherche
                except moteur_ia.ErreurGemini as erreur:
                    st.error(str(erreur))
    if st.session_state.get("resultat_profil"):
        st.markdown(st.session_state["resultat_profil"])
        if st.session_state.get("suggestions_profil"):
            composants.html(st.session_state["suggestions_profil"], height=160, scrolling=True)

with diagnostic:
    st.subheader("Analyser un échec d'impression")
    image = st.file_uploader("Photographie de l'impression", type=["png", "jpg", "jpeg"])
    severite = st.slider("Sévérité de l'échec", 1, 5, 3)
    symptomes = st.multiselect("Symptômes observés", [
        "Décollement du plateau", "Fils entre les pièces", "Sous-extrusion", "Sur-extrusion",
        "Décalage de couches", "Bouchage de la buse", "Déformation des angles",
        "Couches irrégulières", "Mauvais ponts ou surplombs", "Pièce détachée ou spaghetti",
    ])
    if st.button("Analyser l'échec"):
        st.session_state.pop("resultat_diagnostic", None)
        if not cle_api:
            st.warning("Une clé Google AI Studio est nécessaire pour analyser l'image.")
        elif image is None:
            st.warning("Ajoutez une photographie avant de lancer l'analyse.")
        elif image.size > 15 * 1024 * 1024:
            st.warning("L'image ne doit pas dépasser 15 Mo.")
        else:
            with st.spinner("Analyse de la photographie en cours…"):
                try:
                    st.session_state["resultat_diagnostic"] = moteur.analyser_echec_impression(image.getvalue(), severite, symptomes)
                except moteur_ia.ErreurGemini as erreur:
                    st.error(str(erreur))
    if st.session_state.get("resultat_diagnostic"):
        st.markdown(st.session_state["resultat_diagnostic"])

with communaute:
    st.subheader("Consulter les avis de la communauté")
    cible = st.text_input("Nom du modèle ou adresse de sa page")
    st.caption("Les avis sont des témoignages, pas une garantie de sécurité ou de qualité.")
    if st.button("Vérifier les avis"):
        st.session_state.pop("resultat_communaute", None)
        st.session_state.pop("suggestions_communaute", None)
        if not cle_api:
            st.warning("Une clé Google AI Studio est nécessaire pour effectuer la recherche.")
        elif not cible.strip():
            st.warning("Indiquez un nom ou une adresse.")
        else:
            with st.spinner("Recherche des avis en cours…"):
                try:
                    st.session_state["resultat_communaute"] = moteur.verifier_avis_communaute(cible.strip())
                    st.session_state["suggestions_communaute"] = moteur.suggestions_recherche
                except moteur_ia.ErreurGemini as erreur:
                    st.error(str(erreur))
    if st.session_state.get("resultat_communaute"):
        st.markdown(st.session_state["resultat_communaute"])
        if st.session_state.get("suggestions_communaute"):
            composants.html(st.session_state["suggestions_communaute"], height=160, scrolling=True)

with discussion:
    st.subheader("Discuter avec l'expert de l'atelier")
    service = st.radio("Moteur de discussion", ["Ollama local", "Gemini en ligne"], horizontal=True)
    st.caption("Le dialogue local utilise Qwen 2.5 Coder 14B via Ollama. Avec Gemini, l'historique est envoyé à Google.")
    if "messages_atelier" not in st.session_state:
        st.session_state.messages_atelier = []
    if st.button("Effacer la discussion"):
        st.session_state.messages_atelier = []
    for message in st.session_state.messages_atelier:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    question = st.chat_input("Posez une question sur votre impression 3D")
    if question:
        historique = st.session_state.messages_atelier
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            try:
                with st.spinner("Préparation de la réponse…"):
                    if service == "Gemini en ligne":
                        reponse = moteur.chat_expert(question, historique)
                    else:
                        messages = [{"role": "system", "content": "Tu es un expert de l'impression 3D FDM. Réponds en français et signale les risques et incertitudes."}]
                        messages += historique + [{"role": "user", "content": question}]
                        resultat = requests.post(
                            "http://127.0.0.1:11434/api/chat",
                            json={"model": "qwen2.5-coder:14b", "messages": messages, "stream": False},
                            timeout=(5, 180),
                        )
                        resultat.raise_for_status()
                        reponse = resultat.json()["message"]["content"]
                        if not isinstance(reponse, str) or not reponse.strip():
                            raise ValueError("Réponse vide.")
                st.markdown(reponse)
                historique.extend([{"role": "user", "content": question}, {"role": "assistant", "content": reponse}])
            except moteur_ia.ErreurGemini as erreur:
                st.error(str(erreur))
            except (requests.RequestException, ValueError, KeyError, TypeError):
                st.error("Impossible d'obtenir une réponse d'Ollama. Vérifiez que le service local fonctionne et que le modèle qwen2.5-coder:14b est installé.")
