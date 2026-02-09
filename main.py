import json
import random
from re import PatternError


# --- 1. CHARGEMENT DES DONNÉES ---
def load_data():
    with open("users.json", "r") as f:
        users = json.load(f)
    with open("articles.json", "r") as f:
        articles = json.load(f)
    return users, articles


# --- 2. LE CERVEAU (Fonction de Scoring) ---
def calculate_score(user, article):
    score = 0

    # A. Score d'Affinité (Tags)
    # On additionne les poids que l'utilisateur a pour les tags de l'article
    for tag in article["tags"]:
        # .get(tag, 0) évite le crash si un nouveau tag apparaît un jour
        score += user["weights"].get(tag, 0)

    # B. Score de Niveau (Progression)
    # On prend le premier tag de l'article pour vérifier le niveau du user
    main_tag = article["tags"][0]
    user_lvl = user["mastery"].get(main_tag, 1)
    art_lvl = article["level"]

    diff = art_lvl - user_lvl

    if diff == 0:
        score += 2.0  # Parfait match de niveau (Bonus)
    elif diff == 1:
        score += 0.5  # Un peu dur (Challenge acceptable)
    elif diff > 1:
        score -= 3.0  # Trop dur (Pénalité forte)
    elif diff < 0:
        score -= 1.0  # Trop facile (Petite pénalité)

    # protection to not go negative
    if score < 0:
        score = 0.1

    # C. Jitter (Aléatoire pour la découverte)
    # Ajoute un petit flou pour que les listes ne soient pas figées
    score += random.uniform(0, 0.2)

    return round(score, 2)


# --- 3. GÉNÉRATEUR DE LISTE ---
def get_recommendations(user_id, all_users, all_articles, top_n=10):
    # 1. Trouver le bon utilisateur
    target_user = next((u for u in all_users if u["user_id"] == user_id), None)
    if not target_user:
        print("❌ Erreur: Utilisateur introuvable.")
        return [], None  # Attention: je renvoie une liste vide ET None pour user_obj

    print(f"\n🔍 --- DEBUG ALGO pour {target_user['name']} ---")

    # --- LISTES TEMPORAIRES ---
    pertinence_list = []
    discovery_list = []
    collab_list = []

    # ==========================================
    # 1. PERTINENCE (CONTENT-BASED) -> Objectif ~70%
    # ==========================================
    for article in all_articles:
        if article["article_id"] in target_user["history"]:
            continue

        score = calculate_score(target_user, article)
        pertinence_list.append(
            {
                "id": article["article_id"],
                "title": article["title"],
                "tags": article["tags"],
                "level": article["level"],
                "score": score,
                "type": "pertinence",
            }
        )

    # On trie et on prend les meilleurs
    pertinence_list.sort(key=lambda x: x["score"], reverse=True)
    nb_pertinent = int(0.7 * top_n)  # 7 articles sur 10
    final_pertinent = pertinence_list[:nb_pertinent]
    print(
        f"✅ Pertinence : {len(final_pertinent)} articles sélectionnés (Top score: {final_pertinent[0]['score'] if final_pertinent else 0})"
    )

    # ==========================================
    # 2. COLLABORATION (USER-BASED) -> Objectif ~15%
    # ==========================================
    jumeau, dist, new_items_ids = finding_useful_jumeau(
        target_user, all_users, min_history_len=1
    )

    nb_collab = int(0.15 * top_n)  # ~1 ou 2 articles
    collab_list = []

    if jumeau:
        print(f"👯 Jumeau UTILE trouvé : {jumeau['name']} (Dist: {round(dist, 2)})")
        print(f"   -> Il a {len(new_items_ids)} articles nouveaux pour nous.")

        # On transforme les IDs en objets articles complets
        for art_id in new_items_ids:
            # On vérifie que ce n'est pas déjà dans la liste de pertinence
            if any(p["id"] == art_id for p in final_pertinent):
                continue

            article_obj = next(
                (a for a in all_articles if a["article_id"] == art_id), None
            )

            if article_obj:
                collab_list.append(
                    {
                        "id": article_obj["article_id"],
                        "title": article_obj["title"],
                        "tags": article_obj["tags"],
                        "level": article_obj["level"],
                        "score": 5.0,  # Score Max
                        "type": f"🤝 Lu par {jumeau['name']}",
                    }
                )

        # On coupe si on en a trop
        collab_list = collab_list[:nb_collab]
        print(f"✅ Collaboration : {len(collab_list)} articles ajoutés.")

    else:
        print("⚠️ Collaboration : Aucun voisin n'a d'historique pertinent à partager.")

    # ==========================================
    # 3. DÉCOUVERTE (ALEATOIRE CONTROLÉ) -> Objectif ~15% + Reste
    # ==========================================
    # On calcule combien de places il reste pour atteindre top_n
    slots_filled = len(final_pertinent) + len(collab_list)
    slots_needed = top_n - slots_filled

    if slots_needed > 0:
        # On cherche des articles non lus, non sélectionnés, avec des tags faibles
        low_interest_tags = [t for t, w in target_user["weights"].items() if w < 1.5]
        if not low_interest_tags:
            low_interest_tags = list(target_user["weights"].keys())  # Fallback

        excluded_ids = (
            set(target_user["history"])
            | {a["id"] for a in final_pertinent}
            | {a["id"] for a in collab_list}
        )

        candidates = [
            a
            for a in all_articles
            if a["article_id"] not in excluded_ids
            and any(t in low_interest_tags for t in a["tags"])
        ]

        if candidates:
            # On pioche au hasard
            picked = random.sample(candidates, min(slots_needed, len(candidates)))
            for a in picked:
                discovery_list.append(
                    {
                        "id": a["article_id"],
                        "title": a["title"],
                        "tags": a["tags"],
                        "level": a["level"],
                        "score": calculate_score(
                            target_user, a
                        ),  # Score nul mais c'est pas grave
                        "type": "🌟 DÉCOUVERTE",
                    }
                )
            print(f"✅ Découverte : {len(discovery_list)} articles injectés.")
        else:
            print("⚠️ Découverte : Pas assez d'articles candidats.")

    # ==========================================
    # 4. ASSEMBLAGE FINAL
    # ==========================================
    # L'ordre compte ! D'abord les amis, puis la pertinence, puis la découverte en bas
    final_list = collab_list + final_pertinent + discovery_list

    # Sécurité : Si on n'a pas atteint top_n (cas rare), on comble avec du pertinent
    if len(final_list) < top_n:
        print("🔧 Comblage : On ajoute plus d'articles pertinents pour finir la liste.")
        used_ids = {a["id"] for a in final_list}
        rest = [a for a in pertinence_list if a["id"] not in used_ids]
        final_list.extend(rest[: top_n - len(final_list)])

    print("-----------------------------------")
    return target_user, final_list


