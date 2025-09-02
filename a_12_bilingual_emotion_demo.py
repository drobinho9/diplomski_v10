# a_12_bilingual_emotion_demo.py
from transformers import pipeline
from langdetect import detect, LangDetectException

print("--- KORAK 12: DEMONSTRACIJA BILINGVALNOG MODELA (V2.1 - ISPRAVLJENO) ---")

# --- Učitavanje OBA modela pri pokretanju ---
print("Učitavam modele... (ovo može potrajati)")
try:
    emotion_classifier = pipeline(
        "text-classification",
        model="j-hartmann/emotion-english-distilroberta-base",
        top_k=1
    )
    print("-> Engleski model za emocije uspješno učitan.")

    sentiment_classifier = pipeline(
        "sentiment-analysis",
        model="nlptown/bert-base-multilingual-uncased-sentiment"
    )
    print("-> Višejezični model za sentiment uspješno učitan.")

except Exception as e:
    print(f"Greška pri učitavanju modela: {e}")
    emotion_classifier = None
    sentiment_classifier = None


def analyze_bilingual_emotion(text):
    """
    Detektira jezik teksta i koristi odgovarajući model za analizu.
    """
    if not text or (emotion_classifier is None and sentiment_classifier is None):
        return {"error": "Nema unosa ili modeli nisu dostupni."}

    try:
        lang = detect(text)
        print(f"(Detektiran jezik: {lang})")

        if lang == 'en' and emotion_classifier:
            # =============================== KLJUČAN POPRAVAK OVDJE ===============================
            # Dohvaćamo prvi element vanjske liste, pa prvi element unutarnje liste
            result_dict = emotion_classifier(text)[0][0]
            # ====================================================================================
            return {"language": "en", "type": "emotion", "value": result_dict['label'], "score": result_dict['score']}
        else:
            if sentiment_classifier:
                result_dict = sentiment_classifier(text)[0]
                score = int(result_dict['label'].split()[0])

                if score <= 2:
                    sentiment = 'negative'
                elif score == 3:
                    sentiment = 'neutral'
                else:
                    sentiment = 'positive'

                return {"language": lang, "type": "sentiment", "value": sentiment, "score": result_dict['score']}
            else:
                return {"error": "Višejezični model nije dostupan."}

    except LangDetectException:
        return {"error": "Nije moguće detektirati jezik."}


if __name__ == '__main__':
    def print_analysis(title, text_to_analyze):
        print("\n" + "=" * 60)
        print(f"{title}: '{text_to_analyze}'")
        analysis_result = analyze_bilingual_emotion(text_to_analyze)
        if 'error' in analysis_result:
            print(f"Rezultat: {analysis_result['error']}")
        elif analysis_result['type'] == 'emotion':
            print(
                f"Rezultat: Jezik: Engleski | Emocija: **{analysis_result['value']}** (Pouzdanost: {analysis_result['score']:.2f})")
        else:
            print(
                f"Rezultat: Jezik: {analysis_result['language'].upper()} | Sentiment: **{analysis_result['value']}** (Pouzdanost: {analysis_result['score']:.2f})")
        print("=" * 60)


    text_en = "I am so excited for the concert tonight!"
    text_hr = "Ovaj film je bio prilično dosadan i razočaravajuć."
    text_neutral_hr = "Idem u dućan kupiti mlijeko."

    print_analysis("Testna rečenica (EN)", text_en)
    print_analysis("Testna rečenica (HR - Negativno)", text_hr)
    print_analysis("Testna rečenica (HR - Neutralno)", text_neutral_hr)