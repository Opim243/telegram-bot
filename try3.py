from telethon import TelegramClient, events
from difflib import SequenceMatcher
import re
import os

# ==================================================
# CONFIGURATION
# ==================================================

api_id = 32551545
api_hash = "559f503d6d7cb4d3ee2c74320d4ef791"

CHANNELS = [
    -1002277569779,
    -1002224205561,
    -1002136960190,
    -1001369850989,
    -1002384150780
]

MONITOR_CHANNEL = -1001800917286

# ==================================================
# PARAMETRES
# ==================================================

SIMILARITY_THRESHOLD = 0.80

# ==================================================
# DOSSIER MEDIA
# ==================================================

os.makedirs("media", exist_ok=True)

# ==================================================
# STATISTIQUES
# ==================================================

news_count = 0
spam_count = 0
duplicate_count = 0

# ==================================================
# MEMOIRE DES NEWS
# ==================================================

recent_news = []

# ==================================================
# NORMALISATION
# ==================================================

def normalize_text(text):

    text = clean_message(text)

    text = text.lower()

    text = re.sub(r'http\S+', '', text)

    text = re.sub(r'[^\w\s]', ' ', text)

    text = re.sub(r'\s+', ' ', text)

    return text.strip()

# ==================================================
# SUPPRESSION LIGNES DUPLIQUEES
# ==================================================

def remove_duplicate_lines(text):

    lines = text.splitlines()

    unique = []

    for line in lines:

        line = line.strip()

        if line and line not in unique:
            unique.append(line)

    return "\n".join(unique)

# ==================================================
# NETTOYAGE INTELLIGENT
# ==================================================

def clean_message(text):

    patterns_to_remove = [

        # Ouvrir sur X
        r'›\s*ouvrir sur x',
        r'ouvrir sur x',

        # Mentions
        r'@[\w\d_]+',

        # Hashtags
        r'#\w+',

        # URLs
        r'https?://\S+',
        r'www\.\S+',

        # Telegram
        r't\.me/\S+',

        # Réseaux sociaux
        r'x\.com/\S+',
        r'twitter\.com/\S+',
        r'facebook\.com/\S+',
        r'instagram\.com/\S+',

        # Signatures
        r'source\s*:.*',
        r'crédit\s*:.*',
        r'credit\s*:.*',

        # Promotions de canaux
        r'rejoins notre chaîne.*',
        r'rejoignez notre chaîne.*',
        r'rejoins maintenant.*',
        r'rejoignez-nous.*',
        r'abonnez-vous.*telegram.*',
        r'canal telegram.*',
        r'chaîne telegram.*',

        # Anglais
        r'join us.*',
        r'follow us.*',
        r'subscribe.*',

        # Divers
        r'like and share.*',
        r'partagez.*',
        r'cliquez ici.*'
    ]

    cleaned = text

    for pattern in patterns_to_remove:

        cleaned = re.sub(
            pattern,
            '',
            cleaned,
            flags=re.IGNORECASE
        )

    cleaned = remove_duplicate_lines(cleaned)

    cleaned = re.sub(
        r'\n\s*\n+',
        '\n\n',
        cleaned
    )

    cleaned = cleaned.strip()

    return cleaned

# ==================================================
# DETECTION DOUBLONS
# ==================================================

def is_duplicate(text):

    normalized = normalize_text(text)

    for old_text in recent_news:

        similarity = SequenceMatcher(
            None,
            normalized,
            old_text
        ).ratio()

        if similarity >= SIMILARITY_THRESHOLD:
            return True, similarity

    recent_news.append(normalized)

    # conserver uniquement les 1000 dernières
    if len(recent_news) > 1000:
        recent_news.pop(0)

    return False, 0

# ==================================================
# FILTRE ANTI-SPAM
# ==================================================