def simulate_interaction(user_id, article_id, interaction_type):

    # Chargement
    with open("users.json", "r") as f:
        users = json.load(f)

    # On charge les articles juste pour récupérer les tags
    with open("articles.json", "r") as f:
        articles = json.load(f)

    # Recherche de l'article cible
    target_article = next((a for a in articles if a["article_id"] == article_id), None)
    if not target_article:
        print(f"❌ Erreur : Article {article_id} introuvable.")
        return

    # Définition des points selon l'action
    addedPoints = 0.0
    if interaction_type == "read":
        addedPoints = 0.2
        # Recherche et modification de l'utilisateur
        for user in users:
            if user["user_id"] == user_id:
                print(
                    f"\n[ACTION] {user['name']} effectue : {interaction_type.upper()} sur {article_id}"
                )

                # 1. Mise à jour des poids (Weights)
                for tag in target_article["tags"]:
                    old_weight = user["weights"].get(tag, 0)
                    new_weight = round(old_weight + addedPoints, 2)
                    user["weights"][tag] = new_weight
                    print(f"   -> Poids '{tag}': {old_weight} 📈 {new_weight}")

                # 2. Mise à jour de l'historique (SANS DUPLICATION)
                if article_id not in user["history"]:
                    user["history"].append(article_id)
                    print("   -> Ajouté à l'historique de lecture.")
                else:
                    print("   -> Déjà dans l'historique (pas de doublon).")

                # 3. Sauvegarde immédiate
                with open("users.json", "w") as f:
                    json.dump(users, f, indent=4)
                break
    elif interaction_type == "like":
        addedPoints = 0.3  # Le like vaut plus que la lecture simple
        for user in users:
            if user["user_id"] == user_id:
                print(
                    f"\n[ACTION] {user['name']} effectue : {interaction_type.upper()} sur {article_id}"
                )

                # 1. Mise à jour des poids (Weights)
                for tag in target_article["tags"]:
                    old_weight = user["weights"].get(tag, 0)
                    new_weight = round(old_weight + addedPoints, 2)
                    user["weights"][tag] = new_weight
                    print(f"   -> Poids '{tag}': {old_weight} 📈 {new_weight}")

                # 2. Sauvegarde immédiate
                with open("users.json", "w") as f:
                    json.dump(users, f, indent=4)
                break
    elif interaction_type == "quiz":
        addedPoints = 0.5
        for user in users:
            if user["user_id"] == user_id:
                print(
                    f"\n[ACTION] {user['name']} effectue : {interaction_type.upper()} sur {article_id}"
                )

                # 1. Mise à jour des poids (Weights)
                for tag in target_article["tags"]:
                    old_weight = user["weights"].get(tag, 0)
                    new_weight = round(old_weight + addedPoints, 2)
                    user["weights"][tag] = new_weight
                    print(f"   -> Poids '{tag}': {old_weight} 📈 {new_weight}")

                # 2. Sauvegarde immédiate
                with open("users.json", "w") as f:
                    json.dump(users, f, indent=4)
                break


