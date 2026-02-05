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

    # C. Jitter (Aléatoire pour la découverte)
    # Ajoute un petit flou pour que les listes ne soient pas figées
    score += random.uniform(0, 0.2)

    return score


# --- 3. GÉNÉRATEUR DE LISTE ---
def get_recommendations(user_id, all_users, all_articles, top_n=10):
    # Trouver le bon utilisateur
    target_user = next((u for u in all_users if u["user_id"] == user_id), None)

    if not target_user:
        return []

    scored_articles = []

    for article in all_articles:
        # On évite de recommander les articles déjà lus (history)
        # (Pour ce test simple, on suppose que l'historique contient des ID d'articles)
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
            }
        )

    # Tri décroissant (les plus gros scores en premier)
    scored_articles.sort(key=lambda x: x["score"], reverse=True)

    return target_user, scored_articles[:top_n]


def simulate_interaction(user_id, article_id, interaction_type):
    # Définition des points selon l'action
    addedPoints = 0.0
    if interaction_type == "read":
        addedPoints = 0.2
    elif interaction_type == "like":
        addedPoints = 0.3  # Le like vaut plus que la lecture simple

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


# --- 4. SIMULATION D'ACTION (Mise à jour) ---
def simulate_reading(user_id, article_id):
    # Cette fonction simule: "L'utilisateur a lu et aimé"
    # On recharge le fichier pour être sûr d'avoir la dernière version
    with open("users.json", "r") as f:
        users = json.load(f)

    with open("articles.json", "r") as f:
        articles = json.load(f)

    target_article = next((u for u in articles if u["article_id"] == article_id), None)
    if not target_article:
        print(f"Article avec l'ID {article_id} non trouvé.")
        return

    for user in users:
        if user["user_id"] == user_id:
            print(f"\n[ACTION] {user['name']} lit un article {article_id}...")
            # Mise à jour des poids
            for tag in target_article["tags"]:
                old_weight = user["weights"][tag]
                user["weights"][tag] = round(
                    old_weight + 0.2, 2
                )  # +0.2 points d'intérêt
                print(
                    f"   -> Poids '{tag}' passe de {old_weight} à {user['weights'][tag]}"
                )

            user["history"].append(article_id)
            # Sauvegarde
            with open("users.json", "w") as f:
                json.dump(users, f, indent=4)
            break


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
        print(f"🕹️  PANNEAU DE CONTRÔLE")
        print(f"   User Actuel   : {test_user_id}")
        print(f"   Article Cible : {test_article_id}")
        print("-" * 30)
        print("1. 👤 Changer d'utilisateur")
        print("2. 📄 Changer l'article cible (par ID)")
        print("3. 🔮 Générer les Recommandations")
        print("4. 📖 Simuler LECTURE (Read)")
        print("5. ❤️ Simuler LIKE")
        print("6. 🚪 Quitter")
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

        else:
            print("❌ Choix invalide.")