def is_spam(text):

    text = text.lower()

    instant_block = [

        "1xbet",
        "melbet",
        "betwinner",
        "bet365",
        "1win",
        "zemiplay",

        "reffpa.com",
        "mlbet.co",
        "bwredir.com",
        "lkpq.cc",

        "whatsapp.com/channel",

        "code promo",
        "promo code",

        "dépôt de",
        "depot de",

        "groupe de discussions",
        "rejoignez ce groupe"
    ]

    for word in instant_block:
        if word in text:
            return True, 999, [word]

    score = 0
    reasons = []

    spam_keywords = {

        "pari": 2,
        "paris": 2,
        "pariez": 3,

        "pronostic": 3,
        "pronostique": 3,

        "bonus": 3,
        "cashback": 3,

        "score exact": 4,
        "laisse ton score": 4,

        "abonnez-vous": 4,
        "abonne-toi": 4,

        "rejoins maintenant": 4,
        "rejoignez-nous": 4,

        "canal telegram": 5,
        "chaine telegram": 5,
        "chaîne telegram": 5,

        "t.me/": 3,
        "https://t.me/": 3,

        "inscris-toi": 3,
        "inscrivez-vous": 3,

        "à gagner": 2,
        "gagnants": 2,
        "cadeaux": 2,
        "tirage": 2,
        "iphone": 2,

        "million fcfa": 3,
        "millions fcfa": 3,

        "cash": 2
    }

    for keyword, points in spam_keywords.items():

        if keyword in text:
            score += points
            reasons.append(keyword)

    return score >= 4, score, reasons

# ==================================================
# CONNEXION
# ==================================================

client = TelegramClient(
    "goalsphere_session",
    api_id,
    api_hash
)

# ==================================================
# ECOUTE DES CANAUX
# ==================================================

@client.on(events.NewMessage(chats=CHANNELS))
async def handler(event):

    global news_count
    global spam_count
    global duplicate_count

    text = event.raw_text

    if not text:
       return

# ==========================================
# NETTOYAGE
# ==========================================

    text = clean_message(text)

    if len(text.strip()) < 10:

       print("🗑️ Message vide après nettoyage")

       return

    chat = await event.get_chat()
    channel_name = getattr(chat, "title", "Canal inconnu")

    # ==========================================
    # SPAM
    # ==========================================

    blocked, score, reasons = is_spam(text)

    if blocked:

        spam_count += 1

        print(
            f"🚫 Spam #{spam_count} | "
            f"Canal={channel_name} | "
            f"Score={score}"
        )

        return

    # ==========================================
    # DOUBLON
    # ==========================================

    duplicate, similarity = is_duplicate(text)

    if duplicate:

        duplicate_count += 1

        print(
            f"🔁 Doublon #{duplicate_count} | "
            f"Canal={channel_name} | "
            f"Similarité={similarity:.0%}"
        )

        return

    # ==========================================
    # NEWS VALIDEE
    # ==========================================

    news_count += 1

    print(
        f"⚽ News #{news_count} | "
        f"Canal={channel_name}"
    )

    try:

        # --------------------------------------
        # PHOTO
        # --------------------------------------

        if event.photo:

            photo_path = await event.download_media(
                file="media/"
            )

            await client.send_file(
                MONITOR_CHANNEL,
                photo_path,
                caption=text
            )

            print("📷 Photo transférée")

        # --------------------------------------
        # VIDEO
        # --------------------------------------

        elif event.video:

            print("🎥 Vidéo ignorée")

        # --------------------------------------
        # DOCUMENT
        # --------------------------------------

        elif event.document:

            print("📄 Document ignoré")

        # --------------------------------------
        # TEXTE
        # --------------------------------------

        else:

            await client.send_message(
                MONITOR_CHANNEL,
                text
            )

            print("📝 Message transféré")

    except Exception as e:

        print(f"❌ Erreur : {e}")

# ==================================================
# DEMARRAGE
# ==================================================

print("⚽ Goal Sphere Bot démarré")
print(f"📡 Surveillance de {len(CHANNELS)} canaux")
print("📢 Canal Monitor actif")
print("🚫 Anti-spam actif")
print("🔁 Détection de doublons Niveau 2 active")
print()

client.start()
client.run_until_disconnected()