# ajouter une degradation des poids
def apply_time_decay():
    DECAY_FACTOR = 0.95  # On perd 5% d'intérêt par "cycle" (semaine/jour)

    with open("users.json", "r") as f:
        users = json.load(f)

    print("\n⏳ Passage du temps (Decay)...")
    for user in users:
        print(f"   User {user['user_id']} : ", end="")
        for tag, weight in user["weights"].items():
            # On ne descend pas en dessous de 0.1 pour garder une trace
            new_weight = max(0.1, round(weight * DECAY_FACTOR, 2))
            user["weights"][tag] = new_weight
        print("Poids mis à jour.")

    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)
    print("✅ Temps écoulé : Tous les intérêts ont légèrement baissé.")


# ajout de filtrage collaboratifs pour calculer la disntace entre les users


def euclidian_distance(user1, user2):
    distance = 0
    # On récupère tous les tags uniques des deux dictionnaires pour ne rien oublier
    all_tags = set(user1["weights"].keys()) | set(user2["weights"].keys())

    for tag in all_tags:
        # .get(tag, 0) permet de dire : "Si ce user n'a pas ce tag, considère que c'est 0"
        val1 = user1["weights"].get(tag, 0)
        val2 = user2["weights"].get(tag, 0)

        distance += (val1 - val2) ** 2

    return distance**0.5


def finding_jumeau(target_user, all_users):
    best_jumeau = None
    min_dist = float("inf")  # Infini

    for other_user in all_users:
        # 1. On ne se compare pas à soi-même
        if other_user["user_id"] == target_user["user_id"]:
            continue

        # 2. On calcule la distance
        dist = euclidian_distance(target_user, other_user)

        # 3. On garde le meilleur
        if dist < min_dist:
            min_dist = dist
            best_jumeau = other_user

    return best_jumeau


def finding_useful_jumeau(target_user, all_users, min_history_len=1):
    """
    Trouve l'utilisateur le plus proche qui a lu au moins 'min_history_len' articles
    que le target_user n'a PAS encore lus.
    """
    candidates = []

    # 1. On calcule la distance avec TOUS les autres utilisateurs
    for other_user in all_users:
        if other_user["user_id"] == target_user["user_id"]:
            continue

        dist = euclidian_distance(target_user, other_user)
        candidates.append((dist, other_user))

    # 2. On trie par distance croissante (du plus proche au plus éloigné)
    # C'est ça l'astuce : on a une liste ordonnée de "jumeaux potentiels"
    candidates.sort(key=lambda x: x[0])

    # 3. On parcourt la liste pour trouver le premier "Utile"
    my_history = set(target_user["history"])

    for dist, candidate in candidates:
        # A-t-il un historique ?
        if not candidate["history"]:
            continue

        candidate_history = set(candidate["history"])

        # A-t-il lu des trucs que JE n'ai pas lus ?
        # (C'est inutile de prendre un jumeau qui a lu exactement les mêmes livres que moi)
        new_items = candidate_history - my_history

        if len(new_items) >= min_history_len:
            # BINGO ! C'est lui le meilleur jumeau utile
            return candidate, dist, new_items

    # Si personne n'a rien d'intéressant à proposer
    return None, 0, []


