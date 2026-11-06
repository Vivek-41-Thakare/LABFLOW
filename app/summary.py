import httpx
from app.config import settings


# 30 common laboratory test templates.
# These are educational descriptions, not diagnoses.
LOCKED_TEST_TEMPLATES = {
    "haemoglobin": "Haemoglobin measures the oxygen-carrying protein in red blood cells.",
    "hemoglobin": "Hemoglobin measures the oxygen-carrying protein in red blood cells.",
    "rbc": "Red blood cell count measures the number of red blood cells.",
    "wbc": "White blood cell count measures the number of white blood cells.",
    "platelet count": "Platelet count measures the number of platelets in blood.",
    "total cholesterol": "Total cholesterol measures the overall cholesterol level.",
    "ldl cholesterol": "LDL cholesterol measures low-density lipoprotein cholesterol.",
    "hdl cholesterol": "HDL cholesterol measures high-density lipoprotein cholesterol.",
    "triglycerides": "Triglycerides measure a type of fat in the blood.",
    "glucose": "Glucose measures the amount of sugar in the blood.",
    "fasting blood sugar": "Fasting blood sugar measures glucose after fasting.",
    "hba1c": "HbA1c reflects average blood glucose over approximately three months.",
    "urea": "Urea measures a waste product processed by the kidneys.",
    "bun": "Blood urea nitrogen measures nitrogen from urea in the blood.",
    "creatinine": "Creatinine is a waste product commonly used to assess kidney function.",
    "egfr": "eGFR estimates how effectively the kidneys filter blood.",
    "uric acid": "Uric acid measures a waste product formed during purine breakdown.",
    "sodium": "Sodium measures an important electrolyte in the blood.",
    "potassium": "Potassium measures an electrolyte important for muscle and heart function.",
    "chloride": "Chloride measures an electrolyte that helps maintain fluid balance.",
    "calcium": "Calcium measures the amount of calcium in the blood.",
    "magnesium": "Magnesium measures an electrolyte involved in muscle and nerve function.",
    "tsh": "TSH measures thyroid-stimulating hormone.",
    "t3": "T3 measures a thyroid hormone.",
    "t4": "T4 measures a thyroid hormone.",
    "alt": "ALT is an enzyme commonly assessed in liver-related testing.",
    "ast": "AST is an enzyme commonly assessed in liver-related testing.",
    "bilirubin": "Bilirubin is a pigment produced during the breakdown of red blood cells.",
    "albumin": "Albumin measures a major protein produced by the liver.",
    "total protein": "Total protein measures the combined amount of major proteins in blood."
}


def summarize(values, lang="en"):
    critical = [
        v for v in values
        if v.critical or v.flag == "CRITICAL"
    ]

    if critical:
        critical_messages = {
            "en": "A potentially critical result needs prompt review by the laboratory team. Please contact the lab. No automated explanation is provided for this result.",
            "hi": "एक संभावित गंभीर परिणाम के लिए प्रयोगशाला टीम द्वारा तुरंत समीक्षा आवश्यक है। कृपया प्रयोगशाला से संपर्क करें। इस परिणाम के लिए कोई स्वचालित व्याख्या प्रदान नहीं की जाती है।",
            "te": "ఈ ఫలితం అత్యంత కీలకమైనది కావచ్చు. ప్రయోగశాల బృందం తక్షణమే సమీక్షించాలి. దయచేసి ప్రయోగశాలను సంప్రదించండి. ఈ ఫలితానికి ఆటోమేటెడ్ వివరణ అందించబడదు."
        }
        return {
            "status": "SUPPRESSED_CRITICAL",
            "source": "SAFETY_RULE",
            "text": critical_messages.get(lang, critical_messages["en"])
        }

    abnormal = [
        v for v in values
        if v.flag in ("LOW", "HIGH")
    ]

    if not abnormal:
        texts = {
            "en": "No values are flagged outside the supplied reference ranges.",
            "hi": "दिए गए संदर्भ मानों से बाहर कोई परिणाम चिह्नित नहीं है।",
            "te": "ఇచ్చిన సూచన పరిధికి వెలుపల ఫలితాలు గుర్తించబడలేదు."
        }
        return {
            "status": "TEMPLATE",
            "source": "LOCKED_TEMPLATE",
            "text": texts.get(lang, texts["en"])
        }

    findings = "; ".join(
        f"{v.analyte}: {v.value:g}{v.unit} ({v.flag.lower()})"
        for v in abnormal
    )

    if settings.ai_api_base_url and settings.ai_api_key and settings.ai_model:
        try:
            language = {
                "en": "English",
                "hi": "Hindi",
                "te": "Telugu"
            }.get(lang, "English")

            prompt = (
                f"Explain these abnormal lab values in cautious "
                f"patient-friendly {language}. Do not diagnose or prescribe. "
                f"Advise clinician follow-up. Values: {findings}"
            )

            response = httpx.post(
                settings.ai_api_base_url.rstrip("/") + "/chat/completions",
                headers={
                    "Authorization": "Bearer " + settings.ai_api_key
                },
                json={
                    "model": settings.ai_model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2
                },
                timeout=12
            )
            response.raise_for_status()

            text = response.json()["choices"][0]["message"]["content"]

            if text and len(text) < 1800:
                return {
                    "status": "AI_GENERATED",
                    "source": "AI",
                    "text": text
                }

        except Exception:
            pass

    descriptions = []
    for value in abnormal:
        key = value.analyte.strip().lower()
        description = LOCKED_TEST_TEMPLATES.get(key)

        if description:
            descriptions.append(description)

    description_text = " ".join(descriptions)

    texts = {
        "en": (
            f"Some values are outside the supplied reference range: "
            f"{findings}. {description_text} "
            "This is not a diagnosis. Please discuss the result with your "
            "doctor. Reference ranges can vary by laboratory."
        ),
        "hi": (
            f"कुछ परिणाम दी गई संदर्भ सीमा से बाहर हैं: {findings}। "
            f"{description_text} "
            "यह निदान नहीं है। कृपया अपने डॉक्टर से चर्चा करें।"
        ),
        "te": (
            f"కొన్ని ఫలితాలు ఇచ్చిన సూచన పరిధికి వెలుపల ఉన్నాయి: "
            f"{findings}. {description_text} "
            "ఇది రోగ నిర్ధారణ కాదు. దయచేసి మీ వైద్యునితో చర్చించండి."
        )
    }

    return {
        "status": "FALLBACK_TEMPLATE",
        "source": "LOCKED_TEMPLATE",
        "text": texts.get(lang, texts["en"])
    }
