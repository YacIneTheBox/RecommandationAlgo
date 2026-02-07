import json
import random


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
        score -= 5.0  # Trop dur (Pénalité forte)
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
    # Trouver le bon utilisateur
    target_user = next((u for u in all_users if u["user_id"] == user_id), None)
    if not target_user:
        return []

    scored_articles = []

    # --- 1. SCORING CLASSIQUE ---
    for article in all_articles:
        if article["article_id"] in target_user["history"]:
            continue

        final_score = calculate_score(target_user, article)

        scored_articles.append(
            {
                "id": article["article_id"],
                "title": article["title"],
                "tags": article["tags"],
                "level": article["level"],
                "score": round(final_score, 2),
                "type": "pertinence",  # On marque l'origine
            }
        )

    # Tri décroissant
    scored_articles.sort(key=lambda x: x["score"], reverse=True)

    # --- 2. INJECTION DE DIVERSITÉ ---
    # On garde les (top_n - 2) meilleurs articles "logiques"
    nb_pertinent = max(1, int(0.8 * top_n))
    final_list = scored_articles[:nb_pertinent]

    # On cherche des articles "Découverte" (Tags avec poids faible < 1.5)
    discovery_candidates = []
    low_interest_tags = [t for t, w in target_user["weights"].items() if w < 1.5]

    # Si l'user aime tout, on prend n'importe quoi d'autre
    if not low_interest_tags:
        low_interest_tags = list(target_user["weights"].keys())

    for article in all_articles:
        # Pas d'article déjà lu, ni déjà dans la liste finale
        if article["article_id"] in target_user["history"]:
            continue
        if any(a["id"] == article["article_id"] for a in final_list):
            continue

        # Si l'article contient un tag "faible intérêt"
        if any(t in low_interest_tags for t in article["tags"]):
            discovery_candidates.append(
                {
                    "id": article["article_id"],
                    "title": article["title"],
                    "tags": article["tags"],
                    "level": article["level"],
                    "score": calculate_score(target_user, article),  # Score fictif
                    "type": "🌟 DÉCOUVERTE",  # Pour l'affichage
                }
            )

    # On ajoute 2 articles de découverte au hasard (s'il y en a)
    if discovery_candidates:
        final_list.extend(
            random.sample(discovery_candidates, min(2, len(discovery_candidates)))
        )

    # Optionnel : On mélange un peu la fin de liste pour ne pas que les découvertes soient toujours en bas
    # Mais pour l'instant, laissons-les à la fin pour bien les voir.

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
                    print(f"   -> Ajouté à l'historique de lecture.")
                else:
                    print(f"   -> Déjà dans l'historique (pas de doublon).")

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


# --- FONCTION UTILITAIRE POUR L'AFFICHAGE ---
def print_separator(title):
    print(f"\n{'=' * 60}")
    print(f" 📊 {title.upper()}")
    print(f"{'=' * 60}")


def print_top_interests(weights, top_n=5):
    # Trie les poids du plus grand au plus petit
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:top_n]
    print(f"🧠 TOP INTÉRÊTS : ", end="")
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
            created_id = create_new_user_wizard()
            # On connecte automatiquement le nouvel utilisateur
            test_user_id = created_id
            # On recharge les données
            users, articles = load_data()
        else:
            print("❌ Choix invalide.")


# eventually adding some like levels a atteindre pour un sentiment d'amelioration
# proposer une recommandation plus poussé en proposant des resumé d'article et voir lequels l'interessent