def collaborative_filtering(target_user, jumeau, all_articles):
    reco_collab = []

    if not jumeau or not jumeau.get("history"):
        return []

    # Les IDs que le jumeau a lus
    jumeau_history_ids = set(jumeau["history"])
    # Les IDs que j'ai lus
    my_history_ids = set(target_user["history"])

    # La différence : Ce qu'il a lu ET que je n'ai PAS lu
    ids_to_recommend = jumeau_history_ids - my_history_ids

    for art_id in ids_to_recommend:
        # On doit retrouver l'objet article complet dans la liste all_articles
        # (C'est un peu lourd mais nécessaire avec des fichiers JSON)
        article_obj = next((a for a in all_articles if a["article_id"] == art_id), None)

        if article_obj:
            # On formate l'article pour qu'il ressemble aux autres recommandations
            reco_collab.append(
                {
                    "id": article_obj["article_id"],
                    "title": article_obj["title"],
                    "tags": article_obj["tags"],
                    "level": article_obj["level"],
                    "score": calculate_score(target_user, article_obj),
                    "type": f"🤝 Lu par {jumeau['name']}",  # Petit bonus visuel
                }
            )

    return reco_collab


# --- FONCTION UTILITAIRE POUR L'AFFICHAGE ---
def print_separator(title):
    print(f"\n{'=' * 60}")
    print(f" 📊 {title.upper()}")
    print(f"{'=' * 60}")


def print_top_interests(weights, top_n=5):
    # Trie les poids du plus grand au plus petit
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:top_n]
    print("🧠 TOP INTÉRÊTS : ", end="")
    items = [f"{k}: {v}" for k, v in sorted_weights]
    print(" | ".join(items))


def print_reco_table(recos):
    print(f"\n   {'SCORE':<8} | {'NIV':<4} | {'TITRE':<25} | {'TAGS'}")
    print(f"   {'-' * 60}")
    for i, r in enumerate(recos):
        tags_str = ", ".join(r["tags"])
        # Tronque le titre s'il est trop long pour l'affichage
        title = (r["title"][:22] + "..") if len(r["title"]) > 22 else r["title"]
        print(f"{i + 1}. {r['score']:<8} | {r['level']:<4} | {title:<25} | {tags_str}")


def create_new_user_wizard():
    print("\n" + "=" * 40)
    print("👋 BIENVENUE ! CRÉATION DE PROFIL")
    print("=" * 40)

    # 1. On récupère tous les tags possibles depuis le fichier articles
    with open("articles.json", "r") as f:
        articles = json.load(f)

    # On utilise un set() pour avoir une liste unique de tags
    all_tags = set()
    for art in articles:
        for t in art["tags"]:
            all_tags.add(t)
    sorted_tags = sorted(list(all_tags))

    # 2. Saisie du nom
    user_name = input("👉 Comment t'appelles-tu ? : ")
    new_id = f"user_{random.randint(1000, 9999)}"  # ID aléatoire simple

    # 3. Initialisation du profil vide
    # Par défaut, tout le monde est curieux (0.5) et débutant (1)
    new_user = {
        "user_id": new_id,
        "name": user_name,
        "weights": {tag: 0.5 for tag in sorted_tags},
        "mastery": {tag: 1 for tag in sorted_tags},
        "history": [],
    }

    print("\n🎯 PARLONS DE TES GOÛTS...")
    print("Voici les sujets disponibles :")
    for i, tag in enumerate(sorted_tags):
        print(f"   {i + 1}. {tag}")

    # 4. Sélection des intérêts
    print(
        "\nQuels sujets t'intéressent ? (Entre les numéros séparés par une virgule, ex: 1,4,8)"
    )
    choices = input("👉 Ton choix : ")

    try:
        indices = [int(x.strip()) - 1 for x in choices.split(",")]

        for idx in indices:
            if 0 <= idx < len(sorted_tags):
                selected_tag = sorted_tags[idx]

                # A. On booste le poids
                new_user["weights"][selected_tag] = 2.5

                # B. On demande le niveau pour ce tag précis
                print(f"\n📚 Quel est ton niveau en '{selected_tag}' ?")
                print("   1. Débutant (Je découvre)")
                print("   2. Intermédiaire (J'ai des bases)")
                # Pas de niveau 3 proposé, il faut le mériter !

                lvl = input("👉 Niveau (1-2) [Défaut: 1] : ")
                if lvl == "2":
                    new_user["mastery"][selected_tag] = 2
                else:
                    new_user["mastery"][selected_tag] = 1

    except ValueError:
        print("⚠️  Erreur de saisie. On garde les valeurs par défaut.")

    # 5. Sauvegarde
    with open("users.json", "r") as f:
        users = json.load(f)

    users.append(new_user)

    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

    print(f"\n✅ Compte créé avec succès ! Ton ID est : {new_id}")
    return new_id


def onboard_user_hybrid():
    print("\n" + "🚀" * 40)
    print("   BIENVENUE ! CRÉATION DE TON PROFIL")

    # --- ÉTAPE 1 : CHARGEMENT DES DONNÉES ---
    with open("articles.json", "r") as f:
        articles = json.load(f)

    # Récupérer la liste unique des tags
    all_tags = set()
    for art in articles:
        for t in art["tags"]:
            all_tags.add(t)
    sorted_tags = sorted(list(all_tags))

    # --- ÉTAPE 2 : CRÉATION DE BASE ---
    user_name = input("\n👉 Comment t'appelles-tu ? : ")
    new_id = f"user_{random.randint(10000, 99999)}"

    # Initialisation : Tout le monde commence à 0.5 (Curiosité neutre)
    # Et niveau 1 (Débutant)
    new_user = {
        "user_id": new_id,
        "name": user_name,
        "weights": {tag: 0.5 for tag in sorted_tags},
        "mastery": {tag: 1 for tag in sorted_tags},
        "history": [],
    }

    # --- ÉTAPE 3 : SÉLECTION DÉCLARATIVE (MACRO) ---
    print("\nQuels sont tes domaines de prédilection ?")
    for i, tag in enumerate(sorted_tags):
        print(f"   {i + 1}. {tag}")

    print("\n(Entre les numéros séparés par une virgule, ex: 1, 3)")
    choices = input("👉 Tes choix : ")

    chosen_tags = []
    try:
        indices = [int(x.strip()) - 1 for x in choices.split(",")]
        for idx in indices:
            if 0 <= idx < len(sorted_tags):
                tag = sorted_tags[idx]
                chosen_tags.append(tag)
                # BOOST INITIAL : On met un poids fort
                new_user["weights"][tag] = 2.0
                print(f"   ✅ {tag} ajouté aux favoris.")
    except ValueError:
        print("⚠️  Entrée invalide. On continue avec les valeurs par défaut.")

    # --- ÉTAPE 4 : CALIBRATION FINE (MICRO) ---
    # On propose de calibrer si l'utilisateur a choisi au moins un tag
    if chosen_tags:
        print("\n" + "-" * 40)
        print("🎯 Veux-tu affiner ton profil avec 3 exemples rapides ?")
        confirm = input("👉 (o/n) : ").lower()

        if confirm == "o":
            print("\n🔍 Analyse de tes goûts...")

            # STRATÉGIE DE SÉLECTION D'ARTICLES :
            # On prend 2 articles liés à ses choix (pour vérifier la profondeur)
            # Et 1 article aléatoire (pour vérifier l'ouverture d'esprit)

            candidates = [
                a for a in articles if any(t in chosen_tags for t in a["tags"])
            ]
            random_candidates = [a for a in articles if a not in candidates]

            # On pioche 2 pertinents et 1 hasard
            sample_articles = random.sample(candidates, min(2, len(candidates)))
            if random_candidates:
                sample_articles.append(random.choice(random_candidates))

            # Boucle de notation
            for art in sample_articles:
                print(f"\n📄 {art['title']}")
                print(f"   Tags : {art['tags']}")
                # Si tu avais un champ "summary" ou "content" court, tu l'afficherais ici
                # print(f"   Résumé : {art['content'][:100]}...")

                vote = input(
                    "   Est-ce que ça t'intéresse ? (1: Oui! / 2: Bof / 3: Pas du tout) : "
                )

                if vote == "1":  # OUI -> Gros Boost
                    for t in art["tags"]:
                        new_user["weights"][t] = round(
                            new_user["weights"].get(t, 0.5) + 0.8, 2
                        )
                    print("   👍 Noté : On t'en proposera plus !")

                elif vote == "2":  # BOF -> Petit Malus
                    for t in art["tags"]:
                        # On baisse doucement, sans descendre sous 0.1
                        current = new_user["weights"].get(t, 0.5)
                        new_user["weights"][t] = max(0.1, round(current - 0.2, 2))

                elif vote == "3":  # NON -> Gros Malus
                    for t in art["tags"]:
                        current = new_user["weights"].get(t, 0.5)
                        new_user["weights"][t] = max(0.0, round(current - 0.8, 2))
                    print("   👎 Noté : On évitera ce genre de sujet.")

    # --- ÉTAPE 5 : SAUVEGARDE ---
    # Chargement du fichier users existant
    try:
        with open("users.json", "r") as f:
            users = json.load(f)
    except FileNotFoundError:
        users = []

    users.append(new_user)

    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

    print("\n" + "=" * 40)
    print(f"✨ Profil terminé ! ID: {new_id}")
    print("=" * 40)

    return new_id


# --- 5. EXÉCUTION DU SCÉNARIO ---
if __name__ == "__main__":
    # Initialisation
    test_user_id = "user_0"
    test_article_id = "article_0"
    # adding something

    # On charge une première fois
    users, articles = load_data()

    while True:
        # --- AFFICHAGE DU MENU ---
        print("\n" + "=" * 30)
        print("🕹️  PANNEAU DE CONTRÔLE")
        print(f"   User Actuel   : {test_user_id}")
        print(f"   Article Cible : {test_article_id}")
        print("-" * 30)
        print("1. 👤 Changer d'utilisateur")
        print("2. 📄 Changer l'article cible (par ID)")
        print("3. 🔮 Générer les Recommandations")
        print("4. 📖 Simuler LECTURE (Read)")
        print("5. ❤️ Simuler LIKE")
        print("6. 🚪 Quitter")
        print("7. ⏳ Simuler '1 Semaine plus tard' (Decay)")  # NOUVEAU
        print("8. ✨ Créer un nouvel utilisateur (Onboarding)")
        print()
        print("=" * 30)

        try:
            choice = int(input("👉 Ton choix (1-6) : "))
        except ValueError:
            print("❌ Erreur : Entre un chiffre !")
            continue

        # --- LOGIQUE ---

        if choice == 1:
            new_id = input("Nouvel ID User (ex: user_2) : ")
            # Petite vérif pour voir si l'user existe
            if any(u["user_id"] == new_id for u in users):
                test_user_id = new_id
                print(f"✅ User changé pour {test_user_id}")
            else:
                print("⚠️  Attention : Cet ID n'existe pas dans le JSON chargé.")

        elif choice == 2:
            test_article_id = input("Nouvel ID Article (ex: article_42) : ")

        elif choice == 3:
            # CRUCIAL : On recharge les données pour être sûr d'avoir les derniers poids
            users, articles = load_data()

            user_obj, recos = get_recommendations(test_user_id, users, articles)

            if user_obj:
                print_separator(f"RECOMMANDATIONS POUR {user_obj['name']}")
                print_top_interests(user_obj["weights"])
                if recos:
                    print_reco_table(recos)
                    # Astuce : Mettre à jour l'article cible avec le 1er de la liste
                    print(f"\n💡 Astuce : L'article '{recos[0]['id']}' est le top 1.")
                else:
                    print("❌ Aucune recommandation (tout lu ?)")
            else:
                print("❌ User introuvable.")

        elif choice == 4:
            simulate_interaction(test_user_id, test_article_id, "read")
            # On recharge immédiatement pour que la mémoire soit à jour
            users, articles = load_data()

        elif choice == 5:
            simulate_interaction(test_user_id, test_article_id, "like")
            users, articles = load_data()

        elif choice == 6:
            print("Fermeture... Bye ! 👋")
            break
        elif choice == 7:
            apply_time_decay()
            # On recharge pour voir les effets si on fait un choix 3 juste après
            users, articles = load_data()
        elif choice == 8:
            new_id = onboard_user_hybrid()
            test_user_id = new_id  # On connecte directement le nouveau
            users, articles = load_data()
        else:
            print("❌ Choix invalide.")


# eventually adding some like levels a atteindre pour un sentiment d'amelioration
# proposer une recommandation plus poussé en proposant des resumé d'article et voir lequels l'interessent
